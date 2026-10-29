"""Create deterministic, fictional E2E records in the isolated SQLite database."""

import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from tempfile import gettempdir

from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from zoneinfo import ZoneInfo


def validate_test_database() -> date:
    if os.environ.get("APP_ENV") != "test":
        raise RuntimeError("E2E seed only runs with APP_ENV=test")
    url = make_url(os.environ.get("DATABASE_URL", ""))
    if url.get_backend_name() != "sqlite" or url.database is None:
        raise RuntimeError("E2E seed requires its temporary SQLite database")
    database_path = Path(url.database).resolve()
    temp_path = Path(gettempdir()).resolve()
    if temp_path not in database_path.parents or not database_path.parent.name.startswith("barbearia-e2e-"):
        raise RuntimeError("E2E seed refused a database outside its temporary test directory")
    expected = os.environ.get("E2E_BOOKING_DATE", "")
    booking_date = date.fromisoformat(expected)
    local_target = datetime.now(ZoneInfo("America/Sao_Paulo")).date() + timedelta(days=5)
    if booking_date != local_target:
        raise RuntimeError("E2E booking date changed while preparing the isolated database")
    return booking_date


booking_date = validate_test_database()

from app.core.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.user import (  # noqa: E402
    Appointment,
    AppointmentStatusEnum,
    BarbearioServico,
    BloqueioHorario,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


if not set(Base.metadata.tables).issubset(set(inspect(engine).get_table_names())):
    raise RuntimeError("Alembic did not create the complete E2E schema")

admin_password = "E2E-Test-Admin-Only-2026!"
client_password = "E2E-Test-Client-Only-2026!"
barber_password = "E2E-Test-Barber-Only-2026!"

with SessionLocal() as db:
    admin = User(
        nome="Admin E2E Fictício", email="admin.e2e@example.com",
        senha_hash=get_password_hash(admin_password), role=RoleEnum.ADMIN,
        consentimento_lgpd=False,
    )
    barber = User(
        nome="Barbeiro E2E Fictício", email="barbeiro.e2e@example.com",
        senha_hash=get_password_hash(barber_password), role=RoleEnum.BARBEIRO,
        consentimento_lgpd=False,
    )
    client = User(
        nome="Cliente E2E Fictício", email="cliente.e2e@example.com",
        senha_hash=get_password_hash(client_password), role=RoleEnum.CLIENTE,
        consentimento_lgpd=True,
    )
    mobile_client = User(
        nome="Cliente Mobile E2E Fictício", email="cliente.mobile.e2e@example.com",
        senha_hash=get_password_hash("E2E-Test-Client-Only-2026!"), role=RoleEnum.CLIENTE,
        consentimento_lgpd=True,
    )
    service = Service(nome="Corte E2E", preco=35.0, duracao_minutos=30)
    long_service = Service(nome="Serviço Longo E2E", preco=75.0, duracao_minutos=90)
    db.add_all([admin, barber, client, mobile_client, service, long_service])
    db.flush()
    db.add(BarbearioServico(barbeiro_id=barber.id, service_id=service.id))
    db.add(BarbearioServico(barbeiro_id=barber.id, service_id=long_service.id))

    for weekday in range(7):
        db.add(JornadaTrabalho(
            barbeiro_id=barber.id,
            dia_semana=weekday,
            hora_inicio="08:00",
            hora_fim="18:00",
            ativo=True,
        ))

    blocked_start = datetime.combine(booking_date, time(12, 0))
    db.add(BloqueioHorario(
        barbeiro_id=barber.id,
        inicio=blocked_start,
        fim=blocked_start + timedelta(minutes=30),
        motivo="Bloqueio E2E fictício",
        tipo="bloqueio_ad_hoc",
        ativo=True,
    ))

    yesterday = datetime.now(ZoneInfo("America/Sao_Paulo")).date() - timedelta(days=2)
    for account in (client, mobile_client):
        for offset in range(2):
            completed_at = datetime.combine(yesterday - timedelta(days=offset), time(10 + offset, 0))
            db.add(Appointment(
                user_id=account.id,
                nome_cliente=account.nome,
                service_id=service.id,
                barbeiro_id=barber.id,
                data_hora=completed_at,
                status=AppointmentStatusEnum.CONCLUIDO,
                preco=service.preco,
                duracao_minutos=service.duracao_minutos,
            ))
    db.commit()
