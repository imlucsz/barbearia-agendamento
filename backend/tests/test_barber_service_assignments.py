import unittest
from datetime import timedelta

from support import asgi_request, load_app_for_environment, main, reset_database
from app.booking import now_local
from app.core.security import create_access_token
from app.models.user import JornadaTrabalho, RoleEnum, Service, User


class BarberServiceAssignmentTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            admin = User(nome="Assignment Admin", email="assignment-admin@example.test", senha_hash="test", role=RoleEnum.ADMIN)
            client = User(nome="Assignment Client", email="assignment-client@example.test", senha_hash="test", role=RoleEnum.CLIENTE)
            barber = User(nome="Assignment Barber", email="assignment-barber@example.test", senha_hash="test", role=RoleEnum.BARBEIRO)
            service = Service(nome="Assignment Service", preco=45, duracao_minutos=30)
            db.add_all([admin, client, barber, service])
            db.flush()
            tomorrow = (now_local() + timedelta(days=1)).date()
            db.add(JornadaTrabalho(
                barbeiro_id=barber.id, dia_semana=(tomorrow.weekday() + 1) % 7,
                hora_inicio="09:00", hora_fim="17:00", ativo=True,
            ))
            db.commit()
            self.admin_id, self.client_id, self.barber_id, self.service_id = admin.id, client.id, barber.id, service.id
            self.client_email, self.admin_email, self.day = client.email, admin.email, tomorrow.isoformat()
        finally:
            db.close()

    def request(self, method, path, payload=None, role="client"):
        email = self.admin_email if role == "admin" else self.client_email
        token = create_access_token({"sub": email})
        return asgi_request(self.app, method, path, payload, headers={"Authorization": f"Bearer {token}"})

    def test_assignment_adds_barber_to_catalog_and_availability_then_removal_reverses_it(self):
        status, rows = self.request("GET", f"/barbeiro-servico/servico/{self.service_id}/barbeiros")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])

        status, created = self.request("POST", "/barbeiro-servico/", {
            "barbeiro_id": self.barber_id, "service_id": self.service_id,
        }, role="admin")
        self.assertEqual(status, 201, created)

        status, rows = self.request("GET", f"/barbeiro-servico/servico/{self.service_id}/barbeiros")
        self.assertEqual(status, 200)
        self.assertEqual([row["barbeiro_id"] for row in rows], [self.barber_id])
        status, slots = self.request(
            "GET", f"/appointments/disponiveis?service_id={self.service_id}&barbeiro_id={self.barber_id}&data={self.day}",
        )
        self.assertEqual(status, 200, slots)
        self.assertTrue(slots)
        self.assertTrue(all(slot["barbeiro_id"] == self.barber_id for slot in slots))

        status, _body = self.request(
            "DELETE", f"/barbeiro-servico/?barbeiro_id={self.barber_id}&service_id={self.service_id}", role="admin",
        )
        self.assertEqual(status, 204)
        status, rows = self.request("GET", f"/barbeiro-servico/servico/{self.service_id}/barbeiros")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])
        status, _body = self.request(
            "GET", f"/appointments/disponiveis?service_id={self.service_id}&barbeiro_id={self.barber_id}&data={self.day}",
        )
        self.assertEqual(status, 404)

