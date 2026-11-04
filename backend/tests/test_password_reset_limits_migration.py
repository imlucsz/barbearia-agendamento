"""Real DDL on a disposable database; no create_all replacement for Alembic."""
import os
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from alembic import command
from sqlalchemy import create_engine, inspect, text, event
from sqlalchemy.exc import SQLAlchemyError

from support import create_isolated_postgres_test_schema, drop_isolated_postgres_test_schema
from test_schema_migrations import migration_config, assert_matches_models


class PasswordResetLimitsMigrationTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get("BOOKING_TEST_BACKEND") == "postgresql":
            schema, url = create_isolated_postgres_test_schema("reset_limits")
            self.addCleanup(drop_isolated_postgres_test_schema, schema)
        else:
            directory = tempfile.TemporaryDirectory(prefix="reset-limits-migration-")
            self.addCleanup(directory.cleanup)
            url = f"sqlite:///{(Path(directory.name) / 'migration.db').as_posix()}"
        self.engine = create_engine(url)
        self.addCleanup(self.engine.dispose)

    def migrate(self, target, *, downgrade=False):
        with self.engine.connect() as connection:
            (command.downgrade if downgrade else command.upgrade)(migration_config(connection), target)

    def test_upgrade_preserves_users_downgrade_empty_and_reupgrade_match_models(self):
        self.migrate("20261031_01")
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO users (nome,email,senha_hash,consentimento_lgpd) VALUES ('Test','test@example.com','test',false)"))
        self.migrate("head")
        assert_matches_models(self, self.engine)
        self.migrate("20261031_01", downgrade=True)
        self.assertNotIn("password_reset_limits", inspect(self.engine).get_table_names())
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT nome FROM users")).scalar_one(), "Test")
        self.migrate("head")
        assert_matches_models(self, self.engine)

    def test_downgrade_refuses_to_discard_active_limits(self):
        self.migrate("head")
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO password_reset_limits (key,window_started_at,requests,next_allowed_at,lease_until) VALUES ('test',CURRENT_TIMESTAMP,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        with self.assertRaisesRegex(RuntimeError, "active limits must be preserved"):
            self.migrate("20261031_01", downgrade=True)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM password_reset_limits")).scalar_one(), 1)
            self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(), "20261103_01")

    @unittest.skipUnless(os.environ.get("BOOKING_TEST_BACKEND") == "postgresql", "PostgreSQL concurrent DDL test requires a disposable cluster")
    def test_downgrade_prevents_insertion_between_empty_check_and_drop(self):
        self.migrate("head")
        competing = create_engine(self.engine.url)
        completed = Event()
        outcomes = []
        self.addCleanup(competing.dispose)
        def insert_limit():
            try:
                with competing.begin() as connection:
                    connection.execute(text("INSERT INTO password_reset_limits (key,window_started_at,requests,next_allowed_at,lease_until) VALUES ('race',CURRENT_TIMESTAMP,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
                outcomes.append("inserted")
            except SQLAlchemyError:
                outcomes.append("rejected")
            finally:
                completed.set()
        with ThreadPoolExecutor(max_workers=1) as executor:
            def after_select(_connection, _cursor, statement, _parameters, _context, _many):
                if statement == "SELECT 1 FROM password_reset_limits LIMIT 1":
                    executor.submit(insert_limit)
                    # Without a DDL lock, the other connection commits in this gap.
                    completed.wait(2)
            event.listen(self.engine, "after_cursor_execute", after_select)
            try:
                self.migrate("20261031_01", downgrade=True)
            finally:
                event.remove(self.engine, "after_cursor_execute", after_select)
            self.assertTrue(completed.wait(5))
        self.assertEqual(outcomes, ["rejected"], "A committed limit must never be discarded by downgrade")
