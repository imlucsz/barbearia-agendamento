import importlib.util
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CREATOR_PATH = REPO / "tools" / "new-installation" / "create.py"
CREATOR_SPEC = importlib.util.spec_from_file_location("install_creator_for_isolation", CREATOR_PATH)
CREATOR = importlib.util.module_from_spec(CREATOR_SPEC)
CREATOR_SPEC.loader.exec_module(CREATOR)


def unused_port():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return server.getsockname()[1]


def request(url, *, origin=None, preflight=False):
    headers = {}
    method = "GET"
    if origin:
        headers["Origin"] = origin
    if preflight:
        method = "OPTIONS"
        headers["Access-Control-Request-Method"] = "GET"
    req = urllib.request.Request(url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as response:
        try:
            return response.code, response.headers, response.read()
        finally:
            response.close()


class TwoInstallationIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="barbearia-installations-")
        cls.temp_root = Path(cls.temporary.name)
        cls.instances = []
        for suffix, name, service_name, origin, timezone_name in (
            ("aurora", "Barbearia Aurora", "Corte Aurora", "https://aurora.example.test", "America/Sao_Paulo"),
            ("norte", "Barbearia Norte", "Corte Norte", "https://norte.example.test", "UTC"),
        ):
            instance_root = cls.temp_root / suffix
            config_path = instance_root / "frontend" / "assets" / "js" / "installation-config.mjs"
            config_path.parent.mkdir(parents=True)
            api_port = unused_port()
            api_url = f"https://api-{suffix}.example.test"
            config_path.write_text(CREATOR.make_frontend_config(name, api_url), encoding="utf-8")

            database_path = instance_root / "barbearia_test.db"
            env = {key: value for key, value in os.environ.items() if key not in {
                "DATABASE_URL", "SECRET_KEY", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD",
                "SMTP_FROM", "PASSWORD_RESET_URL", "BOOKING_TEST_BACKEND", "BOOKING_TEST_POSTGRES_URL",
            }}
            env.update({
                "APP_ENV": "development",
                "INSTALLATION_NAME": name,
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "SECRET_KEY": f"shop_{suffix}_private_sunrise_key_1234567890",
                "CORS_ALLOWED_ORIGINS": origin,
                "SCHEDULING_TIMEZONE": timezone_name,
                "TERMS_VERSION": f"2026-{suffix}",
                "FORCE_HTTPS": "false",
                "PYTHON_DOTENV_DISABLED": "1",
                "PYTHONPATH": str(BACKEND),
            })
            cls._run_checked([sys.executable, "-m", "alembic", "upgrade", "head"], env)
            seed = (
                "from app.database import SessionLocal; "
                "from app.models.user import User, Service, RoleEnum; "
                "db=SessionLocal(); "
                f"db.add_all([User(nome={name!r}, email={('owner-' + suffix + '@example.test')!r}, "
                f"senha_hash={'not-used-' + suffix!r}, role=RoleEnum.CLIENTE), "
                f"Service(nome={service_name!r}, descricao='fixture', preco=35.0, duracao_minutos=30)]); "
                "db.commit(); db.close()"
            )
            cls._run_checked([sys.executable, "-c", seed], env)
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port), "--log-level", "critical"],
                cwd=BACKEND,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            instance = {
                "name": name,
                "service": service_name,
                "email": f"owner-{suffix}@example.test",
                "origin": origin,
                "port": api_port,
                "database": database_path,
                "config": config_path,
                "process": process,
            }
            cls.instances.append(instance)
            cls._wait_ready(instance)

    @classmethod
    def tearDownClass(cls):
        for instance in getattr(cls, "instances", []):
            process = instance["process"]
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        time.sleep(0.2)
        cls.temporary.cleanup()

    @staticmethod
    def _run_checked(command, env):
        result = subprocess.run(command, cwd=BACKEND, env=env, capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise RuntimeError("Isolated installation setup failed; subprocess output withheld")

    @classmethod
    def _wait_ready(cls, instance):
        deadline = time.monotonic() + 30
        url = f"http://127.0.0.1:{instance['port']}/health"
        while time.monotonic() < deadline:
            if instance["process"].poll() is not None:
                raise RuntimeError("Isolated API stopped before becoming healthy")
            try:
                if request(url)[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.25)
        raise RuntimeError("Isolated API did not become healthy before timeout")

    def test_two_installations_have_independent_brand_databases_and_public_apis(self):
        first, second = self.instances
        first_config = first["config"].read_text(encoding="utf-8")
        second_config = second["config"].read_text(encoding="utf-8")
        self.assertIn(first["name"], first_config)
        self.assertIn(second["name"], second_config)
        self.assertNotEqual(first_config, second_config)

        for own, other in ((first, second), (second, first)):
            api = f"http://127.0.0.1:{own['port']}"
            self.assertEqual(request(f"{api}/health")[0], 200)
            self.assertEqual(request(f"{api}/ready")[0], 200)
            status, _, body = request(f"{api}/services/")
            self.assertEqual(status, 200)
            services = json.loads(body)
            self.assertEqual([item["nome"] for item in services], [own["service"]])
            self.assertNotIn(other["service"], body.decode("utf-8"))
            openapi_status, _, openapi_body = request(f"{api}/openapi.json")
            self.assertEqual(openapi_status, 200)
            self.assertEqual(json.loads(openapi_body)["info"]["title"], f"API {own['name']}")

            own_status, own_headers, _ = request(f"{api}/services/", origin=own["origin"], preflight=True)
            other_status, other_headers, _ = request(f"{api}/services/", origin=other["origin"], preflight=True)
            self.assertEqual(own_status, 200)
            self.assertEqual(own_headers.get("access-control-allow-origin"), own["origin"])
            self.assertNotEqual(other_headers.get("access-control-allow-origin"), other["origin"])

        for own, other in ((first, second), (second, first)):
            database = sqlite3.connect(own["database"])
            try:
                emails = {row[0] for row in database.execute("SELECT email FROM users")}
                self.assertEqual(emails, {own["email"]})
                self.assertNotIn(other["email"], emails)
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
