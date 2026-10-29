import unittest
from datetime import datetime

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.clock import utc_now_naive
from app.core.security import get_password_hash
from app.database import Base
from app.models.user import (
    Appointment, AppointmentStatusEnum, Avaliacao, ConsentimentoLGPD,
    PasswordResetToken, RefreshToken, RoleEnum, Service, User,
)


class LgpdPortabilityTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        self.owner_id = self.add_user("titular@example.com", "Nome Privado QA", RoleEnum.CLIENTE)
        self.other_id = self.add_user("outra@example.com", "Outra Pessoa QA", RoleEnum.CLIENTE)
        self.barber_id = self.add_user("barber@example.com", "Barbeiro Privado QA", RoleEnum.BARBEIRO)
        self.admin_id = self.add_user("admin@example.com", "Admin QA", RoleEnum.ADMIN)
        self.service_id, self.appointment_id, self.review_id = self.add_records()

    def add_user(self, email, name, role):
        db = main.SessionLocal()
        try:
            user = User(nome=name, email=email, senha_hash=get_password_hash("current-password-123"), role=role,
                        consentimento_lgpd=True, consentimento_em=utc_now_naive())
            db.add(user)
            db.commit()
            return user.id
        finally:
            db.close()

    def add_records(self):
        db = main.SessionLocal()
        try:
            service = Service(nome="Corte teste", preco=40, duracao_minutos=30)
            db.add(service)
            db.flush()
            appointment = Appointment(
                user_id=self.owner_id, nome_cliente="Nome Privado QA", service_id=service.id,
                barbeiro_id=self.barber_id, data_hora=datetime(2025, 1, 15, 10),
                status=AppointmentStatusEnum.AVALIADO, preco=40, duracao_minutos=30, valor_cobrado=37,
            )
            other_appointment = Appointment(
                user_id=self.other_id, nome_cliente="Outra Pessoa QA", service_id=service.id,
                barbeiro_id=self.barber_id, data_hora=datetime(2025, 1, 16, 10),
                status=AppointmentStatusEnum.CONCLUIDO, preco=40, duracao_minutos=30, valor_cobrado=40,
            )
            db.add_all([appointment, other_appointment])
            db.flush()
            review = Avaliacao(appointment_id=appointment.id, nota=5, comentario="Meu comentário privado")
            db.add_all([
                review,
                ConsentimentoLGPD(user_id=self.owner_id, versao_termos="terms-4", aceito_em=utc_now_naive(),
                                  ip_origem="192.0.2.10", origem="https://frontend.test.invalid"),
                PasswordResetToken(user_id=self.owner_id, token="only-a-test-hash", expires_at=utc_now_naive()),
            ])
            db.commit()
            return service.id, appointment.id, review.id
        finally:
            db.close()

    def login(self, email):
        status, body, _headers = asgi_request(self.app, "POST", "/auth/login", {
            "email": email, "senha": "current-password-123",
        }, return_headers=True)
        self.assertEqual(status, 200, body)
        return body["access_token"]

    def test_export_is_versioned_complete_and_never_includes_another_user_or_secrets(self):
        token = self.login("titular@example.com")
        status, payload = asgi_request(self.app, "GET", "/users/me/exportacao", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["usuario"]["email"], "titular@example.com")
        self.assertEqual(payload["consentimentos"][0]["versao_termos"], "terms-4")
        self.assertEqual(payload["agendamentos"][0]["servico"], "Corte teste")
        self.assertEqual(payload["agendamentos"][0]["valor_cobrado"], 37)
        self.assertEqual(payload["avaliacoes"][0]["nota"], 5)
        serialized = str(payload)
        self.assertNotIn("outra@example.com", serialized)
        self.assertNotIn("Outra Pessoa QA", serialized)
        self.assertNotIn("senha_hash", serialized)
        self.assertNotIn("only-a-test-hash", serialized)
        self.assertNotIn("token", payload)
        for _ in range(4):
            self.assertEqual(asgi_request(self.app, "GET", "/users/me/exportacao", headers={"Authorization": f"Bearer {token}"})[0], 200)
        limited, _ = asgi_request(self.app, "GET", "/users/me/exportacao", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(limited, 429)

    def test_erasure_unlinks_identity_preserves_financial_values_and_blocks_login(self):
        token = self.login("titular@example.com")
        admin_token = self.login("admin@example.com")
        report_before = asgi_request(self.app, "GET", "/admin/relatorio?inicio=2025-01-15&fim=2025-01-15", headers={"Authorization": f"Bearer {admin_token}"})[1]
        status, body = asgi_request(self.app, "DELETE", "/users/me", {"senha_atual": "current-password-123"},
                                    headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, 200, body)
        report_after = asgi_request(self.app, "GET", "/admin/relatorio?inicio=2025-01-15&fim=2025-01-15", headers={"Authorization": f"Bearer {admin_token}"})[1]
        self.assertEqual(report_after["total_receita"], report_before["total_receita"])
        self.assertEqual(report_after["total_agendamentos"], report_before["total_agendamentos"])
        review_status, review_rows = asgi_request(self.app, "GET", "/admin/avaliacoes", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(review_status, 200, review_rows)
        self.assertIsNone(next(row for row in review_rows if row["id"] == self.review_id)["appointment_id"])
        self.assertEqual(asgi_request(self.app, "POST", "/auth/login", {"email": "titular@example.com", "senha": "current-password-123"})[0], 401)

        db = main.SessionLocal()
        try:
            appointment = db.query(Appointment).filter_by(id=self.appointment_id).one()
            review = db.query(Avaliacao).filter_by(id=self.review_id).one()
            self.assertIsNone(appointment.user_id)
            self.assertIsNone(appointment.nome_cliente)
            self.assertEqual((appointment.preco, appointment.valor_cobrado, appointment.status), (40, 37, AppointmentStatusEnum.AVALIADO))
            self.assertEqual(review.nota, 5)
            self.assertIsNone(review.appointment_id)
            self.assertIsNone(review.comentario)
            self.assertFalse(db.query(PasswordResetToken).filter_by(user_id=self.owner_id).count())
            self.assertTrue(any(row.revoked_at is not None and row.user_id is None for row in db.query(RefreshToken).all()))
            consent = db.query(ConsentimentoLGPD).filter(ConsentimentoLGPD.user_id.is_(None)).one()
            self.assertIsNone(consent.ip_origem)
            for table in Base.metadata.sorted_tables:
                rows = db.execute(table.select()).mappings().all()
                for row in rows:
                    text = repr(dict(row))
                    self.assertNotIn("Nome Privado QA", text)
                    self.assertNotIn("titular@example.com", text)
        finally:
            db.close()

    def test_wrong_password_and_last_active_admin_are_rejected(self):
        admin_token = self.login("admin@example.com")
        wrong, body = asgi_request(self.app, "DELETE", "/users/me", {"senha_atual": "incorrect-password"},
                                   headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(wrong, 403, body)
        last_admin = self.add_user("last-admin@example.com", "Last Admin", RoleEnum.ADMIN)
        # This fresh admin is the only active admin for its own installation context after the other is deactivated.
        db = main.SessionLocal()
        try:
            db.query(User).filter(User.id == self.admin_id).update({User.ativo: False})
            db.commit()
        finally:
            db.close()
        token = self.login("last-admin@example.com")
        rejected, body = asgi_request(self.app, "DELETE", "/users/me", {"senha_atual": "current-password-123"},
                                      headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(rejected, 409, body)
        db = main.SessionLocal()
        try:
            self.assertTrue(db.query(User).filter_by(id=last_admin, ativo=True).one())
        finally:
            db.close()
