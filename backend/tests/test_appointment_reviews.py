import unittest
from datetime import datetime

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import create_access_token
from app.models.user import Appointment, AppointmentStatusEnum, RoleEnum, Service, User


class AppointmentReviewTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        db = main.SessionLocal()
        try:
            self.client = self._add_user(db, "review-owner@example.test", RoleEnum.CLIENTE)
            self.other = self._add_user(db, "review-other@example.test", RoleEnum.CLIENTE)
            self.barber = self._add_user(db, "review-barber@example.test", RoleEnum.BARBEIRO)
            service = Service(nome="Review service", preco=40, duracao_minutos=30)
            db.add(service)
            db.flush()
            self.concluded_id = self._add_appointment(db, service, AppointmentStatusEnum.CONCLUIDO)
            self.pending_id = self._add_appointment(db, service, AppointmentStatusEnum.PENDENTE)
            db.commit()
            self.owner_email = self.client.email
            self.other_email = self.other.email
        finally:
            db.close()

    @staticmethod
    def _add_user(db, email, role):
        user = User(nome=email, email=email, senha_hash="test-only", role=role)
        db.add(user)
        db.flush()
        return user

    def _add_appointment(self, db, service, status):
        appointment = Appointment(
            user_id=self.client.id, nome_cliente=self.client.nome, service_id=service.id,
            barbeiro_id=self.barber.id, data_hora=datetime(2026, 1, 1, 10),
            status=status, preco=service.preco, duracao_minutos=service.duracao_minutos,
        )
        db.add(appointment)
        db.flush()
        return appointment.id

    def _request(self, email, appointment_id, payload):
        token = create_access_token({"sub": email})
        return asgi_request(
            self.app, "POST", f"/appointments/{appointment_id}/avaliacao", payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_owner_can_rate_concluded_appointment_only_once(self):
        status, row = self._request(self.owner_email, self.concluded_id, {"nota": 5, "comentario": "Atendimento excelente"})
        self.assertEqual(status, 201, row)
        self.assertEqual(row["nota"], 5)
        self.assertEqual(row["comentario"], "Atendimento excelente")
        db = main.SessionLocal()
        try:
            appointment = db.query(Appointment).filter(Appointment.id == self.concluded_id).one()
            self.assertEqual(appointment.status, AppointmentStatusEnum.AVALIADO)
        finally:
            db.close()
        status, _body = self._request(self.owner_email, self.concluded_id, {"nota": 4})
        self.assertEqual(status, 400)

    def test_rating_requires_owner_and_concluded_status_and_valid_score(self):
        status, _body = self._request(self.other_email, self.concluded_id, {"nota": 5})
        self.assertEqual(status, 403)
        status, _body = self._request(self.owner_email, self.pending_id, {"nota": 5})
        self.assertEqual(status, 400)
        status, _body = self._request(self.owner_email, self.concluded_id, {"nota": 0})
        self.assertEqual(status, 422)

