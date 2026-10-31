import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from support import (
    Base,
    create_isolated_postgres_test_schema,
    drop_isolated_postgres_test_schema,
    main,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG = BACKEND_DIR / "alembic.ini"
POSTGRES_TESTS_ENABLED = (
    os.environ.get("BOOKING_TEST_BACKEND", "sqlite").strip().lower() == "postgresql"
    and bool(os.environ.get("BOOKING_TEST_POSTGRES_URL"))
)


def migration_config(connection):
    config = Config(str(ALEMBIC_CONFIG))
    config.attributes["connection"] = connection
    return config


def schema_snapshot(engine):
    inspector = inspect(engine)
    tables = {}
    for table in sorted(set(inspector.get_table_names()) - {"alembic_version"}):
        tables[table] = (
            tuple(
                (column["name"], str(column["type"]), column["nullable"])
                for column in inspector.get_columns(table)
            ),
            tuple(sorted(
                (tuple(column if column is not None else index["expressions"][position]
                       for position, column in enumerate(index["column_names"])), bool(index["unique"]))
                for index in inspector.get_indexes(table)
            )),
            tuple(sorted(
                (tuple(item["constrained_columns"] or ()), item["referred_table"], tuple(item["referred_columns"] or ()))
                for item in inspector.get_foreign_keys(table)
            )),
            tuple(sorted(
                tuple(item["column_names"] or ())
                for item in inspector.get_unique_constraints(table)
            )),
        )
    return tables


def assert_matches_models(test_case, engine):
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection,
            opts={"compare_type": True, "compare_server_default": True},
        )
        differences = compare_metadata(context, Base.metadata)
    test_case.assertEqual(differences, [])


class SQLiteSchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="barbearia-schema-migration-")
        self.addCleanup(self.tempdir.cleanup)
        self.db_path = Path(self.tempdir.name) / "migration-test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.addCleanup(self.engine.dispose)

    def _upgrade(self, target="head"):
        with self.engine.connect() as connection:
            command.upgrade(migration_config(connection), target)

    def test_empty_database_upgrade_creates_complete_schema_and_repeats_cleanly(self):
        self._upgrade()
        self.assertEqual(set(inspect(self.engine).get_table_names()), set(Base.metadata.tables) | {"alembic_version"})
        assert_matches_models(self, self.engine)
        snapshot = schema_snapshot(self.engine)

        self._upgrade()

        self.assertEqual(schema_snapshot(self.engine), snapshot)
        assert_matches_models(self, self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                "20261031_01",
            )

    def test_supported_create_all_legacy_schema_is_adopted_without_losing_rows(self):
        legacy_tables = [
            table for table in Base.metadata.sorted_tables
            if table.name not in {"consentimentos_lgpd", "refresh_tokens", "login_attempts", "audit_logs"}
        ]
        Base.metadata.create_all(bind=self.engine, tables=legacy_tables)
        with self.engine.begin() as connection:
            for index_name in (
                "ix_appointments_barbeiro_data_hora",
                "ix_jornadas_barbeiro_dia_ativo",
                "ix_bloqueios_barbeiro_inicio_fim_ativo",
            ):
                connection.exec_driver_sql(f'DROP INDEX IF EXISTS "{index_name}"')
            connection.exec_driver_sql("ALTER TABLE services DROP COLUMN descricao")
            connection.execute(text(
                "INSERT INTO users (nome, email, senha_hash, consentimento_lgpd) "
                "VALUES ('Cliente legado', 'legacy@example.test', 'hashed', 0)"
            ))

        self._upgrade()

        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SELECT email FROM users")).scalar_one(),
                "legacy@example.test",
            )
        assert_matches_models(self, self.engine)

    def test_incompatible_schema_fails_without_dropping_existing_table_or_data(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"
            )
            connection.exec_driver_sql(
                "INSERT INTO users(id, email) VALUES (1, 'keep@example.test')"
            )

        with self.assertRaisesRegex(RuntimeError, "not a supported create_all development schema"):
            self._upgrade()

        self.assertEqual(set(inspect(self.engine).get_table_names()), {"users", "alembic_version"})
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SELECT email FROM users")).scalar_one(),
                "keep@example.test",
            )

    def test_unknown_revision_fails_and_startup_check_only_warns_without_ddl(self):
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
            connection.exec_driver_sql(
                "INSERT INTO alembic_version(version_num) VALUES ('unknown_revision')"
            )

        with self.assertRaises(Exception):
            self._upgrade()

        self.assertEqual(
            set(inspect(self.engine).get_table_names()),
            {"alembic_version"},
        )
        with patch.object(main, "engine", self.engine):
            with self.assertLogs("app.main", level="WARNING") as logs:
                async def run_app_lifespan():
                    async with main.app.router.lifespan_context(main.app):
                        pass
                asyncio.run(run_app_lifespan())
        self.assertIn("alembic upgrade head", " ".join(logs.output))
        self.assertNotIn("unknown_revision", " ".join(logs.output))
        self.assertEqual(set(inspect(self.engine).get_table_names()), {"alembic_version"})

    def test_production_startup_check_does_not_create_or_modify_tables(self):
        with patch.object(main, "engine", self.engine), patch.dict(os.environ, {"APP_ENV": "production"}):
            with self.assertLogs("app.main", level="WARNING") as logs:
                async def run_app_lifespan():
                    async with main.app.router.lifespan_context(main.app):
                        pass
                asyncio.run(run_app_lifespan())

        self.assertIn("alembic upgrade head", " ".join(logs.output))
        self.assertEqual(inspect(self.engine).get_table_names(), [])

    def test_baseline_downgrade_is_refused_without_touching_schema(self):
        self._upgrade()
        before = schema_snapshot(self.engine)

        with self.assertRaisesRegex(RuntimeError, "Downgrade is disabled"):
            with self.engine.connect() as connection:
                command.downgrade(migration_config(connection), "20261027_01")

        self.assertEqual(schema_snapshot(self.engine), before)
        with self.engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                "20261031_01",
            )


@unittest.skipUnless(
    POSTGRES_TESTS_ENABLED,
    "PostgreSQL schema migration tests require the isolated *_test database harness",
)
class PostgreSQLSchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.schema_name, self.schema_url = create_isolated_postgres_test_schema("full_migration")
        self.engine = create_engine(self.schema_url, pool_pre_ping=True)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(drop_isolated_postgres_test_schema, self.schema_name)

    def test_empty_database_upgrade_creates_complete_schema_and_repeats_cleanly(self):
        with self.engine.connect() as connection:
            command.upgrade(migration_config(connection), "head")
        self.assertEqual(set(inspect(self.engine).get_table_names()), set(Base.metadata.tables) | {"alembic_version"})
        assert_matches_models(self, self.engine)
        snapshot = schema_snapshot(self.engine)

        with self.engine.connect() as connection:
            command.upgrade(migration_config(connection), "head")

        self.assertEqual(schema_snapshot(self.engine), snapshot)
        assert_matches_models(self, self.engine)


if __name__ == "__main__":
    unittest.main()
