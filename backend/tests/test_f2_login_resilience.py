"""Reproducible F2 login failure regressions (temporary database harness)."""
# ruff: noqa: I001
# support configures the test database before app imports.
import os
import unittest
from http.cookies import SimpleCookie
from unittest.mock import patch
from support import asgi_request, load_app_for_environment, main, reset_database
from app.core.security import get_password_hash
from app.models.user import LoginAttempt, RefreshToken, RoleEnum, User


class F2LoginResilienceTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app = load_app_for_environment("test").app
        self.env = patch.dict(os.environ, {
            "CLIENT_IP_SOURCE": "direct",
            "CORS_ALLOWED_ORIGINS": "https://frontend.test.invalid",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        db = main.SessionLocal()
        try:
            db.add(User(
                nome="Conta Resilience", email="resilience@example.com",
                senha_hash=get_password_hash("fixture-password-only"),
                role=RoleEnum.CLIENTE, consentimento_lgpd=True,
            ))
            db.commit()
        finally:
            db.close()

    def login(self):
        return asgi_request(
            self.app, "POST", "/auth/login",
            {"email": "resilience@example.com", "senha": "fixture-password-only"},
            return_headers=True,
        )

    def refresh(self, raw):
        return asgi_request(
            self.app, "POST", "/auth/refresh",
            headers={"Cookie": "refresh_token=" + raw,
                     "Origin": "https://frontend.test.invalid"},
            return_headers=True,
        )

    @staticmethod
    def cookie_value(headers):
        cookies = SimpleCookie()
        cookies.load(headers["set-cookie"])
        return cookies["refresh_token"].value

    def test_claim_exception_does_not_commit_a_refresh_session(self):
        with patch("app.routers.auth.claim_login_reservation",
                   side_effect=RuntimeError("fixture failure")):
            status, _, headers = self.login()
        self.assertEqual(status, 503)
        self.assertNotIn("set-cookie", headers)
        db = main.SessionLocal()
        try:
            self.assertEqual(db.query(RefreshToken).count(), 0)
            self.assertEqual(db.query(LoginAttempt).count(), 1)
        finally:
            db.close()

    def test_finish_storage_failure_does_not_leave_an_unusable_session(self):
        with patch("app.core.login_rate_limit.finish",
                   side_effect=RuntimeError("fixture storage failure")) as finish:
            status, _, headers = self.login()
        self.assertEqual(status, 200)
        finish.assert_not_called()
        raw = self.cookie_value(headers)
        db = main.SessionLocal()
        try:
            attempt = db.query(LoginAttempt).one()
            self.assertEqual(attempt.resultado, "sucesso")
            self.assertEqual(
                db.query(RefreshToken).count(), 1,
                "The successful response must match exactly one committed refresh session",
            )
        finally:
            db.close()

        self.assertEqual(self.refresh(raw)[0], 200)
