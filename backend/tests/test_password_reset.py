import hashlib
import json
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

from support import asgi_request, load_app_for_environment, main, reset_database
from fastapi import FastAPI
from app.core.security import get_password_hash, verify_password
from app.models.user import PasswordResetToken, User
from app.core.clock import utc_now_naive
from app.core.email import send_password_reset_email


def asgi_post(application, path, payload):
    return asgi_request(application, "POST", path, payload)


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        self.app_module = load_app_for_environment("development")
        self.application = self.app_module.app
        self.assertIsInstance(self.application, FastAPI)
        self.assertIs(self.application, self.app_module.app)
        self.assertEqual(self.app_module.APP_ENV, "development")
        for key in (
            "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM",
            "PASSWORD_RESET_URL",
        ):
            os.environ.pop(key, None)
        os.environ["SMTP_PORT"] = "587"

    def create_user(self, email, password="old-password"):
        db = main.SessionLocal()
        try:
            user = User(
                nome=email.split("@")[0],
                email=email,
                senha_hash=get_password_hash(password),
                consentimento_lgpd=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id
        finally:
            db.close()

    def reset_token_count(self, user_id=None):
        db = main.SessionLocal()
        try:
            query = db.query(PasswordResetToken)
            if user_id is not None:
                query = query.filter(PasswordResetToken.user_id == user_id)
            return query.count()
        finally:
            db.close()

    def test_recovery_response_is_uniform_and_contains_no_secret(self):
        self.create_user("known@example.com")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            known_status, known_body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "known@example.com"}
            )
            unknown_status, unknown_body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "unknown@example.com"}
            )

        self.assertEqual((known_status, known_body), (unknown_status, unknown_body))
        self.assertNotIn("dev_token", known_body)
        self.assertNotIn("reset.html", json.dumps(known_body))
        self.assertEqual(sender.call_count, 1)
        raw_token = sender.call_args.args[1]
        self.assertNotIn(raw_token, json.dumps(known_body))

        db = main.SessionLocal()
        try:
            stored = db.query(PasswordResetToken).one()
            self.assertEqual(stored.token, hashlib.sha256(raw_token.encode()).hexdigest())
            self.assertNotEqual(stored.token, raw_token)
        finally:
            db.close()

    def test_invalid_and_expired_tokens_are_rejected(self):
        user_id = self.create_user("person@example.com")
        expired_token = "expired-reset-token"
        db = main.SessionLocal()
        try:
            db.add(PasswordResetToken(
                user_id=user_id,
                token=hashlib.sha256(expired_token.encode()).hexdigest(),
                expires_at=utc_now_naive() - timedelta(seconds=1),
                used=False,
            ))
            db.commit()
        finally:
            db.close()

        invalid_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": "not-a-token", "nova_senha": "new-password"},
        )
        expired_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": expired_token, "nova_senha": "new-password"},
        )
        self.assertEqual(invalid_status, 400)
        self.assertEqual(expired_status, 400)

    def test_only_valid_token_changes_its_account_and_token_cannot_be_reused(self):
        account_a = self.create_user("a@example.com", "old-password-a")
        account_b = self.create_user("b@example.com", "old-password-b")
        with patch("app.routers.auth.send_password_reset_email") as sender:
            asgi_post(self.application, "/auth/esqueci-senha", {"email": "a@example.com"})
        token = sender.call_args.args[1]

        status, body = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": token, "nova_senha": "new-password-a"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["mensagem"], "Senha redefinida com sucesso")

        retry_status, _ = asgi_post(
            self.application, "/auth/redefinir-senha",
            {"token": token, "nova_senha": "attacker-password"},
        )
        self.assertEqual(retry_status, 400)

        db = main.SessionLocal()
        try:
            updated_a = db.query(User).filter(User.id == account_a).one()
            unchanged_b = db.query(User).filter(User.id == account_b).one()
            self.assertTrue(verify_password("new-password-a", updated_a.senha_hash))
            self.assertFalse(verify_password("attacker-password", updated_a.senha_hash))
            self.assertTrue(verify_password("old-password-b", unchanged_b.senha_hash))
        finally:
            db.close()

    def test_failed_email_delivery_returns_generic_response_and_persists_no_token(self):
        user_id = self.create_user("known@example.com")
        with patch(
            "app.routers.auth.send_password_reset_email",
            side_effect=RuntimeError("mail unavailable"),
        ):
            status, body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "known@example.com"}
            )

        self.assertEqual(status, 200)
        self.assertEqual(body, {"mensagem": "Se o email existir, um link de redefinição foi gerado."})
        self.assertEqual(self.reset_token_count(user_id), 0)

    def test_test_or_production_environment_has_no_local_email_fallback(self):
        user_id = self.create_user("known@example.com")
        for app_env in (None, "production"):
            with self.subTest(app_env=app_env):
                app_module = load_app_for_environment(app_env)
                application = app_module.app
                self.assertIsInstance(application, FastAPI)
                self.assertIs(application, app_module.app)
                self.assertEqual(app_module.APP_ENV, app_env or "test")
                with patch("logging.Logger.info") as logger_info:
                    status, body = asgi_post(
                        application, "/auth/esqueci-senha",
                        {"email": "known@example.com"},
                    )
                self.assertEqual(status, 200)
                self.assertNotIn("dev_token", body)
                self.assertEqual(self.reset_token_count(user_id), 0)
                logger_info.assert_not_called()

    def test_validation_errors_do_not_echo_password_or_reset_token(self):
        secret_input = "xP@ss"
        status, body = asgi_post(
            self.application,
            "/auth/redefinir-senha",
            {"token": "private-reset-token", "nova_senha": secret_input},
        )

        self.assertEqual(status, 422)
        serialized = json.dumps(body)
        self.assertNotIn(secret_input, serialized)
        self.assertNotIn("private-reset-token", serialized)
        self.assertNotIn('"input"', serialized)
        self.assertNotIn('"ctx"', serialized)
        self.assertIn("loc", body["detail"][0])

    def test_password_reset_link_keeps_token_in_fragment_not_query(self):
        settings = {
            "APP_ENV": "development",
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "587",
            "SMTP_FROM": "barbearia@example.test",
            "PASSWORD_RESET_URL": "https://frontend.example/reset.html?campaign=dev&token=old#previous",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
        }
        with patch.dict(os.environ, settings), patch("app.core.email.smtplib.SMTP") as smtp_factory:
            send_password_reset_email("client@example.test", "test-reset-token")

        smtp = smtp_factory.return_value.__enter__.return_value
        message = smtp.send_message.call_args.args[0]
        body = message.get_content()
        link = next(line for line in body.splitlines() if line.startswith("https://"))
        self.assertIn("?campaign=dev#token=test-reset-token", link)
        self.assertNotIn("token=old", link)
        self.assertNotIn("&token=test-reset-token", link)

    def test_explicit_development_without_smtp_does_not_log_or_persist_token(self):
        user_id = self.create_user("local@example.com")
        with patch("logging.Logger.info") as logger_info:
            status, body = asgi_post(
                self.application, "/auth/esqueci-senha", {"email": "local@example.com"}
            )

        self.assertEqual(status, 200)
        self.assertNotIn("dev_token", body)
        self.assertEqual(self.reset_token_count(user_id), 0)
        logger_info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
