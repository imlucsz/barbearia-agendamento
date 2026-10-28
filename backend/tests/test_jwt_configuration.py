import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from support import TEST_SECRET_KEY, asgi_request, load_app_for_environment
from app.core.security import ALGORITHM, create_access_token, decode_access_token
from app.core.clock import utc_now
from jose import jwt


_UNSET = object()
_BACKEND_DIR = Path(__file__).resolve().parents[1]


def run_app_import(secret_key=_UNSET, app_env="production"):
    with tempfile.TemporaryDirectory(prefix="barbearia-jwt-config-") as temp_dir:
        database_path = (Path(temp_dir) / "startup-test.db").as_posix()
        env = os.environ.copy()
        env["APP_ENV"] = app_env
        env["DATABASE_URL"] = f"sqlite:///{database_path}"
        env["PYTHON_DOTENV_DISABLED"] = "1"
        env.pop("SECRET_KEY", None)
        if secret_key is not _UNSET:
            env["SECRET_KEY"] = secret_key

        return subprocess.run(
            [sys.executable, "-c", "import app.main"],
            cwd=_BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


class JwtConfigurationTests(unittest.TestCase):
    def test_valid_explicit_key_allows_production_application_initialization(self):
        result = run_app_import(TEST_SECRET_KEY)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(TEST_SECRET_KEY, result.stdout + result.stderr)

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

    def test_invalid_signature_error_response_does_not_reveal_either_key(self):
        application = load_app_for_environment("production").app
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
