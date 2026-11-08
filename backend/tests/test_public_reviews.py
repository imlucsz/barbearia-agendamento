import unittest
from datetime import datetime

from support import asgi_request, load_app_for_environment, main, reset_database
from app.models.user import Appointment, AppointmentStatusEnum, Avaliacao, RoleEnum, Service, User


class PublicReviewTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            client = User(nome="Review Client", email="review-client@example.com", senha_hash="x", role=RoleEnum.CLIENTE)
            barber = User(nome="Review Barber", email="review-barber@example.com", senha_hash="x", role=RoleEnum.BARBEIRO)
            service = Service(nome="Review Cut", preco=40, duracao_minutos=30)
            db.add_all([client, barber, service])
            db.flush()
            appointment_ids = []
            for day in (1, 2, 3):
                appointment = Appointment(
                    user_id=client.id, nome_cliente=client.nome, service_id=service.id,
                    barbeiro_id=barber.id, data_hora=datetime(2026, 1, day),
                    status=AppointmentStatusEnum.AVALIADO, preco=40, duracao_minutos=30,
                )
                db.add(appointment)
                db.flush()
                appointment_ids.append(appointment.id)
            db.add_all([
                Avaliacao(appointment_id=appointment_ids[0], nota=5, comentario="Visible", oculta=False),
                Avaliacao(appointment_id=appointment_ids[1], nota=1, comentario="Hidden", oculta=True),
            ])
            db.commit()
        finally:
            db.close()

    def test_public_endpoint_returns_only_visible_reviews(self):
        status, rows = asgi_request(self.app, "GET", "/appointments/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual([row["comentario"] for row in rows], ["Visible"])
        self.assertTrue(all(not row["oculta"] for row in rows))

    def test_public_endpoint_returns_empty_list_without_reviews(self):
        db = main.SessionLocal()
        try:
            db.query(Avaliacao).delete()
            db.commit()
        finally:
            db.close()
        status, rows = asgi_request(self.app, "GET", "/appointments/avaliacoes")
        self.assertEqual(status, 200)
        self.assertEqual(rows, [])
