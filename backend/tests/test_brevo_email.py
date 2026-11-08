import http.client
import json
import secrets
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from support import asgi_request, load_app_for_environment, main, reset_database
from test_configuration import valid_production_environment
from app.config import load_settings
from app.core.email import EmailDeliveryError, send_password_reset_email
from app.core.clock import utc_now_naive
from app.core.security import get_password_hash
from app.models.user import PasswordResetToken, User


def brevo_environment():
    values = {key: value for key, value in valid_production_environment().items() if not key.startswith("SMTP_")}
    values.update(EMAIL_TRANSPORT="brevo_api", BREVO_API_KEY=secrets.token_urlsafe(32),
                  EMAIL_FROM="sender@example.test")
    return values


class BrevoConfigurationTests(unittest.TestCase):
    def test_repository_email_configuration_contains_no_brevo_credentials(self):
        root = Path(__file__).resolve().parents[2]
        key_pattern = re.compile(r"xkeysib-" + r"[A-Za-z0-9_-]{40,}")
        for filename in ("render.yaml", "backend/app/config.py", "backend/app/core/email.py",
                         "backend/tests/test_brevo_email.py", "README.md", "docs/REQUISITOS_STATUS.md"):
            content = (root / filename).read_text(encoding="utf-8")
            self.assertFalse(key_pattern.search(content), filename)
        blueprint = (root / "render.yaml").read_text(encoding="utf-8")
        self.assertRegex(blueprint, r"key: BREVO_API_KEY\s+sync: false")
        self.assertNotRegex(blueprint, r"key: BREVO_API_KEY\s+value:")

    def test_production_brevo_needs_no_smtp_and_hides_key(self):
        values = brevo_environment()
        values.update(SMTP_PORT="unused", SMTP_TIMEOUT_SECONDS="unused", SMTP_USERNAME="unused")
        configuration = load_settings(values)
        self.assertEqual(configuration.email_transport, "brevo_api")
        self.assertNotIn(values["BREVO_API_KEY"], repr(configuration))
        self.assertEqual(load_settings(valid_production_environment()).email_transport, "smtp")

    def test_required_brevo_values_and_production_reset_origin(self):
        for field in ("BREVO_API_KEY", "EMAIL_FROM", "PASSWORD_RESET_URL"):
            values = brevo_environment()
            values.pop(field)
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                load_settings(values)
        for field, value in (("EMAIL_TRANSPORT", "disabled"), ("EMAIL_FROM", "bad\naddress"),
                             ("BREVO_API_KEY", "key\nvalue"), ("BREVO_API_KEY", "non-ascii-ç"),
                             ("EMAIL_TIMEOUT_SECONDS", "nan"), ("EMAIL_TIMEOUT_SECONDS", "0"),
                             ("EMAIL_TIMEOUT_SECONDS", "later"), ("EMAIL_TIMEOUT_SECONDS", "121"),
                             ("EMAIL_FROM", "Sender <sender@example.test>"),
                             ("PASSWORD_RESET_URL", "https://other.example.test/pages/reset.html"),
                             ("PASSWORD_RESET_URL", "http://barbearia.example.test/pages/reset.html")):
            values = brevo_environment()
            values[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError) as raised:
                load_settings(values)
            self.assertNotIn(values["BREVO_API_KEY"], str(raised.exception))


class BrevoDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.values = brevo_environment()
        self.config = load_settings(self.values)
        self.settings_patch = patch("app.core.email.load_app_settings", return_value=self.config)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_official_https_request_and_fragment_without_smtp(self):
        with patch("app.core.email.http.client.HTTPSConnection") as factory, patch("app.core.email.smtplib.SMTP") as smtp:
            connection = factory.return_value
            connection.getresponse.return_value.status = 201
            send_password_reset_email("client@example.test", "private-token")
        factory.assert_called_once_with("api.brevo.com", timeout=10)
        call = connection.request.call_args
        self.assertEqual(call.args, ("POST", "/v3/smtp/email"))
        self.assertEqual(call.kwargs["headers"]["api-key"], self.values["BREVO_API_KEY"])
        payload = json.loads(call.kwargs["body"])
        self.assertEqual(payload["sender"], {"email": "sender@example.test"})
        self.assertEqual(payload["to"], [{"email": "client@example.test"}])
        link = next(line for line in payload["textContent"].splitlines() if line.startswith("https://"))
        self.assertEqual(parse_qs(urlsplit(link).fragment), {"token": ["private-token"]})
        self.assertFalse(urlsplit(link).query)
        self.assertNotIn(self.values["BREVO_API_KEY"], payload["textContent"])
        connection.close.assert_called_once()
        connection.getresponse.return_value.read.assert_not_called()
        smtp.assert_not_called()

    def test_api_errors_timeouts_and_redirects_are_sanitized_without_retry(self):
        for status in (301, 400, 401, 429, 500):
            with self.subTest(status=status), patch("app.core.email.http.client.HTTPSConnection") as factory:
                connection = factory.return_value
                connection.getresponse.return_value.status = status
                with self.assertRaises(EmailDeliveryError) as raised:
                    send_password_reset_email("client@example.test", "private-token")
                self.assertNotIn(self.values["BREVO_API_KEY"], str(raised.exception))
                connection.request.assert_called_once()
                connection.close.assert_called_once()
        for failure in (TimeoutError("private-token"), http.client.HTTPException(self.values["BREVO_API_KEY"])):
            with patch("app.core.email.http.client.HTTPSConnection") as factory:
                factory.return_value.request.side_effect = failure
                with self.assertRaises(EmailDeliveryError) as raised:
                    send_password_reset_email("client@example.test", "private-token")
                self.assertNotIn("private-token", str(raised.exception))
                self.assertTrue(raised.exception.__suppress_context__)
                factory.return_value.close.assert_called_once()

    def test_recovery_rate_limit_still_blocks_repeated_requests(self):
        reset_database()
        application = load_app_for_environment("development").app
        with patch("app.core.email.http.client.HTTPSConnection") as factory:
            for _ in range(4):
                self.assertEqual(asgi_request(application, "POST", "/auth/esqueci-senha", {"email": "unknown@example.com"})[0], 200)
            self.assertEqual(asgi_request(application, "POST", "/auth/esqueci-senha", {"email": "unknown@example.com"})[0], 429)
            factory.assert_not_called()

    def test_recovery_with_brevo_preserves_expiry_invalidation_rollback_and_single_use(self):
        reset_database()
        application = load_app_for_environment("development").app
        with main.SessionLocal() as db:
            db.add(User(nome="Cliente", email="client@example.com", senha_hash=get_password_hash("old-password"), consentimento_lgpd=True))
            db.commit()
        tokens = []

        def request(method, path, **kwargs):
            payload = json.loads(kwargs["body"])
            link = next(line for line in payload["textContent"].splitlines() if line.startswith("https://"))
            tokens.append(parse_qs(urlsplit(link).fragment)["token"][0])

        def recover(address="client@example.com"):
            return asgi_request(application, "POST", "/auth/esqueci-senha", {"email": address})

        with patch("app.core.email.http.client.HTTPSConnection") as factory:
            connection = factory.return_value
            connection.request.side_effect = request
            connection.getresponse.return_value.status = 201
            first = recover()
            self.assertEqual(first[0], 200)
            self.assertEqual(first, recover("unknown@example.com"))
            recover()
            with main.SessionLocal() as db:
                rows = db.query(PasswordResetToken).order_by(PasswordResetToken.id).all()
                self.assertEqual([row.used for row in rows], [True, False])
                self.assertTrue(3590 < (rows[-1].expires_at - utc_now_naive()).total_seconds() <= 3600)
            connection.getresponse.return_value.status = 500
            self.assertEqual(first, recover())
            with main.SessionLocal() as db:
                rows = db.query(PasswordResetToken).order_by(PasswordResetToken.id).all()
                self.assertEqual([row.used for row in rows], [True, False])
        for token, expected in ((tokens[0], 400), (tokens[1], 200), (tokens[1], 400), (tokens[2], 400)):
            status, _ = asgi_request(application, "POST", "/auth/redefinir-senha", {"token": token, "nova_senha": "new-password"})
            self.assertEqual(status, expected)
