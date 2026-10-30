import unittest
from datetime import datetime, timedelta

from support import asgi_request, load_app_for_environment, main, reset_database
from app.booking import now_local
from app.core.security import create_access_token
from app.models.user import BarbearioServico, RoleEnum, Service, User


class ScheduleBlockLifecycleTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            self.barber = User(nome="Lifecycle Barber", email="lifecycle-barber@example.test", senha_hash="test", role=RoleEnum.BARBEIRO)
            self.admin = User(nome="Lifecycle Admin", email="lifecycle-admin@example.test", senha_hash="test", role=RoleEnum.ADMIN)
            service = Service(nome="Lifecycle Service", preco=40, duracao_minutos=30)
            db.add_all([self.barber, self.admin, service])
            db.flush()
            db.add(BarbearioServico(barbeiro_id=self.barber.id, service_id=service.id))
            self.barber_id, self.admin_email, self.barber_email, self.service_id = (
                self.barber.id, self.admin.email, self.barber.email, service.id,
            )
            self.day = (now_local() + timedelta(days=1)).date()
            self.weekday = (self.day.weekday() + 1) % 7
            self.day_text = self.day.isoformat()
            db.commit()
        finally:
            db.close()

    def request(self, method, path, payload=None, role="barber"):
        email = self.admin_email if role == "admin" else self.barber_email
        token = create_access_token({"sub": email})
        return asgi_request(self.app, method, path, payload, headers={"Authorization": f"Bearer {token}"})

    def available(self):
        return self.request(
            "GET", f"/appointments/disponiveis?service_id={self.service_id}&barbeiro_id={self.barber_id}&data={self.day_text}",
            role="admin",
        )

    def test_owner_can_create_update_and_deactivate_schedule(self):
        status, schedule = self.request("POST", "/horario/jornadas", {
            "barbeiro_id": self.barber_id, "dia_semana": self.weekday,
            "hora_inicio": "09:00", "hora_fim": "17:00", "ativo": True,
        })
        self.assertEqual(status, 201, schedule)
        status, slots = self.available()
        self.assertEqual(status, 200)
        self.assertIn("09:00", [slot["horario"] for slot in slots])

        status, updated = self.request("PUT", f"/horario/jornadas/{schedule['id']}", {
            "hora_inicio": "10:00", "hora_fim": "16:00",
        })
        self.assertEqual(status, 200, updated)
        status, slots = self.available()
        self.assertEqual(status, 200)
        self.assertIn("10:00", [slot["horario"] for slot in slots])
        self.assertNotIn("09:00", [slot["horario"] for slot in slots])

        status, updated = self.request("PUT", f"/horario/jornadas/{schedule['id']}", {"ativo": False})
        self.assertEqual(status, 200, updated)
        status, slots = self.available()
        self.assertEqual(status, 200)
        self.assertEqual(slots, [])
        status, _body = self.request("DELETE", f"/horario/jornadas/{schedule['id']}")
        self.assertEqual(status, 204)
        status, rows = self.request("GET", f"/horario/jornadas/{self.barber_id}")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])

    def test_folga_and_feriado_blocks_edit_deactivate_and_remove_availability(self):
        status, _schedule = self.request("POST", "/horario/jornadas", {
            "barbeiro_id": self.barber_id, "dia_semana": self.weekday,
            "hora_inicio": "09:00", "hora_fim": "17:00", "ativo": True,
        })
        self.assertEqual(status, 201)

        for block_type in ("folga", "feriado"):
            start = datetime.combine(self.day, datetime.strptime("10:00", "%H:%M").time())
            end = start + timedelta(minutes=30)
            status, block = self.request("POST", "/horario/bloqueios", {
                "barbeiro_id": self.barber_id, "inicio": start.isoformat(), "fim": end.isoformat(),
                "tipo": block_type, "motivo": f"Teste {block_type}", "ativo": True,
            })
            self.assertEqual(status, 201, block)
            status, slots = self.available()
            self.assertEqual(status, 200)
            self.assertNotIn("10:00", [slot["horario"] for slot in slots])
            self.assertIn("10:30", [slot["horario"] for slot in slots])

            updated_end = end + timedelta(minutes=30)
            status, updated = self.request("PUT", f"/horario/bloqueios/{block['id']}", {
                "fim": updated_end.isoformat(), "motivo": f"Revisto {block_type}",
            })
            self.assertEqual(status, 200, updated)
            self.assertEqual(updated["motivo"], f"Revisto {block_type}")

            status, _updated = self.request("PUT", f"/horario/bloqueios/{block['id']}", {"ativo": False})
            self.assertEqual(status, 200)
            status, slots = self.available()
            self.assertEqual(status, 200)
            self.assertIn("10:00", [slot["horario"] for slot in slots])

            status, _active = self.request("PUT", f"/horario/bloqueios/{block['id']}", {"ativo": True})
            self.assertEqual(status, 200)
            status, _body = self.request("DELETE", f"/horario/bloqueios/{block['id']}")
            self.assertEqual(status, 204)
            status, slots = self.available()
            self.assertEqual(status, 200)
            self.assertIn("10:00", [slot["horario"] for slot in slots])

