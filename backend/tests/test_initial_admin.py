import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config

from support import Base, asgi_request, main, reset_database
from app.core.security import verify_password
from app.initial_admin import create_initial_admin, validate_installation_for_admin_bootstrap
from app.models.user import RoleEnum, User


class InitialAdminTests(unittest.TestCase):
    def setUp(self):
        reset_database()
        Base.metadata.drop_all(bind=main.engine)
        with main.engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with main.engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def test_creates_first_admin_with_hashed_password(self):
        db = main.SessionLocal()
        try:
            admin = create_initial_admin(
                db, nome="Installation admin", email="OWNER@example.test", password="long-test-password"
            )
            self.assertEqual(admin.email, "owner@example.test")
            self.assertEqual(admin.role, RoleEnum.ADMIN)
            self.assertTrue(verify_password("long-test-password", admin.senha_hash))
        finally:
            db.close()

    def test_refuses_second_admin_and_existing_email(self):
        db = main.SessionLocal()
        try:
            create_initial_admin(db, nome="Initial admin", email="owner@example.test", password="long-test-password")
            with self.assertRaisesRegex(ValueError, "already has an administrator"):
                create_initial_admin(db, nome="Second admin", email="other@example.test", password="another-test-password")
        finally:
            db.close()

    def test_refuses_short_password_and_existing_email(self):
        db = main.SessionLocal()
        try:
            with self.assertRaisesRegex(ValueError, "at least 12"):
                create_initial_admin(db, nome="Admin", email="owner@example.test", password="short")
            db.add(User(nome="Client", email="owner@example.test", senha_hash="hashed"))
            db.commit()
            with self.assertRaisesRegex(ValueError, "already registered"):
                create_initial_admin(db, nome="Admin", email="owner@example.test", password="long-test-password")
        finally:
            db.close()

    def test_simultaneous_bootstrap_attempts_create_exactly_one_admin(self):
        barrier = threading.Barrier(2)

        def attempt(address):
            db = main.SessionLocal()
            try:
                barrier.wait(timeout=5)
                create_initial_admin(db, nome="Admin", email=address, password="long-test-password")
                return "created"
            except ValueError:
                return "refused"
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ("first@example.test", "second@example.test")))

        self.assertCountEqual(results, ["created", "refused"])
        with main.SessionLocal() as db:
            self.assertEqual(db.query(User).filter(User.role == RoleEnum.ADMIN).count(), 1)

    def test_public_registration_cannot_promote_itself(self):
        status, body = asgi_request(
            main.app,
            "POST",
            "/auth/register",
            {
                "nome": "Public user",
                "email": "public@example.com",
                "senha": "test-password",
                "consentimento_lgpd": True,
                "role": "admin",
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["role"], "cliente")
        with main.SessionLocal() as db:
            user = db.query(User).filter(User.email == "public@example.com").one()
            self.assertEqual(user.role, RoleEnum.CLIENTE)

    def test_cli_accepts_explicit_local_development_on_migrated_sqlite(self):
        if main.engine.dialect.name != "sqlite":
            self.skipTest("This check targets the isolated SQLite test backend")
        with patch.dict(os.environ, {"APP_ENV": "development"}):
            validate_installation_for_admin_bootstrap()

    def test_cli_rejects_missing_or_test_environment(self):
        for environment in ("", "test"):
            with self.subTest(environment=environment), patch.dict(os.environ, {"APP_ENV": environment}):
                with self.assertRaisesRegex(RuntimeError, "APP_ENV"):
                    validate_installation_for_admin_bootstrap()

    def test_cli_rejects_sqlite_in_production(self):
        if main.engine.dialect.name != "sqlite":
            self.skipTest("SQLite production rejection is covered by the isolated SQLite backend")
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            with self.assertRaisesRegex(RuntimeError, "requires PostgreSQL"):
                validate_installation_for_admin_bootstrap()

    def test_cli_accepts_migrated_isolated_postgresql_in_production(self):
        if main.engine.dialect.name != "postgresql":
            self.skipTest("Requires the isolated PostgreSQL test backend")
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            validate_installation_for_admin_bootstrap()


if __name__ == "__main__":
    unittest.main()
