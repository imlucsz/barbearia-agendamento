from support import access_token_for_user
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

    def test_failed_known_login_keeps_actor_and_unknown_login_stays_anonymous(self):
        for email, expected_actor in (("client@example.com", self.client_id), ("unknown@example.com", None)):
            status, _ = asgi_request(self.app, "POST", "/auth/login", {"email": email, "senha": "wrong-fixture-password"})
            self.assertEqual(status, 401)
            with main.SessionLocal() as db:
                row = db.query(AuditLog).filter_by(acao="auth.login").order_by(AuditLog.id.desc()).first()
                self.assertEqual(row.usuario_id, expected_actor)
                self.assertEqual(row.resultado, "falha")

    def test_admin_profile_edit_records_field_names_without_personal_values(self):
        token = self.login("admin@example.com")
        status, _ = asgi_request(self.app, "PUT", f"/users/{self.client_id}",
            {"nome": "Private Fixture Name", "email": "changed@example.com"},
            headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, 200)
        with main.SessionLocal() as db:
            row = db.query(AuditLog).filter_by(acao="usuario.alterado").one()
            self.assertEqual((row.usuario_id, row.entidade, row.entidade_id), (self.admin_id, "usuario", str(self.client_id)))
            self.assertEqual(row.detalhes, {"campos": ["email", "nome"]})
            self.assertNotIn("changed@example.com", json.dumps(row.detalhes))
        asgi_request(self.app, "PUT", f"/users/{self.client_id}", {"nome": "Private Fixture Name"},
                     headers={"Authorization": f"Bearer {token}"})
        with main.SessionLocal() as db:
            self.assertEqual(db.query(AuditLog).filter_by(acao="usuario.alterado").count(), 1)

    def test_inactive_and_blocked_login_failures_keep_actor_reason_and_role(self):
        for field, reason, expected_status in (("ativo", "conta_inativa", 401), ("bloqueado", "conta_bloqueada", 403)):
            with main.SessionLocal() as db:
                user = db.get(User, self.client_id)
                user.ativo, user.bloqueado = True, False
                setattr(user, field, field == "bloqueado")
                db.commit()
            status, _ = asgi_request(self.app, "POST", "/auth/login", {"email": "client@example.com", "senha": "audit-password"})
            self.assertEqual(status, expected_status)
            with main.SessionLocal() as db:
                row = db.query(AuditLog).filter_by(acao="auth.login").order_by(AuditLog.id.desc()).first()
                self.assertEqual((row.usuario_id, row.ator_role, row.resultado, row.detalhes),
                                 (self.client_id, "cliente", "falha", {"motivo": reason}))

    def test_admin_block_and_unblock_record_actor_target_and_metadata(self):
        token = self.login("admin@example.com")
        for blocked, action in ((True, "usuario.bloqueado"), (False, "usuario.desbloqueado")):
            status, _ = asgi_request(self.app, "PUT", f"/users/{self.client_id}", {"bloqueado": blocked},
                                     headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(status, 200)
            with main.SessionLocal() as db:
                row = db.query(AuditLog).filter_by(acao=action).one()
                self.assertEqual((row.usuario_id, row.ator_role, row.entidade_id, row.ip),
                                 (self.admin_id, "admin", str(self.client_id), "127.0.0.1"))
                self.assertIsNotNone(row.ocorrido_em)
                self.assertEqual(row.detalhes, {})

    def test_barber_cannot_query_audit_and_persistence_failure_logs_no_private_error(self):
        self.add_user("barber@example.com", RoleEnum.BARBEIRO)
        token = access_token_for_user("barber@example.com")
        self.assertEqual(asgi_request(self.app, "GET", "/admin/auditoria",
                         headers={"Authorization": f"Bearer {token}"})[0], 403)
        with self.assertLogs("security.audit", level="WARNING") as captured, patch(
            "app.core.audit.AuditLog", side_effect=RuntimeError("fixture-private-credential")):
            status, _ = asgi_request(self.app, "POST", "/auth/register", {
                "nome": "Fixture", "email": "safe-failure@example.com", "senha": "audit-password",
                "consentimento_lgpd": True})
        self.assertEqual(status, 201)
        self.assertNotIn("fixture-private-credential", " ".join(captured.output))
        event = json.loads(captured.records[0].getMessage())
        self.assertEqual(event["event"], "audit_persist_failed")
        self.assertTrue(event["request_id"])

    def test_period_action_actor_entity_filters_and_stable_pagination(self):
        from datetime import datetime
        token = self.login("admin@example.com")
        instant = datetime(2030, 1, 2, 12)
        with main.SessionLocal() as db:
            for when, actor in ((instant - timedelta(seconds=1), self.admin_id),
                                (instant, self.admin_id), (instant, self.admin_id),
                                (instant + timedelta(seconds=1), self.admin_id), (instant, self.client_id)):
                db.add(AuditLog(usuario_id=actor, ator_role="admin", acao="period.fixture", entidade="fixture",
                                resultado="sucesso", detalhes={}, ocorrido_em=when))
            db.commit()
            expected = [row.id for row in db.query(AuditLog).filter_by(acao="period.fixture", usuario_id=self.admin_id,
                        ocorrido_em=instant).order_by(AuditLog.id.desc())]
        base = f"/admin/auditoria?usuario={self.admin_id}&acao=period.fixture&entidade=fixture&de=2030-01-02T12:00:00&ate=2030-01-02T12:00:00&limit=1"
        pages = []
        for skip in (0, 1):
            status, body = asgi_request(self.app, "GET", base + f"&skip={skip}", headers={"Authorization": f"Bearer {token}"})
            self.assertEqual(status, 200)
            self.assertEqual((body["total"], body["skip"], body["limit"]), (2, skip, 1))
            pages.extend(row["id"] for row in body["items"])
        self.assertEqual(pages, expected)
        for suffix, expected_status in (("?de=2030-01-03&ate=2030-01-01", 400), ("?skip=-1", 422), ("?limit=201", 422)):
            self.assertEqual(asgi_request(self.app, "GET", "/admin/auditoria" + suffix,
                            headers={"Authorization": f"Bearer {token}"})[0], expected_status)

    def test_record_stores_required_metadata_and_filters_secret_fields(self):
        from starlette.requests import Request
        from app.core.audit import record
        from datetime import datetime
        instant = datetime(2030, 1, 2, 12)
        request = Request({"type": "http", "client": ("203.0.113.9", 1234), "headers": []})
        with main.SessionLocal() as db, patch("app.core.audit.utc_now_naive", return_value=instant), patch.dict(os.environ, {"CLIENT_IP_SOURCE": "direct"}):
            actor = db.get(User, self.admin_id)
            record(db, request, actor=actor, acao="fixture.metadata", entidade="fixture", entidade_id=42,
                   detalhes={"status": "confirmado", "password": "fixture-password", "token": "fixture-token",
                             "BREVO_API_KEY": "fixture-brevo-secret", "SECRET_KEY": "fixture-secret",
                             "DATABASE_URL": "fixture-connection", "api-key": "fixture-api-key"})
            db.commit()
            row = db.query(AuditLog).filter_by(acao="fixture.metadata").one()
            self.assertEqual((row.usuario_id, row.ator_role, row.entidade_id, row.ip, row.ocorrido_em),
                             (self.admin_id, "admin", "42", "203.0.113.9", instant))
            self.assertEqual(row.detalhes, {"status": "confirmado"})

    def test_period_normalizes_offset_and_naive_utc_before_comparison(self):
        from datetime import datetime
        token = self.login("admin@example.com")
        with main.SessionLocal() as db:
            db.add(AuditLog(usuario_id=self.admin_id, acao="offset.fixture", entidade="fixture",
                            resultado="sucesso", detalhes={}, ocorrido_em=datetime(2030, 1, 2, 12)))
            db.commit()
        auth = {"Authorization": f"Bearer {token}"}
        status, body = asgi_request(self.app, "GET",
            "/admin/auditoria?acao=offset.fixture&de=2030-01-02T09:00:00-03:00&ate=2030-01-02T12:00:00", headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(body["total"], 1)
        status, _ = asgi_request(self.app, "GET",
            "/admin/auditoria?de=2030-01-02T13:00:00Z&ate=2030-01-02T12:00:00", headers=auth)
        self.assertEqual(status, 400)

    def test_retention_real_purge_preserves_exact_boundary_and_recent_events(self):
        from datetime import datetime
        instant = datetime(2030, 2, 1, 12)
        cutoff = instant - timedelta(days=30)
        with main.SessionLocal() as db:
            for when in (cutoff - timedelta(microseconds=1), cutoff, instant):
                db.add(AuditLog(acao="retention.fixture", entidade="fixture", resultado="sucesso", detalhes={}, ocorrido_em=when))
            db.commit()
        with patch.dict(os.environ, {"RETENTION_DAYS": "30"}), patch("app.maintenance.utc_now_naive", return_value=instant), redirect_stdout(StringIO()):
            # Restrict assertions to the three controlled rows; login rows may also expire.
            purge_audit(dry_run=True)
            with main.SessionLocal() as db:
                self.assertEqual(db.query(AuditLog).filter_by(acao="retention.fixture").count(), 3)
            purge_audit()
        with main.SessionLocal() as db:
            rows = db.query(AuditLog).filter_by(acao="retention.fixture").order_by(AuditLog.ocorrido_em).all()
            self.assertEqual([row.ocorrido_em for row in rows], [cutoff, instant])
