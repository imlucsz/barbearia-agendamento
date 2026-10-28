import os
import subprocess
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestDatabaseSelectionTests(unittest.TestCase):
    def _run_import(self, *, backend, postgres_url=None, database_url=None, code=None):
        env = os.environ.copy()
        env["BOOKING_TEST_BACKEND"] = backend
        env["PYTHON_DOTENV_DISABLED"] = "1"
        env["SECRET_KEY"] = "isolated-test-key-not-for-deployment"
        if postgres_url is None:
            env.pop("BOOKING_TEST_POSTGRES_URL", None)
        else:
            env["BOOKING_TEST_POSTGRES_URL"] = postgres_url
        if database_url is None:
            env.pop("DATABASE_URL", None)
        else:
            env["DATABASE_URL"] = database_url
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def test_sqlite_remains_isolated_even_when_postgres_url_is_present(self):
        result = self._run_import(
            backend="sqlite",
            postgres_url="postgresql+psycopg://fake:fake@127.0.0.1:55432/barbearia_test",
            database_url="postgresql+psycopg://also-fake:also-fake@127.0.0.1:5432/development",
            code=(
                "import sys; sys.path.insert(0, 'tests'); import support; "
                "import test_postgres_booking_migration as pg; "
                "print(support.main.engine.url.get_backend_name()); "
                "print(support.main.engine.url.database); "
                "print(pg.POSTGRES_TESTS_ENABLED)"
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sqlite", result.stdout.splitlines())
        self.assertIn("False", result.stdout.splitlines())
        self.assertIn("barbearia-tests", result.stdout)
        self.assertNotIn("development", result.stdout)

    def test_postgres_mode_requires_its_explicit_url_without_database_url_fallback(self):
        result = self._run_import(
            backend="postgresql",
            postgres_url=None,
            database_url="postgresql+psycopg://fake:fake@127.0.0.1:5432/development",
            code="import sys; sys.path.insert(0, 'tests'); import support",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit BOOKING_TEST_POSTGRES_URL", result.stderr)
        self.assertNotIn("fake:fake", result.stderr)

    def test_schema_scoped_url_preserves_explicit_connection_fields(self):
        result = self._run_import(
            backend="sqlite",
            code=(
                "import sys; sys.path.insert(0, 'tests'); import support; "
                "from sqlalchemy.engine import URL, make_url; "
                "source=URL.create('postgresql+psycopg', username='test_user', "
                "password='p@ss:/%secret', host='127.0.0.1', port=55432, "
                "database='barbearia_test').render_as_string(hide_password=False); "
                "support._POSTGRES_TEST_URL=source; original=make_url(source); "
                "derived=make_url(support._postgres_url_for_schema('barbearia_test_app_probe')); "
                "assert (derived.drivername,derived.host,derived.port,derived.database,derived.username,derived.password)==" 
                "(original.drivername,original.host,original.port,original.database,original.username,original.password); "
                "assert derived.query['options']=='-c search_path=barbearia_test_app_probe'; "
                "print('connection identity preserved')"
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("connection identity preserved", result.stdout)
        self.assertNotIn("p@ss", result.stdout)


if __name__ == "__main__":
    unittest.main()
