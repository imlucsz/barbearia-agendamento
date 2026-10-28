import importlib.util
import os
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from support import (
    create_isolated_postgres_test_schema,
    drop_isolated_postgres_test_schema,
)


try:
    from alembic import command as _alembic_command
    from alembic.config import Config as _AlembicConfig

    ALEMBIC_AVAILABLE = True
except ImportError:
    _alembic_command = None
    _AlembicConfig = None
    ALEMBIC_AVAILABLE = False

POSTGRES_TESTS_ENABLED = (
    os.environ.get("BOOKING_TEST_BACKEND", "sqlite").strip().lower() == "postgresql"
    and bool(os.environ.get("BOOKING_TEST_POSTGRES_URL"))
)
PSYCOPG_AVAILABLE = importlib.util.find_spec("psycopg") is not None


@unittest.skipUnless(
    POSTGRES_TESTS_ENABLED and ALEMBIC_AVAILABLE and PSYCOPG_AVAILABLE,
    "Requires BOOKING_TEST_BACKEND=postgresql, BOOKING_TEST_POSTGRES_URL, Alembic, and psycopg",
)
class PostgresBookingMigrationTests(unittest.TestCase):
    def setUp(self):
        self.schema_name, self.schema_url = create_isolated_postgres_test_schema("migration")
        self.engine = create_engine(self.schema_url, pool_pre_ping=True)
        self.assertEqual(self.engine.dialect.name, "postgresql")
        self.config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
        self._create_legacy_schema()

    def tearDown(self):
        self.engine.dispose()
        drop_isolated_postgres_test_schema(self.schema_name)

    def _create_legacy_schema(self, with_legacy_unique=True):
        legacy_constraint = (
            ", CONSTRAINT _service_date_uc UNIQUE(service_id, data_hora)"
            if with_legacy_unique else ""
        )
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT NOT NULL UNIQUE)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE services (id SERIAL PRIMARY KEY, nome TEXT NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE appointments ("
                "id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id), "
                "nome_cliente TEXT, service_id INTEGER REFERENCES services(id), "
                "barbeiro_id INTEGER NOT NULL REFERENCES users(id), "
                "data_hora TIMESTAMP NOT NULL, status TEXT NOT NULL, "
                "preco FLOAT NOT NULL, duracao_minutos INTEGER NOT NULL, "
                "valor_cobrado FLOAT, reschedule_count INTEGER, "
                "CONSTRAINT uq_unrelated_client_snapshot UNIQUE(user_id, nome_cliente)"
                f"{legacy_constraint})"
            )
            connection.exec_driver_sql(
                "CREATE INDEX ix_appointments_barbeiro_id ON appointments(barbeiro_id)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE appointment_notes ("
                "id SERIAL PRIMARY KEY, appointment_id INTEGER NOT NULL "
                "REFERENCES appointments(id), note TEXT NOT NULL)"
            )
            connection.exec_driver_sql(
                "INSERT INTO users(id,email) VALUES "
                "(1,'client@example.test'),(2,'barber-a@example.test'),(3,'barber-b@example.test')"
            )
            connection.exec_driver_sql("INSERT INTO services(id,nome) VALUES (1,'Corte')")
            appointment_id = connection.execute(text(
                "INSERT INTO appointments "
                "(user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
                "VALUES (1,'Cliente legado',1,2,'2030-01-02 10:00:00','pendente',35,30) "
                "RETURNING id"
            )).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO appointment_notes(id,appointment_id,note) "
                    "VALUES (1,:appointment_id,'Preservar referência')"
                ),
                {"appointment_id": appointment_id},
            )

    def _config(self, connection):
        config = _AlembicConfig(str(self.config_path))
        config.attributes["connection"] = connection
        return config

    def _upgrade(self):
        with self.engine.connect() as connection:
            _alembic_command.upgrade(self._config(connection), "head")

    def test_upgrade_preserves_data_foreign_keys_and_other_constraints(self):
        self._upgrade()
        inspector = inspect(self.engine)
        unique_sets = [
            set(item["column_names"])
            for item in inspector.get_unique_constraints("appointments")
        ]
        self.assertNotIn({"service_id", "data_hora"}, unique_sets)
        self.assertIn({"user_id", "nome_cliente"}, unique_sets)
        self.assertEqual(
            {item["referred_table"] for item in inspector.get_foreign_keys("appointments")},
            {"users", "services"},
        )
        self.assertIn(
            "ix_appointments_barbeiro_id",
            {item["name"] for item in inspector.get_indexes("appointments")},
        )
        with self.engine.begin() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM appointments")).scalar_one(), 1)
            self.assertEqual(connection.execute(text("SELECT note FROM appointment_notes")).scalar_one(), "Preservar referência")
            connection.execute(text(
                "INSERT INTO appointments "
                "(user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
                "VALUES (1,'Outro cliente',1,3,'2030-01-02 10:00:00','pendente',35,30)"
            ))

    def test_upgrade_is_safe_if_the_legacy_constraint_is_absent(self):
        self.engine.dispose()
        drop_isolated_postgres_test_schema(self.schema_name)
        self.schema_name, self.schema_url = create_isolated_postgres_test_schema("migration")
        self.engine = create_engine(self.schema_url, pool_pre_ping=True)
        self._create_legacy_schema(with_legacy_unique=False)
        self._upgrade()
        unique_sets = [
            set(item["column_names"])
            for item in inspect(self.engine).get_unique_constraints("appointments")
        ]
        self.assertNotIn({"service_id", "data_hora"}, unique_sets)

    def test_downgrade_restores_constraint_when_data_is_compatible(self):
        self._upgrade()
        with self.engine.connect() as connection:
            _alembic_command.downgrade(self._config(connection), "base")
        unique_sets = [
            set(item["column_names"])
            for item in inspect(self.engine).get_unique_constraints("appointments")
        ]
        self.assertIn({"service_id", "data_hora"}, unique_sets)

    def test_downgrade_rejects_duplicates_and_preserves_rows(self):
        self._upgrade()
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO appointments "
                "(user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
                "VALUES (1,'Outro cliente',1,3,'2030-01-02 10:00:00','pendente',35,30)"
            ))
        with self.engine.connect() as connection:
            with self.assertRaisesRegex(RuntimeError, "duplicate service_id/data_hora"):
                _alembic_command.downgrade(self._config(connection), "base")
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM appointments")).scalar_one(), 2)
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
