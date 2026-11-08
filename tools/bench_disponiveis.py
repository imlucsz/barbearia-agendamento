"""Benchmark GET /appointments/disponiveis using disposable databases only.

Run with backend/.venv: python tools/bench_disponiveis.py
Optional PostgreSQL target must be explicitly set as BOOKING_TEST_POSTGRES_URL,
localhost only, and have a database name ending in _test.
"""
from __future__ import annotations

import os
import statistics
import tempfile
import time
from datetime import timedelta
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "bench-only-secret-key-32-bytes-minimum")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "https://bench.invalid")
os.environ["DATABASE_URL"] = "sqlite://"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import (
    Appointment, AppointmentStatusEnum, BarbearioServico, BloqueioHorario,
    JornadaTrabalho, RoleEnum, Service, User,
)
from app.routers.appointments import get_available_slots
from app.booking import now_local


def _engine(url: str):
    if url == "sqlite://":
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url)


def run_benchmark(label: str, url: str) -> dict:
    engine = _engine(url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        service = Service(nome="Benchmark fictício", preco=40, duracao_minutos=30)
        db.add(service)
        db.flush()
        barbers = []
        for index in range(5):
            barber = User(nome=f"Barbeiro benchmark {index}", email=f"bench-{index}@example.test",
                          senha_hash="x", role=RoleEnum.BARBEIRO, ativo=True)
            db.add(barber)
            db.flush()
            barbers.append(barber)
            db.add(BarbearioServico(barbeiro_id=barber.id, service_id=service.id))
            for weekday in range(7):
                db.add(JornadaTrabalho(barbeiro_id=barber.id, dia_semana=weekday,
                                       hora_inicio="09:00", hora_fim="18:00", ativo=True))
        day = (now_local() + timedelta(days=1)).date()
        for index in range(5):
            db.add(BloqueioHorario(barbeiro_id=barbers[index].id,
                                   inicio=now_local().replace(hour=12, minute=0) + timedelta(days=1),
                                   fim=now_local().replace(hour=13, minute=0) + timedelta(days=1),
                                   tipo="bloqueio_ad_hoc", ativo=True))
        for index in range(500):
            barber = barbers[index % len(barbers)]
            appointment_day = day + timedelta(days=index // 400)
            db.add(Appointment(user_id=None, nome_cliente=f"Fictício {index}", service_id=service.id,
                               barbeiro_id=barber.id,
                               data_hora=now_local().replace(year=appointment_day.year, month=appointment_day.month,
                                                             day=appointment_day.day, hour=9 + (index % 8), minute=0),
                               status=AppointmentStatusEnum.PENDENTE, preco=40, duracao_minutos=30))
        db.commit()

        counter = {"queries": 0}
        def count_query(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith(("SELECT", "WITH")):
                counter["queries"] += 1
        event.listen(engine, "before_cursor_execute", count_query)
        timings = []
        for _ in range(100):
            counter["queries"] = 0
            started = time.perf_counter()
            get_available_slots(service_id=service.id, data=day, barbeiro_id=None,
                                db=db, current_user=User(id=0, role=RoleEnum.ADMIN))
            timings.append((time.perf_counter() - started) * 1000)
        event.remove(engine, "before_cursor_execute", count_query)
        ordered = sorted(timings)
        result = {
            "database": label,
            "calls": len(timings),
            "p50_ms": round(statistics.median(ordered), 2),
            "p95_ms": round(ordered[94], 2),
            "max_ms": round(max(ordered), 2),
            "queries_last_call": counter["queries"],
        }
        print(result)
        return result
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def main():
    with tempfile.TemporaryDirectory(prefix="bench-disponiveis-") as directory:
        sqlite_path = Path(directory) / "benchmark.sqlite3"
        run_benchmark("SQLite temporário", f"sqlite:///{sqlite_path.as_posix()}")
    postgres = os.environ.get("BOOKING_TEST_POSTGRES_URL")
    if postgres:
        from sqlalchemy.engine import make_url
        parsed = make_url(postgres)
        if (parsed.get_backend_name() != "postgresql" or parsed.host not in {"localhost", "127.0.0.1", "::1"}
                or not (parsed.database or "").lower().endswith("_test")):
            raise RuntimeError("PostgreSQL benchmark requires localhost and a *_test database")
        # Use a disposable isolated schema so the supplied test database remains intact.
        schema = "bench_disponiveis_" + os.urandom(6).hex()
        admin_engine = create_engine(postgres)
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        query = dict(parsed.query)
        query["options"] = f"-c search_path={schema}"
        isolated_url = parsed.set(query=query).render_as_string(hide_password=False)
        try:
            run_benchmark("PostgreSQL de teste (schema temporário)", isolated_url)
        finally:
            with admin_engine.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            admin_engine.dispose()
    else:
        print("PostgreSQL: não executado (BOOKING_TEST_POSTGRES_URL ausente)")


if __name__ == "__main__":
    main()
