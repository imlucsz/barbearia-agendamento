import asyncio
import importlib
import os
import secrets
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import main


BACKEND_DIR = Path(__file__).resolve().parents[1]
_MISSING = object()


def _asgi_exchange(application, method, headers):
    messages = []
    sent_request = False

    async def receive():
        nonlocal sent_request
        if sent_request:
            return {"type": "http.disconnect"}
        sent_request = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "root_path": "",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    asyncio.run(application(scope, receive, send))
    status = next(item["status"] for item in messages if item["type"] == "http.response.start")
    response_headers = dict(
        (key.decode().lower(), value.decode())
        for item in messages
        if item["type"] == "http.response.start"
        for key, value in item.get("headers", [])
    )
    return status, response_headers


class ApplicationConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.previous_app_env = os.environ.get("APP_ENV", _MISSING)
        self.previous_origins = os.environ.get("CORS_ALLOWED_ORIGINS", _MISSING)
        os.environ["APP_ENV"] = "development"
        os.environ["CORS_ALLOWED_ORIGINS"] = "http://frontend.test"
        self.application = importlib.reload(main).app

    def tearDown(self):
        self._restore("APP_ENV", self.previous_app_env)
        self._restore("CORS_ALLOWED_ORIGINS", self.previous_origins)
        importlib.reload(main)

    @staticmethod
    def _restore(name, previous):
        if previous is _MISSING:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous

    def test_configured_origin_is_allowed_and_unlisted_origin_is_not(self):
        allowed_status, allowed_headers = _asgi_exchange(
            self.application,
            "GET",
            {"origin": "http://frontend.test"},
        )
        denied_status, denied_headers = _asgi_exchange(
            self.application,
            "GET",
            {"origin": "http://unlisted.test"},
        )

        self.assertEqual(allowed_status, 200)
        self.assertEqual(allowed_headers.get("access-control-allow-origin"), "http://frontend.test")
        self.assertEqual(allowed_headers.get("access-control-allow-credentials"), "true")
        self.assertEqual(denied_status, 200)
        self.assertNotIn("access-control-allow-origin", denied_headers)

    def test_preflight_is_accepted_for_configured_origin(self):
        status, headers = _asgi_exchange(
            self.application,
            "OPTIONS",
            {
                "origin": "http://frontend.test",
                "access-control-request-method": "GET",
                "access-control-request-headers": "authorization",
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://frontend.test")
        self.assertIn("GET", headers.get("access-control-allow-methods", ""))

    def test_development_defaults_to_the_documented_local_frontend_origin(self):
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        application = importlib.reload(main).app

        self.assertEqual(main.CORS_ALLOWED_ORIGINS, ["http://127.0.0.1:5500"])
        status, headers = _asgi_exchange(
            application,
            "GET",
            {"origin": "http://127.0.0.1:5500"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), "http://127.0.0.1:5500")

    def test_wildcard_origin_configuration_is_rejected(self):
        for origin in ("*", "https://*.dominio.example"):
            with self.subTest(origin=origin):
                os.environ["CORS_ALLOWED_ORIGINS"] = origin
                with self.assertRaises(RuntimeError):
                    main._configured_cors_origins()

    def test_default_ports_hostname_case_and_duplicates_are_normalized(self):
        os.environ["CORS_ALLOWED_ORIGINS"] = (
            " HTTPS://EXAMPLE.TEST:443/ , https://example.test, "
            "http://127.0.0.1:80, http://127.0.0.1, "
            "HTTP://[2001:0DB8:0:0::1]:80, http://[2001:db8::1] "
        )

        self.assertEqual(
            main._configured_cors_origins("development"),
            [
                "https://example.test",
                "http://127.0.0.1",
                "http://[2001:db8::1]",
            ],
        )

    def test_malformed_ports_are_rejected(self):
        for origin in ("https://example.test:not-a-port", "https://example.test:65536", "https://example.test:0"):
            with self.subTest(origin=origin):
                os.environ["CORS_ALLOWED_ORIGINS"] = origin
                with self.assertRaises(RuntimeError):
                    main._configured_cors_origins("development")

    def test_paths_queries_fragments_credentials_and_bad_schemes_are_rejected(self):
        invalid_origins = (
            "https://example.test/path",
            "https://example.test?query=1",
            "https://example.test#fragment",
            "https://user@example.test",
            "https://user:password@example.test",
            "ftp://example.test",
        )
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                os.environ["CORS_ALLOWED_ORIGINS"] = origin
                with self.assertRaises(RuntimeError):
                    main._configured_cors_origins("development")

    def test_http_is_allowed_in_development_but_not_production(self):
        os.environ["CORS_ALLOWED_ORIGINS"] = "http://127.0.0.1:5500"

        self.assertEqual(
            main._configured_cors_origins("development"),
            ["http://127.0.0.1:5500"],
        )
        with self.assertRaisesRegex(RuntimeError, "Production.*HTTPS"):
            main._configured_cors_origins("production")

        os.environ["CORS_ALLOWED_ORIGINS"] = "HTTPS://PRODUCTION.EXAMPLE:443"
        self.assertEqual(
            main._configured_cors_origins("production"),
            ["https://production.example"],
        )

    def test_published_environment_requires_explicit_cors_configuration(self):
        os.environ["APP_ENV"] = "production"
        os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        with self.assertRaisesRegex(RuntimeError, "explicitly configured in production"):
            main._configured_cors_origins("production")

    def test_empty_cors_configuration_fails_closed(self):
        os.environ["CORS_ALLOWED_ORIGINS"] = " ,  , "

        self.assertEqual(main._configured_cors_origins("development"), [])
        with self.assertRaisesRegex(RuntimeError, "at least one HTTPS origin"):
            main._configured_cors_origins("production")

    def _run_app_import(self, app_env):
        with tempfile.TemporaryDirectory(prefix="barbearia-app-config-") as temp_dir:
            env = os.environ.copy()
            env["APP_ENV"] = app_env
            env["PYTHON_DOTENV_DISABLED"] = "1"
            env["SECRET_KEY"] = "isolated-app-config-test-key-not-for-deployment"
            env.pop("DATABASE_URL", None)
            env["CORS_ALLOWED_ORIGINS"] = "https://unit-test.example"
            python_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(BACKEND_DIR) + (os.pathsep + python_path if python_path else "")
            return subprocess.run(
                [sys.executable, "-c", "import app.main; print(app.main.engine.dialect.name)"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def _run_database_import(self, app_env, database_url=None):
        with tempfile.TemporaryDirectory(prefix="barbearia-db-config-") as temp_dir:
            env = os.environ.copy()
            env["APP_ENV"] = app_env
            env["PYTHON_DOTENV_DISABLED"] = "1"
            env["SECRET_KEY"] = secrets.token_urlsafe(48)
            env["CORS_ALLOWED_ORIGINS"] = "https://unit-test.example"
            env["SMTP_HOST"] = "smtp.example.test"
            env["SMTP_FROM"] = "no-reply@example.test"
            env["PASSWORD_RESET_URL"] = "https://unit-test.example/frontend/pages/reset.html"
            env["SCHEDULING_TIMEZONE"] = "America/Sao_Paulo"
            env["SMTP_USERNAME"] = ""
            env["SMTP_PASSWORD"] = ""
            env.pop("DATABASE_URL", None)
            if database_url is not None:
                env["DATABASE_URL"] = database_url
            python_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(BACKEND_DIR) + (os.pathsep + python_path if python_path else "")
            return subprocess.run(
                [sys.executable, "-c", "import app.database; print(app.database.engine.dialect.name)"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def _run_production_import(self, overrides=None):
        with tempfile.TemporaryDirectory(prefix="barbearia-prod-config-") as temp_dir:
            env = os.environ.copy()
            env.update({
                "APP_ENV": "production",
                "DATABASE_URL": (
                    "postgresql+psycopg://app_user:fake-production-test-password@"
                    "127.0.0.1:5432/barbearia_test?sslmode=require"
                ),
                "SECRET_KEY": secrets.token_urlsafe(48),
                "CORS_ALLOWED_ORIGINS": "https://unit-test.example",
                "SCHEDULING_TIMEZONE": "America/Sao_Paulo",
                "SMTP_HOST": "smtp.example.test",
                "SMTP_FROM": "no-reply@example.test",
                "SMTP_USERNAME": "",
                "SMTP_PASSWORD": "",
                "PASSWORD_RESET_URL": "https://unit-test.example/frontend/pages/reset.html",
                "PYTHON_DOTENV_DISABLED": "1",
            })
            for name, value in (overrides or {}).items():
                if value is None:
                    env.pop(name, None)
                else:
                    env[name] = value
            python_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(BACKEND_DIR) + (os.pathsep + python_path if python_path else "")
            return subprocess.run(
                [sys.executable, "-c", "import app.main"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def test_development_without_database_url_initializes_with_local_sqlite(self):
        result = self._run_app_import("development")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "sqlite")

    def test_published_environment_without_database_url_fails_clearly(self):
        result = self._run_app_import("production")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL must be explicitly configured", result.stderr)
        self.assertNotIn("sqlite:///", result.stderr)

    def test_explicit_sqlite_database_url_is_rejected_in_production(self):
        sqlite_url = "sqlite:///./unit-test-only.db"
        result = self._run_database_import("production", sqlite_url)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SQLite DATABASE_URL is not allowed", result.stderr)
        self.assertNotIn(sqlite_url, result.stdout + result.stderr)

    def test_explicit_postgresql_database_url_is_accepted_without_connecting(self):
        postgres_url = "postgresql+psycopg://unit_test:fake-test-password@127.0.0.1:55432/barbearia_test?sslmode=require"
        result = self._run_database_import("production", postgres_url)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "postgresql")
        self.assertNotIn(postgres_url, result.stdout + result.stderr)

    def test_production_application_refuses_to_start_without_password_recovery_email(self):
        result = self._run_production_import({"SMTP_FROM": None})
        output = result.stdout + result.stderr

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SMTP_HOST", output)
        self.assertNotIn("fake-production-test-password", output)

    def test_env_variants_are_ignored_but_example_template_remains_trackable(self):
        repository_root = Path(__file__).resolve().parents[2]
        for path in (".env.local", "backend/.env.production"):
            with self.subTest(path=path):
                ignored = subprocess.run(
                    ["git", "check-ignore", "--quiet", "--no-index", path],
                    cwd=repository_root,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(ignored.returncode, 0)

        example = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", "backend/.env.example"],
            cwd=repository_root,
            capture_output=True,
            check=False,
        )
        self.assertEqual(example.returncode, 1)

        tracked = subprocess.run(
            ["git", "ls-files", "--cached", "-z"],
            cwd=repository_root,
            capture_output=True,
            check=True,
        ).stdout.decode().split("\0")
        tracked_env_files = [
            path for path in tracked
            if Path(path).name == ".env" or Path(path).name.startswith(".env.")
        ]
        self.assertEqual(tracked_env_files, ["backend/.env.example"])


if __name__ == "__main__":
    unittest.main()
