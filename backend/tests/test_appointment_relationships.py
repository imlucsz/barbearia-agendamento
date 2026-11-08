import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

from support import main, reset_database
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    RoleEnum,
    Service,
    User,
)


_BACKEND_DIR = Path(__file__).resolve().parents[1]


class AppointmentRelationshipTests(unittest.TestCase):
    def setUp(self):
        reset_database()

    def test_barbeiro_relationships_navigate_both_ways_after_reload(self):
        db = main.SessionLocal()
        try:
            barber = User(
                nome="Barbeiro QA",
                email="barber-orm@example.test",
                senha_hash="test-hash",
                role=RoleEnum.BARBEIRO,
            )
            client = User(
                nome="Cliente QA",
                email="client-orm@example.test",
                senha_hash="test-hash",
                role=RoleEnum.CLIENTE,
            )
            service = Service(nome="Corte ORM QA", preco=35.0, duracao_minutos=30)
            db.add_all([barber, client, service])
            db.flush()

            appointment = Appointment(
                user=client,
                service=service,
                data_hora=datetime(2030, 1, 2, 12, 0),
                status=AppointmentStatusEnum.CONFIRMADO,
                preco=service.preco,
                duracao_minutos=service.duracao_minutos,
            )
            barber.barbeiro_appointments.append(appointment)
            db.add(appointment)

            self.assertIs(appointment.barbeiro, barber)
            self.assertIn(appointment, barber.barbeiro_appointments)
            self.assertIs(appointment.user, client)

            db.commit()
            appointment_id = appointment.id
            barber_id = barber.id
            client_id = client.id
            db.expunge_all()

            persisted_appointment = db.query(Appointment).filter_by(id=appointment_id).one()
            persisted_barber = db.query(User).filter_by(id=barber_id).one()
            persisted_client = db.query(User).filter_by(id=client_id).one()

            self.assertEqual(persisted_appointment.barbeiro_id, barber_id)
            self.assertIs(persisted_appointment.barbeiro, persisted_barber)
            self.assertEqual(
                [item.id for item in persisted_barber.barbeiro_appointments],
                [appointment_id],
            )
            self.assertEqual(persisted_appointment.user_id, client_id)
            self.assertIs(persisted_appointment.user, persisted_client)
            self.assertEqual(
                [item.id for item in persisted_client.appointments],
                [appointment_id],
            )
        finally:
            db.close()

    def test_mapper_does_not_emit_the_ambiguous_barbeiro_relationship_warning(self):
        script = """
import warnings
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import configure_mappers
from app.models.user import Appointment, User

with warnings.catch_warnings(record=True) as captured:
    warnings.simplefilter('always', SAWarning)
    configure_mappers()

target = [
    item for item in captured
    if 'Appointment.barbeiro' in str(item.message)
    and 'User.barbeiro_appointments' in str(item.message)
]
for item in captured:
    if item not in target:
        warnings.showwarning(item.message, item.category, item.filename, item.lineno)
if target:
    raise AssertionError(str(target[0].message))
"""
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite:///:memory:"
        env["PYTHON_DOTENV_DISABLED"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
