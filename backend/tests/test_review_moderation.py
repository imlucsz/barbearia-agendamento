import unittest
from datetime import datetime

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import Appointment, AppointmentStatusEnum, Avaliacao, RoleEnum, Service, User


class ReviewModerationTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            admin = self._user(db, "moderation-admin@example.test", RoleEnum.ADMIN)
            client = self._user(db, "moderation-client@example.test", RoleEnum.CLIENTE)
            barber = self._user(db, "moderation-barber@example.test", RoleEnum.BARBEIRO)
            service = Service(nome="Moderation service", preco=40, duracao_minutos=30)
            db.add(service)
            db.flush()
            appointment = Appointment(
                user_id=client.id, nome_cliente=client.nome, service_id=service.id,
                barbeiro_id=barber.id, data_hora=datetime(2026, 1, 1),
                status=AppointmentStatusEnum.AVALIADO, preco=40, duracao_minutos=30,
            )
            db.add(appointment)
            db.flush()
            review = Avaliacao(appointment_id=appointment.id, nota=2, comentario="Precisa melhorar", oculta=False)
            db.add(review)
            db.commit()
            self.review_id = review.id
            self.admin_email, self.client_email = admin.email, client.email
        finally:
            db.close()

    @staticmethod
    def _user(db, email, role):
        user = User(nome=email, email=email, senha_hash="test", role=role)
        db.add(user)
        db.flush()
        return user

    def request(self, method, path, role="admin"):
        email = self.admin_email if role == "admin" else self.client_email
        token = create_access_token({"sub": email})
        return asgi_request(self.app, method, path, headers={"Authorization": f"Bearer {token}"})

    def test_admin_can_hide_and_restore_public_review(self):
        status, rows = asgi_request(self.app, "GET", "/appointments/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 1)

        status, all_reviews = self.request("GET", "/admin/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual(len(all_reviews), 1)
        status, hidden = self.request("PATCH", f"/admin/avaliacoes/{self.review_id}/ocultar?ocultar=true")
        self.assertEqual(status, 200, hidden)
        self.assertTrue(hidden["oculta"])
        status, public_rows = asgi_request(self.app, "GET", "/appointments/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual(public_rows, [])

        status, restored = self.request("PATCH", f"/admin/avaliacoes/{self.review_id}/ocultar?ocultar=false")
        self.assertEqual(status, 200, restored)
        self.assertFalse(restored["oculta"])
        status, public_rows = asgi_request(self.app, "GET", "/appointments/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual([row["comentario"] for row in public_rows], ["Precisa melhorar"])

    def test_non_admin_cannot_moderate(self):
        status, _body = self.request("GET", "/admin/avaliacoes", role="client")
        self.assertEqual(status, 403)
        status, _body = self.request("PATCH", f"/admin/avaliacoes/{self.review_id}/ocultar?ocultar=true", role="client")
        self.assertEqual(status, 403)

