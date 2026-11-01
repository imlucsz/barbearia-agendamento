import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from support import asgi_request, main


BACKEND = Path(__file__).resolve().parents[1]


class RenderStartTests(unittest.TestCase):
    """Catch serving before migration, skipped upgrades and ignored failures."""

    def test_start_migrates_before_serving_empty_current_and_stale_databases(self):
        for initial in (None, "head", "20261029_06"):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory(prefix="render-start-") as tmp:
                directory = Path(tmp)
                url = f"sqlite:///{(directory / 'database.db').as_posix()}"
                engine = create_engine(url, connect_args={"check_same_thread": False})
                try:
                    if initial:
                        with engine.connect() as connection:
                            config = Config(str(BACKEND / "alembic.ini"))
                            config.attributes["connection"] = connection
                            command.upgrade(config, initial)
                        with engine.begin() as connection:
                            connection.exec_driver_sql(
                                "INSERT INTO users (nome, email, senha_hash, consentimento_lgpd) "
                                "VALUES ('Fixture', 'keep@example.test', 'test-only', 0)")
                    with patch.object(main, "engine", engine):
                        before = asgi_request(main.app, "GET", "/ready")[0]
                    self.assertEqual(before, 200 if initial == "head" else 503)

                    result, marker = self._start(directory, url)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(marker.exists(), "Uvicorn was not launched")
                    with patch.object(main, "engine", engine):
                        status, body = asgi_request(main.app, "GET", "/ready")
                    self.assertEqual((status, body), (200, {"status": "ready"}))
                    if initial:
                        with engine.connect() as connection:
                            self.assertEqual(connection.execute(text("SELECT email FROM users")).scalars().all(),
                                             ["keep@example.test"])
                finally:
                    engine.dispose()

    def test_failed_migration_never_launches_server_or_exposes_error_details(self):
        with tempfile.TemporaryDirectory(prefix="render-start-failure-") as tmp:
            directory = Path(tmp)
            url = f"sqlite:///{(directory / 'database.db').as_posix()}"
            engine = create_engine(url, connect_args={"check_same_thread": False})
            try:
                with engine.begin() as connection:
                    connection.exec_driver_sql("CREATE TABLE alembic_version (version_num VARCHAR(32))")
                    connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"),
                                       {"revision": "private-invalid-revision"})
                result, marker = self._start(directory, url)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(marker.exists())
                self.assertIn("Migration failed", result.stderr)
                self.assertNotIn("private-invalid-revision", result.stdout + result.stderr)
                self.assertNotIn(url, result.stdout + result.stderr)
                with patch.object(main, "engine", engine):
                    self.assertEqual(asgi_request(main.app, "GET", "/ready")[0], 503)
            finally:
                engine.dispose()

    def test_conflicting_data_aborts_real_migration_and_preserves_accounts(self):
        with tempfile.TemporaryDirectory(prefix="render-start-conflict-") as tmp:
            directory = Path(tmp)
            url = f"sqlite:///{(directory / 'database.db').as_posix()}"
            engine = create_engine(url, connect_args={"check_same_thread": False})
            try:
                with engine.connect() as connection:
                    config = Config(str(BACKEND / "alembic.ini"))
                    config.attributes["connection"] = connection
                    command.upgrade(config, "20261029_06")
                with engine.begin() as connection:
                    for email in ("conflict@example.test", "CONFLICT@example.test"):
                        connection.execute(text(
                            "INSERT INTO users (nome, email, senha_hash, consentimento_lgpd) "
                            "VALUES ('Fixture', :email, 'test-only', 0)"), {"email": email})
                result, marker = self._start(directory, url)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(marker.exists())
                self.assertNotIn("conflict@example.test", result.stdout + result.stderr)
                with engine.connect() as connection:
                    self.assertEqual(connection.execute(text("SELECT count(*) FROM users")).scalar_one(), 2)
                    self.assertEqual(connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                                     "20261029_06")
                with patch.object(main, "engine", engine):
                    self.assertEqual(asgi_request(main.app, "GET", "/ready")[0], 503)
            finally:
                engine.dispose()

    def _start(self, directory, url):
        marker = directory / "server-started"
        # Replace only the blocking server boundary. Real Alembic and /ready run.
        # The child must observe head before it can record that Uvicorn started.
        (directory / "uvicorn.py").write_text(
            "import os, sys\n"
            "from pathlib import Path\n"
            "from sqlalchemy import create_engine, text\n"
            "from alembic.config import Config\n"
            "from alembic.script import ScriptDirectory\n"
            "engine = create_engine(os.environ['DATABASE_URL'])\n"
            "with engine.connect() as connection:\n"
            "    revisions = set(connection.execute(text('SELECT version_num FROM alembic_version')).scalars())\n"
            "heads = set(ScriptDirectory.from_config(Config('alembic.ini')).get_heads())\n"
            "assert revisions == heads, 'server launched before migration'\n"
            "assert sys.argv[1:] == ['app.main:app', '--host', '0.0.0.0', '--port', '10000', '--no-proxy-headers']\n"
            "Path(os.environ['RENDER_START_TEST_MARKER']).write_text('started')\n"
            "engine.dispose()\n", encoding="utf-8")
        environment = dict(os.environ, DATABASE_URL=url, APP_ENV="test", PORT="10000",
                           PYTHON_DOTENV_DISABLED="1", PYTHONDONTWRITEBYTECODE="1",
                           RENDER_START_TEST_MARKER=str(marker),
                           PYTHONPATH=os.pathsep.join((str(directory), str(BACKEND))))
        result = subprocess.run([sys.executable, "-B", "-m", "app.render_start"],
                                cwd=BACKEND, env=environment, capture_output=True,
                                text=True, timeout=60)
        return result, marker
