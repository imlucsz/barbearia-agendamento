import json
import os
import secrets
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from support import TEST_SECRET_KEY, asgi_request, load_app_for_environment
from app.core.security import ALGORITHM, create_access_token, decode_access_token
from app.core.clock import utc_now
import jwt


_UNSET = object()
_BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_app_import(secret_key=_UNSET, app_env="production"):
    with tempfile.TemporaryDirectory(prefix="barbearia-jwt-config-") as temp_dir:
        env = os.environ.copy()
        env["APP_ENV"] = app_env
        env["DATABASE_URL"] = "postgresql+psycopg://unit_test:unit_test@127.0.0.1:55432/barbearia_test"
        env["CORS_ALLOWED_ORIGINS"] = "https://unit-test.example"
        env["SMTP_HOST"] = "smtp.example.test"
        env["SMTP_FROM"] = "no-reply@example.test"
        env["PASSWORD_RESET_URL"] = "https://unit-test.example/frontend/pages/reset.html"
        env["SCHEDULING_TIMEZONE"] = "America/Sao_Paulo"
        env["SMTP_USERNAME"] = ""
        env["SMTP_PASSWORD"] = ""
        env["PYTHON_DOTENV_DISABLED"] = "1"
        env.pop("SECRET_KEY", None)
        env["DATABASE_URL"] += "?sslmode=require"
        if secret_key is not _UNSET:
            env["SECRET_KEY"] = secret_key

        return subprocess.run(
            [
                sys.executable,
                "-c",
                "import app.main",
            ],
            cwd=_BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


class JwtConfigurationTests(unittest.TestCase):
    def test_valid_explicit_key_allows_production_application_initialization(self):
        production_key = secrets.token_urlsafe(48)
        result = run_app_import(production_key)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(production_key, result.stdout + result.stderr)

    def test_missing_and_empty_key_are_rejected_without_revealing_a_value(self):
        for candidate in (_UNSET, ""):
            with self.subTest(candidate="missing" if candidate is _UNSET else "empty"):
                result = run_app_import(candidate)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("SECRET_KEY", output)
                self.assertNotIn("barbearia-dev-secret-key", output)

    def test_missing_key_has_no_development_fallback(self):
        result = run_app_import(_UNSET, app_env="development")
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", output)
        self.assertNotIn("barbearia-dev-secret-key", output)

    def test_placeholder_and_predictable_keys_are_rejected_in_production(self):
        candidates = (
            "replace-this-with-a-long-random-secret",
            "example-secret-key-" + "z" * 40,
            "barbearia-dev-secret-key",
            "a" * 48,
            "abcdefghij" * 5,
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate[:12]):
                result = run_app_import(candidate)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("SECRET_KEY", output)
                self.assertNotIn(candidate, output)

    def test_configured_key_signs_and_verifies_tokens_but_another_key_does_not(self):
        self.assertEqual(os.environ["SECRET_KEY"], TEST_SECRET_KEY)
        token = create_access_token({"sub": "qa-user@example.test"})
        self.assertEqual(decode_access_token(token)["sub"], "qa-user@example.test")

        wrong_key = "different-test-signing-key-that-is-not-configured"
        wrong_token = jwt.encode(
            {
                "sub": "qa-user@example.test",
                "exp": utc_now() + timedelta(minutes=5),
            },
            wrong_key,
            algorithm=ALGORITHM,
        )
        with self.assertRaises(ValueError):
            decode_access_token(wrong_token)

    def test_signed_token_without_expiration_is_rejected_by_decoder_and_endpoint(self):
        token_without_exp = jwt.encode(
            {"sub": "qa-user@example.test"},
            TEST_SECRET_KEY,
            algorithm=ALGORITHM,
        )

        with self.assertRaises(ValueError):
            decode_access_token(token_without_exp)

        application = load_app_for_environment("production").app
        status, body = asgi_request(
            application,
            "GET",
            "/auth/me",
            headers={"Authorization": f"Bearer {token_without_exp}"},
        )
        self.assertEqual(status, 401)
        self.assertIn("Token", body["detail"])

    def test_invalid_signature_error_response_does_not_reveal_either_key(self):
        previous_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS")
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://unit-test.example"
        try:
            application = load_app_for_environment("production").app
        finally:
            if previous_cors_origins is None:
                os.environ.pop("CORS_ALLOWED_ORIGINS", None)
            else:
                os.environ["CORS_ALLOWED_ORIGINS"] = previous_cors_origins
        wrong_key = "different-test-signing-key-that-is-not-configured"
        wrong_token = jwt.encode(
            {
                "sub": "qa-user@example.test",
                "exp": utc_now() + timedelta(minutes=5),
            },
            wrong_key,
            algorithm=ALGORITHM,
        )
        status, body = asgi_request(
            application,
            "GET",
            "/auth/me",
            headers={"Authorization": f"Bearer {wrong_token}"},
        )

        response = json.dumps(body)
        self.assertEqual(status, 401)
        self.assertNotIn(TEST_SECRET_KEY, response)
        self.assertNotIn(wrong_key, response)


if __name__ == "__main__":
    unittest.main()
