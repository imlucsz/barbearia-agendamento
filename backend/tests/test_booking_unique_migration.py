import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text


try:
    from alembic import command as _alembic_command
    from alembic.config import Config as _AlembicConfig

    ALEMBIC_AVAILABLE = True
except ImportError:
    _alembic_command = None
    _AlembicConfig = None
    ALEMBIC_AVAILABLE = False


@unittest.skipUnless(ALEMBIC_AVAILABLE, "Alembic is declared but is not installed in this environment")
class BookingUniqueMigrationTests(unittest.TestCase):
    def setUp(self):
        self._command = _alembic_command
        self._config_class = _AlembicConfig
        self._tempdir = tempfile.TemporaryDirectory(prefix="barbearia-alembic-tests-")
        self.db_path = Path(self._tempdir.name) / "migration-test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path.as_posix()}")
        self.config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
        self._environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "DATABASE_URL": f"sqlite:///{self.db_path.as_posix()}",
                "PYTHON_DOTENV_DISABLED": "1",
            },
        )
        self._environment.start()
        self.addCleanup(self._environment.stop)

    def tearDown(self):
        self.engine.dispose()
        self._tempdir.cleanup()

    def _config(self, connection):
        config = self._config_class(str(self.config_path))
        config.attributes["connection"] = connection
        return config

    def _create_schema(self, *, legacy_unique=True, named_legacy=False):
        named = "CONSTRAINT _service_date_uc " if named_legacy else ""
        legacy_clause = (
            f", {named}UNIQUE(service_id, data_hora)" if legacy_unique else ""
        )
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
            with connection.begin():
                self._create_tables_and_rows(connection, legacy_clause)

    @staticmethod
    def _create_tables_and_rows(connection, legacy_clause):
        connection.exec_driver_sql(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE services (id INTEGER PRIMARY KEY, nome TEXT NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE appointments ("
            "id INTEGER PRIMARY KEY, user_id INTEGER, nome_cliente TEXT, "
            "service_id INTEGER, barbeiro_id INTEGER NOT NULL, "
            "data_hora DATETIME NOT NULL, status TEXT NOT NULL, "
            "preco FLOAT NOT NULL, duracao_minutos INTEGER NOT NULL, "
            "valor_cobrado FLOAT, reschedule_count INTEGER, "
            "CONSTRAINT uq_unrelated_client_snapshot UNIQUE(user_id, nome_cliente), "
            "FOREIGN KEY(user_id) REFERENCES users(id), "
            "FOREIGN KEY(service_id) REFERENCES services(id), "
            "FOREIGN KEY(barbeiro_id) REFERENCES users(id)"
            f"{legacy_clause})"
        )
        connection.exec_driver_sql(
            "CREATE INDEX ix_appointments_barbeiro_id ON appointments(barbeiro_id)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE appointment_notes ("
            "id INTEGER PRIMARY KEY, appointment_id INTEGER NOT NULL, "
            "note TEXT NOT NULL, FOREIGN KEY(appointment_id) REFERENCES appointments(id))"
        )
        connection.exec_driver_sql(
            "INSERT INTO users(id,email) VALUES "
            "(1,'client@example.test'),(2,'barber-a@example.test'),(3,'barber-b@example.test')"
        )
        connection.exec_driver_sql("INSERT INTO services(id,nome) VALUES (1,'Corte')")
        connection.exec_driver_sql(
            "INSERT INTO appointments "
            "(id,user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
            "VALUES (1,1,'Cliente legado',1,2,'2030-01-02 10:00:00','pendente',35,30)"
        )
        connection.exec_driver_sql(
            "INSERT INTO appointment_notes(id,appointment_id,note) "
            "VALUES (1,1,'Preservar referência')"
        )

    def _upgrade(self):
        with self.engine.connect() as connection:
            self._command.upgrade(self._config(connection), "head")

    def test_unnamed_legacy_constraint_is_removed_and_other_schema_data_is_preserved(self):
        self._create_schema(legacy_unique=True, named_legacy=False)
        self._upgrade()

        inspector = inspect(self.engine)
        unique_constraints = inspector.get_unique_constraints("appointments")
        self.assertNotIn(
            {"service_id", "data_hora"},
            [set(item["column_names"]) for item in unique_constraints],
        )
        self.assertIn(
            {"user_id", "nome_cliente"},
            [set(item["column_names"]) for item in unique_constraints],
        )
        self.assertIn("ix_appointments_barbeiro_id", {
            item["name"] for item in inspector.get_indexes("appointments")
        })

        with self.engine.begin() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM appointments")).scalar_one(), 1)
            self.assertEqual(connection.execute(text("SELECT note FROM appointment_notes")).scalar_one(), "Preservar referência")
            connection.execute(text(
                "INSERT INTO appointments "
                "(id,user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
                "VALUES (2,1,'Outro cliente',1,3,'2030-01-02 10:00:00','pendente',35,30)"
            ))
        foreign_key_targets = {
            item["referred_table"] for item in inspect(self.engine).get_foreign_keys("appointments")
        }
        self.assertEqual(foreign_key_targets, {"users", "services"})

    def test_named_legacy_constraint_is_also_removed_by_columns(self):
        self._create_schema(legacy_unique=True, named_legacy=True)
        self._upgrade()
        constraints = inspect(self.engine).get_unique_constraints("appointments")
        self.assertNotIn(
            {"service_id", "data_hora"},
            [set(item["column_names"]) for item in constraints],
        )

    def test_upgrade_is_safe_when_constraint_or_appointments_table_is_absent(self):
        self._create_schema(legacy_unique=False)
        self._upgrade()
        self.assertEqual(
            [set(item["column_names"]) for item in inspect(self.engine).get_unique_constraints("appointments")],
            [{"user_id", "nome_cliente"}],
        )

        empty_path = self.db_path.parent / "empty.db"
        empty_engine = create_engine(f"sqlite:///{empty_path.as_posix()}")
        try:
            with empty_engine.connect() as connection:
                config = self._config_class(str(self.config_path))
                config.attributes["connection"] = connection
                self._command.upgrade(config, "head")
        finally:
            empty_engine.dispose()

    def test_safe_downgrade_restores_the_legacy_constraint(self):
        self._create_schema(legacy_unique=True, named_legacy=False)
        self._upgrade()
        with self.engine.connect() as connection:
            self._command.downgrade(self._config(connection), "base")
        constraints = inspect(self.engine).get_unique_constraints("appointments")
        self.assertIn(
            {"service_id", "data_hora"},
            [set(item["column_names"]) for item in constraints],
        )

    def test_downgrade_refuses_duplicate_data_without_changing_reservations(self):
        self._create_schema(legacy_unique=True, named_legacy=False)
        self._upgrade()
        with self.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO appointments "
                "(id,user_id,nome_cliente,service_id,barbeiro_id,data_hora,status,preco,duracao_minutos) "
                "VALUES (2,1,'Segundo horário',1,3,'2030-01-02 10:00:00','pendente',35,30)"
            ))

        with self.engine.connect() as connection:
            with self.assertRaisesRegex(RuntimeError, "duplicate service_id/data_hora"):
                self._command.downgrade(self._config(connection), "base")
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM appointments")).scalar_one(), 2)
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
