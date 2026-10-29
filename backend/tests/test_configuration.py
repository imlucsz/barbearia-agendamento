import secrets
import unittest

from app.config import load_settings


def valid_production_environment():
    return {
        "APP_ENV": "production",
        "DATABASE_URL": "postgresql+psycopg://app_user:fake-test-password@127.0.0.1:5432/barbearia_test",
        "SECRET_KEY": secrets.token_urlsafe(48),
        "CORS_ALLOWED_ORIGINS": "https://barbearia.example.test",
        "SMTP_HOST": "smtp.example.test",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "no-reply@example.test",
        "SMTP_TIMEOUT_SECONDS": "10",
        "PASSWORD_RESET_URL": "https://barbearia.example.test/frontend/pages/reset.html",
        "SCHEDULING_TIMEZONE": "America/Sao_Paulo",
    }


class ApplicationSettingsTests(unittest.TestCase):
    def test_metrics_token_is_optional_but_must_be_long_and_non_whitespace(self):
        values = valid_production_environment()
        self.assertEqual(load_settings(values).metrics_token, "")
        values["METRICS_TOKEN"] = "m" * 40
        self.assertEqual(load_settings(values).metrics_token, "m" * 40)
        self.assertNotIn(values["METRICS_TOKEN"], repr(load_settings(values)))
        for invalid in ("short", "has whitespace" + "x" * 40):
            with self.subTest(token_length=len(invalid)):
                candidate = valid_production_environment()
                candidate["METRICS_TOKEN"] = invalid
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)

    def test_audit_retention_defaults_and_bounds_are_validated(self):
        values = valid_production_environment()
        self.assertEqual(load_settings(values).retention_days, 365)
        values["RETENTION_DAYS"] = "30"
        self.assertEqual(load_settings(values).retention_days, 30)
        for invalid in ("0", "36501", "later"):
            with self.subTest(retention=invalid):
                candidate = valid_production_environment()
                candidate["RETENTION_DAYS"] = invalid
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)

    def test_valid_production_configuration_is_explicit_and_secret_safe(self):
        values = valid_production_environment()
        loaded = load_settings(values)

        self.assertEqual(loaded.app_env, "production")
        self.assertEqual(loaded.database_backend, "postgresql")
        self.assertEqual(loaded.cors_allowed_origins, ("https://barbearia.example.test",))
        self.assertEqual(loaded.smtp_host, "smtp.example.test")
        rendered = repr(loaded)
        self.assertNotIn(values["SECRET_KEY"], rendered)
        self.assertNotIn("fake-test-password", rendered)
        self.assertNotIn("PASSWORD_RESET_URL", rendered)

    def test_installation_name_is_per_installation_and_bounded(self):
        values = valid_production_environment()
        values["INSTALLATION_NAME"] = "Barbearia Aurora"
        self.assertEqual(load_settings(values).installation_name, "Barbearia Aurora")
        for invalid in ("", "x" * 81, "Shop\nInjected"):
            candidate = valid_production_environment()
            candidate["INSTALLATION_NAME"] = invalid
            with self.subTest(name=invalid[:10]), self.assertRaisesRegex(RuntimeError, "INSTALLATION_NAME"):
                load_settings(candidate)

    def test_development_defaults_to_local_sqlite_and_optional_email(self):
        loaded = load_settings({
            "APP_ENV": "development",
            "SECRET_KEY": "local-test-signing-key-that-is-not-a-real-secret",
        })

        self.assertEqual(loaded.database_url, "sqlite:///./barbearia.db")
        self.assertEqual(loaded.database_backend, "sqlite")
        self.assertEqual(loaded.cors_allowed_origins, ("http://127.0.0.1:5500",))
        self.assertEqual(loaded.smtp_host, "")
        self.assertEqual(loaded.access_token_expire_minutes, 15)
        self.assertEqual(loaded.terms_version, "1.0")
        self.assertEqual(loaded.trusted_proxy_count, 0)

    def test_production_requires_database_secret_cors_and_email(self):
        valid = valid_production_environment()
        required = (
            "APP_ENV",
            "DATABASE_URL",
            "SECRET_KEY",
            "CORS_ALLOWED_ORIGINS",
            "SCHEDULING_TIMEZONE",
            "SMTP_HOST",
            "SMTP_FROM",
            "PASSWORD_RESET_URL",
        )
        for name in required:
            with self.subTest(name=name):
                candidate = dict(valid)
                candidate.pop(name)
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)

    def test_weak_placeholder_and_test_keys_fail_without_echoing_values(self):
        for weak in (
            "replace-this-with-a-long-random-secret-0123456789",
            "example-secret-" + "x" * 40,
            "test-only-secret-" + "Z" * 40,
            "a" * 48,
        ):
            with self.subTest(candidate=weak[:12]):
                candidate = valid_production_environment()
                candidate["SECRET_KEY"] = weak
                with self.assertRaises(RuntimeError) as raised:
                    load_settings(candidate)
                self.assertNotIn(weak, str(raised.exception))

    def test_invalid_or_permissive_cors_is_rejected_in_production(self):
        for origin in ("*", "https://*.example.test", "http://barbearia.example.test", "https://user@example.test"):
            with self.subTest(origin=origin):
                candidate = valid_production_environment()
                candidate["CORS_ALLOWED_ORIGINS"] = origin
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)

    def test_bad_database_url_and_remote_postgres_without_tls_fail_without_echo(self):
        candidate = valid_production_environment()
        candidate["DATABASE_URL"] = (
            "postgresql+psycopg://db_user:db-password-marker@db.example.test:not-a-port/barbearia"
        )
        with self.assertRaises(RuntimeError) as raised:
            load_settings(candidate)
        self.assertNotIn("db-password-marker", str(raised.exception))

        candidate = valid_production_environment()
        candidate["DATABASE_URL"] = (
            "postgresql+psycopg://app_user:fake-test-password@db.example.test:5432/barbearia"
        )
        with self.assertRaisesRegex(RuntimeError, "sslmode"):
            load_settings(candidate)

    def test_incompatible_database_driver_is_rejected(self):
        candidate = valid_production_environment()
        candidate["DATABASE_URL"] = "mysql+pymysql://app_user:fake@localhost/barbearia"
        with self.assertRaisesRegex(RuntimeError, r"postgresql\+psycopg"):
            load_settings(candidate)

    def test_missing_or_incoherent_production_email_configuration_fails(self):
        candidate = valid_production_environment()
        candidate["SMTP_HOST"] = ""
        with self.assertRaisesRegex(RuntimeError, "SMTP_HOST"):
            load_settings(candidate)

        candidate = valid_production_environment()
        candidate["SMTP_USERNAME"] = "smtp-user"
        with self.assertRaisesRegex(RuntimeError, "SMTP_USERNAME and SMTP_PASSWORD"):
            load_settings(candidate)

        candidate = valid_production_environment()
        candidate["SMTP_PORT"] = "70000"
        with self.assertRaisesRegex(RuntimeError, "SMTP_PORT"):
            load_settings(candidate)

    def test_public_reset_url_must_match_https_frontend_origin(self):
        for reset_url in (
            "http://barbearia.example.test/frontend/pages/reset.html",
            "https://other.example.test/frontend/pages/reset.html",
            "https://barbearia.example.test/frontend/pages/reset.html?token=bad",
            "https://barbearia.example.test/frontend/pages/login.html",
        ):
            with self.subTest(url=reset_url):
                candidate = valid_production_environment()
                candidate["PASSWORD_RESET_URL"] = reset_url
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)

    def test_invalid_environment_timezone_and_jwt_options_fail_clearly(self):
        for name, value in (
            ("APP_ENV", "prod"),
            ("SCHEDULING_TIMEZONE", "Mars/Olympus"),
            ("ALGORITHM", "none"),
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "0"),
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "4"),
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "61"),
            ("ACCESS_TOKEN_EXPIRE_MINUTES", "not-a-number"),
            ("TRUSTED_PROXY_COUNT", "-1"),
            ("TRUSTED_PROXY_COUNT", "many"),
            ("TRUSTED_PROXY_COUNT", "33"),
            ("RATE_LIMIT_MAX_ATTEMPTS", "0"),
            ("RATE_LIMIT_MAX_ATTEMPTS", "many"),
            ("RATE_LIMIT_BLOCK_MINUTES", "0"),
            ("RATE_LIMIT_BLOCK_MINUTES", "many"),
            ("FORCE_HTTPS", "sometimes"),
            ("TERMS_VERSION", ""),
        ):
            with self.subTest(name=name):
                candidate = valid_production_environment()
                candidate[name] = value
                with self.assertRaises(RuntimeError):
                    load_settings(candidate)


if __name__ == "__main__":
    unittest.main()
