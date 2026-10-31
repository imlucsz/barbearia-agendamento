import hashlib
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from fastapi import Response

from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.clock import utc_now_naive
from app.core.security import get_password_hash
from app.models.user import ConsentimentoLGPD, RefreshToken, RoleEnum, User
from app.routers.auth import _set_refresh_cookie


class AuthenticationSessionTests(unittest.TestCase):
    def test_email_identity_ignores_case_and_outer_whitespace(self):
        self.create_user("Mixed.Case@example.com")
        status, body, _ = self.login("  MIXED.CASE@EXAMPLE.COM  ")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["user"]["email"], "mixed.case@example.com")
        status, _ = asgi_request(self.application, "POST", "/auth/register", {
            "nome": "Duplicata", "email": "Mixed.Case@example.com", "senha": "client-pass-123", "consentimento_lgpd": True,
        })
        self.assertEqual(status, 400)
        with patch("app.routers.auth.send_password_reset_email") as send:
            status, _ = asgi_request(self.application, "POST", "/auth/esqueci-senha", {"email": " MIXED.CASE@EXAMPLE.COM "})
            self.assertEqual(status, 200)
            self.assertEqual(send.call_args.args[0], "mixed.case@example.com")

    def setUp(self):
        reset_database()
        self.app_module = load_app_for_environment("development")
        self.application = self.app_module.app
        os.environ["CLIENT_IP_SOURCE"] = "direct"
        os.environ["TERMS_VERSION"] = "terms-test-7"
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://frontend.test.invalid"
        self.origin = "https://frontend.test.invalid"

    def create_user(self, email, role=RoleEnum.CLIENTE, password="session-password"):
        db = main.SessionLocal()
        try:
            user = User(
                nome=email.split("@")[0], email=email,
                senha_hash=get_password_hash(password), role=role,
                consentimento_lgpd=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id
        finally:
            db.close()

    def login(self, email, password="session-password"):
        return asgi_request(
            self.application, "POST", "/auth/login",
            {"email": email, "senha": password}, return_headers=True,
        )

    def refresh(self, raw_token, origin=None):
        headers = {"Cookie": f"refresh_token={raw_token}"}
        if origin is not None:
            headers["Origin"] = origin
        return asgi_request(
            self.application, "POST", "/auth/refresh", headers=headers,
            return_headers=True,
        )

    def test_registration_records_versioned_consent_and_login_issues_hashed_cookie_token(self):
        status, _body = asgi_request(
            self.application, "POST", "/auth/register",
            {"nome": "Consent QA", "email": "consent@example.com", "senha": "client-pass-123", "consentimento_lgpd": True},
            headers={"Origin": self.origin},
        )
        self.assertEqual(status, 201, _body)
        db = main.SessionLocal()
        try:
            consent = db.query(ConsentimentoLGPD).one()
            self.assertEqual(consent.versao_termos, "terms-test-7")
            self.assertEqual(consent.ip_origem, "127.0.0.1")
            self.assertEqual(consent.origem, self.origin)
            self.assertIsNotNone(consent.aceito_em)
        finally:
            db.close()

        status, body, headers = self.login("consent@example.com", "client-pass-123")
        self.assertEqual(status, 200, body)
        raw_token = body["refresh_token"]
        self.assertIn(raw_token, headers["set-cookie"])
        self.assertIn("httponly", headers["set-cookie"].lower())
        self.assertIn("samesite=lax", headers["set-cookie"].lower())
        self.assertIn("path=/auth", headers["set-cookie"].lower())
        db = main.SessionLocal()
        try:
            stored = db.query(RefreshToken).one()
            self.assertEqual(stored.token_hash, hashlib.sha256(raw_token.encode()).hexdigest())
            self.assertNotEqual(stored.token_hash, raw_token)
        finally:
            db.close()

    def test_refresh_rotates_token_and_reuse_revokes_the_family(self):
        self.create_user("rotate@example.com")
        status, body, _headers = self.login("rotate@example.com")
        self.assertEqual(status, 200, body)
        first = body["refresh_token"]

        status, _body, headers = self.refresh(first, self.origin)
        self.assertEqual(status, 200)
        second = headers["set-cookie"].split("refresh_token=", 1)[1].split(";", 1)[0]
        self.assertNotEqual(first, second)

        status, _body, _headers = self.refresh(first, self.origin)
        self.assertEqual(status, 401)
        status, _body, _headers = self.refresh(second, self.origin)
        self.assertEqual(status, 401)
        db = main.SessionLocal()
        try:
            self.assertTrue(all(row.revoked_at is not None for row in db.query(RefreshToken).all()))
        finally:
            db.close()

    def test_logout_revokes_refresh_token(self):
        self.create_user("logout@example.com")
        status, body, _headers = self.login("logout@example.com")
        token = body["refresh_token"]
        status, _body, headers = asgi_request(
            self.application, "POST", "/auth/logout", headers={
                "Cookie": f"refresh_token={token}", "Origin": self.origin,
            }, return_headers=True,
        )
        self.assertEqual(status, 200)
        self.assertIn("max-age=0", headers["set-cookie"].lower())
        self.assertEqual(self.refresh(token, self.origin)[0], 401)

    def test_expired_refresh_token_is_rejected(self):
        self.create_user("expired@example.com")
        _status, body, _headers = self.login("expired@example.com")
        db = main.SessionLocal()
        try:
            row = db.query(RefreshToken).one()
            row.expires_at = utc_now_naive() - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()
        self.assertEqual(self.refresh(body["refresh_token"], self.origin)[0], 401)

    def test_blocking_client_revokes_refresh_tokens(self):
        client_id = self.create_user("blocked@example.com")
        self.create_user("admin@example.com", RoleEnum.ADMIN)
        _status, client_login, _headers = self.login("blocked@example.com")
        _status, admin_login, _headers = self.login("admin@example.com")
        status, _body = asgi_request(
            self.application, "PUT", f"/users/{client_id}", {"bloqueado": True},
            headers={"Authorization": f"Bearer {admin_login['access_token']}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.refresh(client_login["refresh_token"], self.origin)[0], 401)
        db = main.SessionLocal()
        try:
            self.assertTrue(all(row.revoked_at is not None for row in db.query(RefreshToken).filter_by(user_id=client_id)))
        finally:
            db.close()

    def test_password_reset_revokes_refresh_tokens(self):
        self.create_user("password-change@example.com", password="old-pass-123")
        _status, login_body, _headers = self.login("password-change@example.com", "old-pass-123")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            asgi_request(self.application, "POST", "/auth/esqueci-senha", {"email": "password-change@example.com"})
        status, _body = asgi_request(
            self.application, "POST", "/auth/redefinir-senha",
            {"token": sender.call_args.args[1], "nova_senha": "new-pass-123"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.refresh(login_body["refresh_token"], self.origin)[0], 401)

    def test_account_deactivation_revokes_refresh_tokens(self):
        user_id = self.create_user("deactivate@example.com")
        _status, login_body, _headers = self.login("deactivate@example.com")
        status, _body = asgi_request(
            self.application, "DELETE", "/users/me",
            {"senha_atual": "session-password"},
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.refresh(login_body["refresh_token"], self.origin)[0], 401)
        db = main.SessionLocal()
        try:
            erased_tokens = db.query(RefreshToken).filter(RefreshToken.token_hash.is_not(None)).all()
            self.assertTrue(any(row.user_id is None and row.revoked_at is not None for row in erased_tokens))
        finally:
            db.close()

    def test_refresh_and_logout_reject_unlisted_origin(self):
        self.create_user("csrf@example.com")
        _status, body, _headers = self.login("csrf@example.com")
        self.assertEqual(self.refresh(body["refresh_token"], "https://attacker.invalid")[0], 403)
        status, _body = asgi_request(
            self.application, "POST", "/auth/logout",
            headers={"Cookie": f"refresh_token={body['refresh_token']}", "Origin": "https://attacker.invalid"},
        )
        self.assertEqual(status, 403)

    def test_refresh_cookie_is_secure_only_in_production(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}):
            development = Response()
            _set_refresh_cookie(development, "dev-token")
        self.assertNotIn("secure", development.headers["set-cookie"].lower())

        with patch.dict(os.environ, {"APP_ENV": "production"}):
            production = Response()
            _set_refresh_cookie(production, "prod-token")
        self.assertIn("secure", production.headers["set-cookie"].lower())


if __name__ == "__main__":
    unittest.main()
