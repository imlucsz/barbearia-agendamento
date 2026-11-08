"""Bounded booking regressions in a newly owned, disposable local container."""
import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    name = "booking-part1-test-" + uuid.uuid4().hex[:12]
    env = dict(os.environ, POSTGRES_PASSWORD=secrets.token_urlsafe(32))
    created = False

    def docker(*args):
        return subprocess.run(["docker", *args], env=env, capture_output=True, text=True,
                              timeout=40, check=True).stdout.strip()
    try:
        # No download, published port is loopback-only, storage is container-owned.
        docker("run", "--detach", "--pull", "never", "--name", name,
               "--label", "purpose=booking-part1-disposable",
               "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_USER=booking_test",
               "--env", "POSTGRES_DB=booking_test", "--publish", "127.0.0.1::5432",
               "postgres:16-alpine")
        created = True
        for _ in range(40):
            try:
                docker("exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "booking_test", "-d", "booking_test")
                break
            except subprocess.CalledProcessError:
                time.sleep(.25)
        else:
            raise RuntimeError("Disposable PostgreSQL did not become ready")
        info = json.loads(docker("inspect", name))[0]
        port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]
        if port["HostIp"] != "127.0.0.1":
            raise RuntimeError("Refusing non-loopback PostgreSQL")
        version = docker("exec", name, "psql", "-U", "booking_test", "-d", "booking_test",
                         "-Atc", "SHOW server_version")
        print("Disposable PostgreSQL", version, flush=True)
        env.update(BOOKING_TEST_BACKEND="postgresql",
                   BOOKING_TEST_POSTGRES_URL=f"postgresql+psycopg://booking_test:{env['POSTGRES_PASSWORD']}@127.0.0.1:{port['HostPort']}/booking_test")
        env["PYTHONPATH"] = str(root / "backend")
        result = subprocess.run([sys.executable, "-m", "unittest", "-q",
                                 "test_booking_calendar", "test_booking_integrity", "test_booking_temporal"],
                                cwd=root / "backend/tests", env=env, timeout=180)
        return result.returncode
    finally:
        if created:
            docker("rm", "--force", "--volumes", name)
            print("Removed only the container and anonymous volumes created by this runner", flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"Disposable Docker operation failed ({exc.returncode}); credential-bearing output omitted")
