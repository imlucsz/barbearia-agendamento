"""Run tests against a fresh local PostgreSQL cluster, never a configured database.

Usage: backend/.venv/Scripts/python.exe tools/test-recovery-postgres.py
Requires installed PostgreSQL binaries; credentials exist only in temporary test state.
"""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    binaries = Path(os.environ.get("POSTGRES_TEST_BIN", r"C:\Program Files\PostgreSQL\18\bin"))
    if not (binaries / "initdb.exe").is_file():
        print("PostgreSQL isolated tests: binaries unavailable; not executed.")
        return 2
    temporary = Path(tempfile.mkdtemp(prefix="barbearia-recovery-pg-test-")).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temporary.parent != temp_root or not temporary.name.startswith("barbearia-recovery-pg-test-"):
        raise RuntimeError("Unexpected temporary cluster path")
    data = temporary / "data"
    password = secrets.token_hex(24)
    password_file = temporary / "test-password"
    password_file.write_text(password, encoding="ascii")
    environment = dict(os.environ, PGPASSWORD=password)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started = False
    stopped = True
    def run(arguments, *, timeout=90):
        # pg_ctl launches a daemon which can inherit pipe handles on Windows.
        # A file avoids waiting forever for inherited stdout/stderr pipes to close.
        output_path = temporary / "command-output.txt"
        with output_path.open("w", encoding="utf-8") as output_file:
            result = subprocess.run([str(item) for item in arguments], env=environment,
                cwd=root / "backend", stdout=output_file, stderr=subprocess.STDOUT,
                creationflags=flags, timeout=timeout)
        output = output_path.read_text(encoding="utf-8", errors="replace").replace(password, "[REDACTED]")
        if result.returncode:
            print(output[-12000:])
            raise RuntimeError(f"Isolated PostgreSQL command failed: {Path(str(arguments[0])).name}")
        return output
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        run([binaries / "initdb.exe", "-D", data, "-U", "reset_test", "--encoding=UTF8",
             "--locale=C", "--auth-local=trust", "--auth-host=scram-sha-256", "--pwfile", password_file])
        password_file.unlink()
        started = True  # Cleanup also covers partially successful pg_ctl startup.
        run([binaries / "pg_ctl.exe", "-D", data, "-l", temporary / "server.log", "-o",
             f"-h 127.0.0.1 -p {port}", "-w", "start"])
        run([binaries / "createdb.exe", "-h", "127.0.0.1", "-p", str(port), "-U", "reset_test", "barbearia_recovery_test"])
        environment["BOOKING_TEST_BACKEND"] = "postgresql"
        environment["BOOKING_TEST_POSTGRES_URL"] = f"postgresql+psycopg://reset_test:{password}@127.0.0.1:{port}/barbearia_recovery_test"
        environment["PYTHON_DOTENV_DISABLED"] = "1"
        print("PostgreSQL isolated cluster ready on loopback; running real database tests.", flush=True)
        # Pass unittest arguments only; no arbitrary executable or database target.
        arguments = sys.argv[1:] or ["discover", "-s", "tests", "-q"]
        output = run([sys.executable, "-m", "unittest", *arguments], timeout=1800)
        print("\n".join(output.splitlines()[-35:]), flush=True)
        return 0
    finally:
        if started:
            try:
                run([binaries / "pg_ctl.exe", "-D", data, "-m", "fast", "-w", "stop"])
            except Exception:
                stopped = False
                print("Temporary cluster shutdown failed; files preserved for local inspection.")
        if stopped:
            # Both the absolute target and its intended parent were checked above.
            shutil.rmtree(temporary)
            print("Temporary PostgreSQL cluster stopped and removed.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
