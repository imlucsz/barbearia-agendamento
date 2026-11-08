"""Local-only disposable fixture. No inherited database or email credentials."""
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def run():
    with tempfile.TemporaryDirectory(prefix="booking-smart-test-") as directory:
        for key in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "PASSWORD_RESET_URL",
                    "EMAIL_TRANSPORT", "BREVO_API_KEY", "EMAIL_FROM"):
            os.environ.pop(key, None)
        os.environ.update(
            APP_ENV="test", PYTHON_DOTENV_DISABLED="1", SERVE_FRONTEND="true",
            DATABASE_URL="sqlite:///" + (Path(directory) / "booking_test.db").as_posix(),
            SECRET_KEY="booking-smart-disposable-secret-only",
            CORS_ALLOWED_ORIGINS="http://127.0.0.1:4186", ALLOWED_HOSTS="127.0.0.1,localhost",
            SCHEDULING_TIMEZONE="America/Sao_Paulo",
        )
        from alembic import command
        from alembic.config import Config
        config = Config(str(ROOT / "backend/alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "backend/alembic"))
        command.upgrade(config, "head")
        from app.database import SessionLocal
        from app.booking import now_local
        from app.core.security import get_password_hash
        from app.models.user import (
            Appointment, AppointmentStatusEnum, Avaliacao, BarbearioServico,
            BloqueioHorario, JornadaTrabalho, RoleEnum, Service, User,
        )
        tomorrow = now_local().date() + timedelta(days=1)
        with SessionLocal() as db:
            client = User(nome='Cliente <svg onload="window.__xss=4">', email="smart@example.com",
                          senha_hash=get_password_hash("Booking-Test-Only-2026!"),
                          role=RoleEnum.CLIENTE, consentimento_lgpd=True)
            barber = User(nome='Profissional <img src=x onerror="window.__xss=1">', email="barber@example.com",
                          senha_hash="test-only", role=RoleEnum.BARBEIRO)
            other = User(nome="Outro profissional", email="other@example.com",
                         senha_hash="test-only", role=RoleEnum.BARBEIRO)
            admin = User(nome="Administrador fictício", email="admin@example.com",
                         senha_hash=get_password_hash("Booking-Test-Only-2026!"), role=RoleEnum.ADMIN)
            services = [Service(nome='Corte <img src=x onerror="window.__xss=1">', descricao="<script>window.__xss=2</script>",
                                preco=25, duracao_minutos=30),
                        Service(nome="Serviço longo", preco=50, duracao_minutos=180)]
            db.add_all([client, barber, other, admin, *services])
            db.flush()
            for service in services:
                for professional in (barber, other):
                    db.add(BarbearioServico(barbeiro_id=professional.id, service_id=service.id))
            for offset in (0, 2, 3):
                day = tomorrow + timedelta(days=offset)
                db.add(JornadaTrabalho(barbeiro_id=barber.id, dia_semana=(day.weekday() + 1) % 7,
                                       hora_inicio="09:00", hora_fim="12:00", ativo=True))
            day = tomorrow + timedelta(days=1)
            db.add(JornadaTrabalho(barbeiro_id=other.id, dia_semana=(day.weekday() + 1) % 7,
                                   hora_inicio="09:00", hora_fim="12:00", ativo=True))
            db.add(BloqueioHorario(barbeiro_id=barber.id,
                                  inicio=datetime.combine(tomorrow + timedelta(days=2), datetime.min.time()),
                                  fim=datetime.combine(tomorrow + timedelta(days=3), datetime.min.time()),
                                  tipo="feriado", ativo=True))
            db.add(Appointment(user_id=client.id, barbeiro_id=barber.id, service_id=services[0].id,
                               data_hora=datetime.combine(tomorrow, datetime.min.time()).replace(hour=9),
                               preco=25, duracao_minutos=180, status=AppointmentStatusEnum.CONFIRMADO))
            db.add(Avaliacao(nota=5, comentario='<img src=x onerror="window.__xss=3">', oculta=False))
            db.commit()
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=4186, access_log=False)


if __name__ == "__main__":
    run()
