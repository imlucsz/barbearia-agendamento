import importlib.util
from pathlib import Path
import unittest
import os
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


class EmailIdentityMigrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("BOOKING_TEST_BACKEND") == "postgresql", "Requires disposable PostgreSQL harness")
    def test_postgres_same_name_index_definition_is_verified(self):
        from support import create_isolated_postgres_test_schema, drop_isolated_postgres_test_schema
        schema, url = create_isolated_postgres_test_schema("email_index")
        engine = create_engine(url)
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))
                connection.execute(text("INSERT INTO users VALUES (1, '  Mixed@example.com  ')"))
                connection.execute(text("CREATE UNIQUE INDEX uq_users_email_identity ON users(email)"))
                with self.assertRaisesRegex(RuntimeError,"incompatível"):
                    self.migrate(connection)
                self.assertEqual(connection.execute(text("SELECT email FROM users")).scalar_one(), "  Mixed@example.com  ")
                connection.execute(text("DROP INDEX uq_users_email_identity"))
                connection.execute(text("CREATE UNIQUE INDEX uq_users_email_identity ON users(lower(ltrim(rtrim(email))))"))
                self.migrate(connection)
                self.assertEqual(connection.execute(text("SELECT email FROM users")).scalar_one(), "mixed@example.com")
        finally:
            engine.dispose()
            drop_isolated_postgres_test_schema(schema)

    def test_same_name_constraint_is_not_silently_accepted(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL, CONSTRAINT uq_users_email_identity CHECK(length(email) > 0))"))
                with self.assertRaisesRegex(RuntimeError,"incompatível"):
                    self.migrate(connection)
        finally:
            engine.dispose()

    def test_wrong_same_name_index_aborts_before_normalizing_data(self):
        engine = create_engine("sqlite://")
        try:
            for definition in ["CREATE INDEX uq_users_email_identity ON users(email)",
                               "CREATE UNIQUE INDEX uq_users_email_identity ON users(email)",
                               "CREATE UNIQUE INDEX UQ_USERS_EMAIL_IDENTITY ON users(email)"]:
                with engine.begin() as connection:
                    connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)"))
                    connection.execute(text("INSERT INTO users VALUES (1, '  Mixed@example.com  ')"))
                    connection.execute(text(definition))
                    with self.assertRaisesRegex(RuntimeError, "incompatível"):
                        self.migrate(connection)
                    self.assertEqual(connection.execute(text("SELECT email FROM users")).scalar_one(), "  Mixed@example.com  ")
                    connection.execute(text("DROP TABLE users"))
        finally:
            engine.dispose()

    def test_supported_same_name_index_and_legacy_whitespace(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)"))
                connection.execute(text("CREATE UNIQUE INDEX uq_users_email_identity ON users(lower(ltrim(rtrim(email))))"))
                connection.execute(text("INSERT INTO users VALUES (1, :email)"), {"email":"\t\u00a0Mixed.Test+alias@Example.com\u00a0\n"})
                self.migrate(connection)
                self.assertEqual(connection.execute(text("SELECT email FROM users")).scalar_one(), "mixed.test+alias@example.com")
        finally:
            engine.dispose()

    def migrate(self, connection):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/20261031_01_email_identity.py"
        spec = importlib.util.spec_from_file_location("email_revision", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()

    def test_collision_does_not_modify_existing_accounts(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)"))
                connection.execute(text("INSERT INTO users VALUES (1, 'Demo@example.com'), (2, 'demo@example.com')"))
                with self.assertRaisesRegex(RuntimeError, "conflitantes"):
                    self.migrate(connection)
                self.assertEqual(connection.execute(text("SELECT email FROM users ORDER BY id")).scalars().all(),
                                 ["Demo@example.com", "demo@example.com"])
        finally:
            engine.dispose()

    def test_existing_identity_is_normalized_without_provider_rewriting(self):
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)"))
                connection.execute(text("INSERT INTO users VALUES (1, '  Name.Test+alias@Example.com  ')"))
                self.migrate(connection)
                self.assertEqual(connection.execute(text("SELECT email FROM users")).scalar_one(), "name.test+alias@example.com")
                with self.assertRaises(IntegrityError):
                    connection.execute(text("INSERT INTO users VALUES (2, 'NAME.TEST+ALIAS@EXAMPLE.COM')"))
        finally:
            engine.dispose()
