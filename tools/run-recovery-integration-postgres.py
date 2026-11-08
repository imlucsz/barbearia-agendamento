"""Run recovery/session integration tests in an exclusively owned disposable container."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import uuid


def main():
    root = Path(__file__).resolve().parents[1]
    name = "recovery-pr35-test-" + uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(32)
    env = dict(os.environ, POSTGRES_PASSWORD=password, PYTHON_DOTENV_DISABLED="1")
    created = False

    def docker(*args):
        return subprocess.run(["docker", *args], env=env, capture_output=True,
                              text=True, timeout=40, check=True).stdout.strip()

    try:
        docker("run", "--detach", "--pull", "never", "--name", name,
               "--label", "purpose=recovery-pr35-disposable", "--env", "POSTGRES_PASSWORD",
               "--env", "POSTGRES_USER=recovery_test", "--env", "POSTGRES_DB=recovery_test",
               "--publish", "127.0.0.1::5432", "postgres:16-alpine")
        created = True
        for _ in range(40):
            try:
                docker("exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "recovery_test", "-d", "recovery_test")
                break
            except subprocess.CalledProcessError:
                time.sleep(.25)
        else:
            raise RuntimeError("Disposable PostgreSQL readiness timeout")
        port = json.loads(docker("inspect", name))[0]["NetworkSettings"]["Ports"]["5432/tcp"][0]
        if port["HostIp"] != "127.0.0.1":
            raise RuntimeError("Refusing non-loopback PostgreSQL")
        print("Disposable PostgreSQL " + docker("exec", name, "psql", "-U", "recovery_test", "-d", "recovery_test", "-Atc", "SHOW server_version"), flush=True)
        env.update(BOOKING_TEST_BACKEND="postgresql", PYTHONPATH=str(root / "backend"),
                   BOOKING_TEST_POSTGRES_URL=f"postgresql+psycopg://recovery_test:{password}@127.0.0.1:{port['HostPort']}/recovery_test")
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", "-q",
                                 "test_password_reset", "test_password_reset_limits_migration",
                                 "test_schema_migrations", "test_auth_stage2_concurrency", "test_authorization"],
                                cwd=root / "backend/tests", env=env, timeout=240,
                                capture_output=True, text=True)
        output = (result.stdout + result.stderr).replace(password, "[REDACTED]")
        output = re.sub(r"postgresql[^\s'\"]+", "[database URL withheld]", output)
        print(output[-10000:], flush=True)
        return result.returncode
    finally:
        if created:
            docker("rm", "--force", "--volumes", name)
            print("Removed only the disposable container and volumes created by this runner", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Disposable Docker operation failed ({exc.returncode}); sensitive output withheld") from None
