from support import access_token_for_user
"""Route regressions on the harness's temporary database; no real email."""
import unittest
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import get_password_hash
from app.models.user import RoleEnum, User


class PersonNameFlowTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app

    def test_registration_normalizes_name_and_login_recovery_keep_contract(self):
        status, body = asgi_request(self.app, "POST", "/auth/register", {
            "nome": "  Jose\u0301\u00a0 da  Silva  ", "email": "  Mixed+tag@Example.COM  ",
            "senha": "  fixture-only  ", "consentimento_lgpd": True,
        })
        self.assertEqual(status, 201)
        self.assertEqual(body["nome"], "José da Silva")
        with main.SessionLocal() as db:
            row = db.query(User).one()
            self.assertTrue(row.email == "mixed+tag@example.com")
            original_hash = row.senha_hash
            self.assertEqual(row.nome, "José da Silva")
        status, _ = asgi_request(self.app, "POST", "/auth/login", {
            "email": " MIXED+tag@EXAMPLE.COM ", "senha": "  fixture-only  ",
        })
        self.assertEqual(status, 200)
        with patch("app.routers.auth.send_password_reset_email") as sender:
            known = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": " MIXED+tag@EXAMPLE.COM "})
            unknown = asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": "unknown@example.com"})
        self.assertEqual(known, unknown)
        self.assertEqual(sender.call_count, 1)
        with main.SessionLocal() as db:
            self.assertTrue(db.query(User).one().senha_hash == original_hash)

    def test_partial_update_does_not_rewrite_legacy_name_email_or_hash(self):
        legacy_name = "Jose\u0301  Legado"
        with main.SessionLocal() as db:
            admin = User(nome="Admin", email="admin@example.com", senha_hash="test", role=RoleEnum.ADMIN)
            client = User(nome=legacy_name, email="legacy@example.com", senha_hash=get_password_hash("fixture-only"), role=RoleEnum.CLIENTE)
            db.add_all([admin, client])
            db.commit()
            user_id, original_hash, email = client.id, client.senha_hash, client.email
        headers = {"Authorization": "Bearer " + access_token_for_user("admin@example.com")}
        status, body = asgi_request(self.app, "PUT", f"/users/{user_id}", {}, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(body["nome"], legacy_name)
        with main.SessionLocal() as db:
            row = db.query(User).filter_by(id=user_id).one()
            self.assertEqual(row.nome, legacy_name)
            self.assertTrue(row.email == email and row.senha_hash == original_hash)
        status, body = asgi_request(self.app, "PUT", f"/users/{user_id}", {"nome": " Ana\u2003  Mari\u0301a "}, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(body["nome"], "Ana María")
        with main.SessionLocal() as db:
            row = db.query(User).filter_by(id=user_id).one()
            self.assertTrue(row.email == email and row.senha_hash == original_hash)

    def test_login_and_recovery_do_not_rewrite_legacy_persisted_name(self):
        legacy_name = "Jose\u0301  Legado"
        with main.SessionLocal() as db:
            row = User(nome=legacy_name, email="legacy@example.com", senha_hash=get_password_hash("fixture-only"))
            db.add(row)
            db.commit()
            original_hash = row.senha_hash
        status, body = asgi_request(self.app, "POST", "/auth/login", {"email": "legacy@example.com", "senha": "fixture-only"})
        self.assertEqual(status, 200)
        self.assertEqual(body["user"]["nome"], legacy_name)
        with patch("app.routers.auth.send_password_reset_email"):
            self.assertEqual(asgi_request(self.app, "POST", "/auth/esqueci-senha", {"email": "legacy@example.com"})[0], 200)
        with main.SessionLocal() as db:
            row = db.query(User).one()
            self.assertEqual(row.nome, legacy_name)
            self.assertTrue(row.senha_hash == original_hash)
