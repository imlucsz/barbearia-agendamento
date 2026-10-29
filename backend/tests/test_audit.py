import json
import os
import unittest
from datetime import timedelta
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import get_password_hash
from app.models.user import AuditLog, RoleEnum, User
from app.core.clock import utc_now_naive
from app.maintenance import purge_audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("development").app
        self.admin_id = self.add_user("admin@example.com", RoleEnum.ADMIN)
        self.client_id = self.add_user("client@example.com", RoleEnum.CLIENTE)

    def add_user(self, email, role):
        db = main.SessionLocal()
        try:
            user = User(nome="Audit Test", email=email, senha_hash=get_password_hash("audit-password"), role=role)
            db.add(user)
            db.commit()
            return user.id
        finally:
            db.close()

    def login(self, email):
        status, body = asgi_request(self.app, "POST", "/auth/login", {"email": email, "senha": "audit-password"})
        self.assertEqual(status, 200, body)
        return body["access_token"]

    def test_login_events_are_recorded_without_password_or_token(self):
        asgi_request(self.app, "POST", "/auth/login", {"email": "missing@example.com", "senha": "do-not-store-this"})
        token = self.login("admin@example.com")
        db = main.SessionLocal()
        try:
            logs = db.query(AuditLog).filter(AuditLog.acao == "auth.login").all()
            self.assertEqual([row.resultado for row in logs], ["falha", "sucesso"])
            rendered = json.dumps([row.detalhes for row in logs])
            self.assertNotIn("do-not-store-this", rendered)
            self.assertNotIn(token, rendered)
        finally:
            db.close()

    def test_security_log_is_json_with_request_id_and_without_account_pii(self):
        with self.assertLogs("security.audit", level="INFO") as captured:
            status, _body, headers = asgi_request(
                self.app, "POST", "/auth/login",
                {"email": "admin@example.com", "senha": "audit-password"},
                headers={"X-Request-ID": "audit-request-123"}, return_headers=True,
            )
        self.assertEqual(status, 200)
        self.assertEqual(headers["x-request-id"], "audit-request-123")
        event = next(json.loads(item.getMessage()) for item in captured.records if '"event":"security_audit"' in item.getMessage())
        self.assertEqual(event["request_id"], "audit-request-123")
        self.assertNotIn("admin@example.com", captured.records[0].getMessage())

    def test_admin_filters_pagination_and_non_admin_forbidden(self):
        token = self.login("admin@example.com")
        db = main.SessionLocal()
        try:
            db.add_all([
                AuditLog(usuario_id=self.admin_id, ator_role="admin", acao="target.action", entidade="user", resultado="sucesso", detalhes={}),
                AuditLog(usuario_id=self.client_id, ator_role="cliente", acao="other.action", entidade="user", resultado="sucesso", detalhes={}),
            ])
            db.commit()
        finally:
            db.close()
        status, body = asgi_request(self.app, "GET", "/admin/auditoria", headers={"Authorization": f"Bearer {token}"}, return_headers=False)
        self.assertEqual(status, 200, body)
        status, body = asgi_request(self.app, "GET", "/admin/auditoria?usuario=%s&acao=target.action&limit=1" % self.admin_id, headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["acao"], "target.action")
        client_token = self.login("client@example.com")
        status, _ = asgi_request(self.app, "GET", "/admin/auditoria", headers={"Authorization": f"Bearer {client_token}"})
        self.assertEqual(status, 403)

    def test_audit_database_failure_does_not_fail_registration(self):
        with patch("app.core.audit.AuditLog", side_effect=RuntimeError("audit unavailable")):
            status, body = asgi_request(self.app, "POST", "/auth/register", {
                "nome": "Resilient User", "email": "resilient@example.com",
                "senha": "resilient-password", "consentimento_lgpd": True,
            })
        self.assertEqual(status, 201, body)

    def test_logout_service_mutation_and_personal_export_are_audited(self):
        admin_token = self.login("admin@example.com")
        status, body = asgi_request(self.app, "POST", "/services/", {"nome": "Corte", "preco": 35, "duracao_minutos": 30}, headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(status, 201, body)
        client_token = self.login("client@example.com")
        status, body = asgi_request(self.app, "GET", "/users/me/export", headers={"Authorization": f"Bearer {client_token}"})
        self.assertEqual(status, 200, body)
        status, _ = asgi_request(self.app, "POST", "/auth/logout", headers={"Origin": "https://frontend.test.invalid"})
        self.assertEqual(status, 200)
        db = main.SessionLocal()
        try:
            actions = {row.acao for row in db.query(AuditLog).all()}
            self.assertTrue({"servico.criado", "dados.exportados", "auth.logout"}.issubset(actions))
        finally:
            db.close()

    def test_purge_dry_run_keeps_only_expired_counted(self):
        os.environ["RETENTION_DAYS"] = "30"
        old, recent = utc_now_naive() - timedelta(days=31), utc_now_naive()
        db = main.SessionLocal()
        try:
            db.add_all([
                AuditLog(acao="expired", entidade="test", resultado="sucesso", detalhes={}, ocorrido_em=old),
                AuditLog(acao="recent", entidade="test", resultado="sucesso", detalhes={}, ocorrido_em=recent),
            ])
            db.commit()
        finally:
            db.close()
        try:
            with redirect_stdout(StringIO()):
                self.assertEqual(purge_audit(dry_run=True), 1)
            db = main.SessionLocal()
            try:
                self.assertEqual(db.query(AuditLog).filter(AuditLog.acao.in_(["expired", "recent"])).count(), 2)
            finally:
                db.close()
        finally:
            os.environ.pop("RETENTION_DAYS", None)
