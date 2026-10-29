import unittest
from datetime import datetime, timedelta

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import Appointment, AppointmentStatusEnum, RoleEnum, Service, User


class ServiceRecordTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            self.client = self._user(db, "rf14-client@example.test", RoleEnum.CLIENTE)
            self.barber = self._user(db, "rf14-barber@example.test", RoleEnum.BARBEIRO)
            self.admin = self._user(db, "rf14-admin@example.test", RoleEnum.ADMIN)
            service = Service(nome="RF14 service", preco=45, duracao_minutos=30)
            db.add(service)
            db.flush()
            self.appointment_ids = {}
            for status in (AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.PENDENTE):
                appointment = Appointment(
                    user_id=self.client.id, nome_cliente=self.client.nome, service_id=service.id,
                    barbeiro_id=self.barber.id, data_hora=datetime.now() + timedelta(days=3),
                    status=status, preco=45, duracao_minutos=30,
                )
                db.add(appointment)
                db.flush()
                self.appointment_ids[len(self.appointment_ids)] = appointment.id
            db.commit()
            self.emails = {"client": self.client.email, "barber": self.barber.email, "admin": self.admin.email}
        finally:
            db.close()

    @staticmethod
    def _user(db, email, role):
        user = User(nome=email, email=email, senha_hash="test-only", role=role)
        db.add(user)
        db.flush()
        return user

    def _update(self, principal, appointment_id, payload):
        token = create_access_token({"sub": self.emails[principal]})
        return asgi_request(
            self.app, "PUT", f"/appointments/{appointment_id}", payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_assigned_barber_records_completion_and_charged_amount(self):
        status, result = self._update("barber", self.appointment_ids[0], {
            "status": "concluido", "valor_cobrado": 38.5,
        })
        self.assertEqual(status, 200, result)
        self.assertEqual(result["status"], "concluido")
        self.assertEqual(result["valor_cobrado"], 38.5)

    def test_admin_can_record_cancellation_and_no_show_statuses(self):
        for appointment_id, new_status in ((self.appointment_ids[1], "cancelado"), (self.appointment_ids[2], "falta")):
            status, result = self._update("admin", appointment_id, {"status": new_status})
            self.assertEqual(status, 200, result)
            self.assertEqual(result["status"], new_status)

    def test_client_cannot_record_team_status_or_charged_amount(self):
        for payload in ({"status": "concluido"}, {"status": "falta"}, {"valor_cobrado": 38.5}):
            status, _body = self._update("client", self.appointment_ids[0], payload)
            self.assertEqual(status, 403)

