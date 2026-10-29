#!/usr/bin/env python3
"""Encrypted PostgreSQL backups and disposable restore verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL


BACKUP_RE = re.compile(r"^barbearia-postgres-(\d{8}T\d{6}Z)-([a-f0-9]{8})\.dump\.age$")
SIDECAR_RE = re.compile(r"^barbearia-postgres-(\d{8}T\d{6}Z)-([a-f0-9]{8})\.(?:sha256|manifest\.json)$")
TEST_DB_RE = re.compile(r"^barbearia_restore_test_\d{8}T\d{6}Z_[a-f0-9]{8}$")
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parents[1] / "backend"


def fail(message: str) -> None:
    raise RuntimeError(message)


def backup_dir() -> Path:
    directory = Path(os.environ.get("BACKUP_DIR", str(ROOT / "archive"))).expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        fail("BACKUP_DIR must be a directory")
    if os.name != "nt":
        directory.chmod(0o700)
    return directory


def validate_pgpass() -> None:
    passfile = os.environ.get("PGPASSFILE")
    if not passfile or not Path(passfile).is_file():
        fail("Set PGPASSFILE to a protected PostgreSQL password file")
    if os.name != "nt" and Path(passfile).stat().st_mode & 0o077:
        fail("PGPASSFILE must not be accessible by group or other users")


def run(args: list[str], *, env: dict[str, str] | None = None) -> None:
    try:
        subprocess.run(args, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        fail(f"Required backup utility is unavailable: {Path(args[0]).name}")
    except subprocess.CalledProcessError:
        fail(f"Backup utility failed: {Path(args[0]).name}; diagnostics suppressed")


def encrypted_dump(output: Path, snapshot: str, recipient: str) -> None:
    env = os.environ.copy()
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as encrypted_stream:
            age = subprocess.Popen(
                ["age", "--encrypt", "--recipient", recipient],
                stdin=subprocess.PIPE, stdout=encrypted_stream, stderr=subprocess.DEVNULL, env=env,
            )
            dump = None
            try:
                dump = subprocess.Popen(
                    ["pg_dump", "--format=custom", "--no-owner", "--no-acl", f"--snapshot={snapshot}", os.environ["PGDATABASE"]],
                    stdin=subprocess.DEVNULL, stdout=age.stdin, stderr=subprocess.DEVNULL, env=env,
                )
                age.stdin.close()
                dump_result = dump.wait()
                age_result = age.wait()
            except BaseException:
                if dump is not None:
                    dump.kill()
                    dump.wait()
                age.stdin.close()
                age.kill()
                age.wait()
                raise
    except FileNotFoundError as error:
        output.unlink(missing_ok=True)
        missing = Path(error.filename or "backup utility").name
        fail(f"Required backup utility is unavailable: {missing}")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    if dump_result != 0 or age_result != 0:
        output.unlink(missing_ok=True)
        fail("pg_dump/age pipeline failed; diagnostics suppressed")


def restore_pipeline(backup: Path, identity: str, database: str) -> None:
    try:
        age = subprocess.Popen(
            ["age", "--decrypt", "--identity", identity, str(backup)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        restore = None
        try:
            restore = subprocess.Popen(
                ["pg_restore", "--exit-on-error", "--no-owner", f"--dbname={database}"],
                stdin=age.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            age.stdout.close()
            restore_result = restore.wait()
            age_result = age.wait()
        except BaseException:
            if restore is not None:
                restore.kill()
                restore.wait()
            age.stdout.close()
            age.kill()
            age.wait()
            raise
    except FileNotFoundError as error:
        missing = Path(error.filename or "restore utility").name
        fail(f"Required restore utility is unavailable: {missing}")
    if restore_result != 0 or age_result != 0:
        fail("age/pg_restore pipeline failed; diagnostics suppressed")


def connect(dbname: str | None = None) -> psycopg.Connection:
    kwargs = {}
    if dbname is not None:
        kwargs["dbname"] = dbname
    try:
        return psycopg.connect(**kwargs)
    except psycopg.Error:
        fail("Could not connect to the configured PostgreSQL test/source database")


def snapshot_counts(connection: psycopg.Connection) -> tuple[str, dict[str, int], str]:
    connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
    tables = connection.execute(
        "SELECT schemaname, tablename FROM pg_tables "
        "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') "
        "ORDER BY schemaname, tablename"
    ).fetchall()
    counts: dict[str, int] = {}
    for schema, table in tables:
        key = f"{schema}.{table}"
        counts[key] = connection.execute(
            sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
        ).fetchone()[0]
    versions = counts.get("public.alembic_version")
    if versions != 1:
        fail("Expected exactly one Alembic version row in the source database")
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    return snapshot, counts, revision


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_private(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8", newline="\n")
    if os.name != "nt":
        path.chmod(0o600)


def remote_copy(files: list[Path]) -> None:
    mode = os.environ.get("BACKUP_REMOTE_MODE", "").strip().lower()
    destination = os.environ.get("BACKUP_REMOTE_DEST", "").strip()
    if not mode and not destination:
        fail("Configure an off-host copy with BACKUP_REMOTE_MODE and BACKUP_REMOTE_DEST")
    if not mode or not destination:
        fail("Configure both BACKUP_REMOTE_MODE and BACKUP_REMOTE_DEST")
    if mode == "rsync":
        if ":" not in destination:
            fail("rsync destination must be an operator-configured remote path")
        run(["rsync", "-a", "--chmod=F600,D700", "--", *[str(path) for path in files], destination.rstrip("/") + "/"])
    elif mode == "rclone":
        if ":" not in destination:
            fail("rclone destination must name a configured remote")
        for path in files:
            run(["rclone", "copyto", str(path), destination.rstrip("/") + "/" + path.name])
    elif mode == "s3":
        if not destination.startswith("s3://"):
            fail("S3 destination must start with s3://")
        for path in files:
            run(["aws", "s3", "cp", str(path), destination.rstrip("/") + "/" + path.name, "--sse", "AES256"])
    else:
        fail("BACKUP_REMOTE_MODE must be rsync, rclone, or s3")


def prune(directory: Path) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(os.environ.get("BACKUP_RETENTION_DAYS", "30")))
    for item in directory.iterdir():
        match = BACKUP_RE.fullmatch(item.name) or SIDECAR_RE.fullmatch(item.name)
        if not match or not item.is_file() or item.is_symlink():
            continue
        created = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if created < cutoff:
            item.unlink()


def create_backup() -> None:
    validate_pgpass()
    if not os.environ.get("PGDATABASE") or not os.environ.get("PGUSER"):
        fail("Set PGDATABASE and PGUSER explicitly for the backup role")
    directory = backup_dir()
    recipient = os.environ.get("BACKUP_AGE_RECIPIENT", "").strip()
    if not recipient:
        fail("Set BACKUP_AGE_RECIPIENT; plaintext backups are not written")
    retention = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
    if not 1 <= retention <= 3650:
        fail("BACKUP_RETENTION_DAYS must be between 1 and 3650")

    now = datetime.now(timezone.utc)
    stem = f"barbearia-postgres-{now:%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"
    encrypted = directory / f"{stem}.dump.age"
    checksum_file = directory / f"{stem}.sha256"
    manifest_file = directory / f"{stem}.manifest.json"
    connection = connect()
    try:
        snapshot, counts, revision = snapshot_counts(connection)
        encrypted_dump(encrypted, snapshot, recipient)
        if os.name != "nt":
            encrypted.chmod(0o600)
        checksum = sha256(encrypted)
        manifest = {
            "format": "postgresql-custom-age-v1",
            "created_at": now.isoformat(),
            "backup_file": encrypted.name,
            "sha256": checksum,
            "alembic_revision": revision,
            "table_counts": counts,
        }
        write_private(checksum_file, f"{checksum}  {encrypted.name}\n")
        write_private(manifest_file, json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    except BaseException:
        for partial in (encrypted, checksum_file, manifest_file):
            partial.unlink(missing_ok=True)
        raise
    finally:
        connection.rollback()
        connection.close()

    remote_copy([encrypted, checksum_file, manifest_file])
    prune(directory)
    print(f"Backup completed: {encrypted.name} (encrypted; SHA-256 {checksum})")


def latest_backup(directory: Path) -> tuple[Path, Path, dict]:
    candidates = sorted((path for path in directory.iterdir() if BACKUP_RE.fullmatch(path.name) and path.is_file() and not path.is_symlink()), reverse=True)
    if not candidates:
        fail("No encrypted backup matching the expected filename was found")
    backup = candidates[0]
    stem = backup.name.removesuffix(".dump.age")
    checksum_path = directory / f"{stem}.sha256"
    manifest_path = directory / f"{stem}.manifest.json"
    if not checksum_path.is_file() or not manifest_path.is_file():
        fail("Latest backup is missing its checksum or manifest; refusing to fall back to an older backup")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = checksum_path.read_text(encoding="utf-8").split()[0]
    except (OSError, ValueError, IndexError):
        fail("Latest backup checksum or manifest cannot be read")
    if manifest.get("backup_file") != backup.name or manifest.get("sha256") != expected or sha256(backup) != expected:
        fail("Latest backup checksum or manifest validation failed; refusing restore")
    if manifest.get("format") != "postgresql-custom-age-v1" or not isinstance(manifest.get("table_counts"), dict):
        fail("Latest backup manifest format is invalid")
    return backup, manifest_path, manifest


def restore_test() -> None:
    validate_pgpass()
    if os.environ.get("RESTORE_TEST_ALLOW") != "I_UNDERSTAND_DISPOSABLE_DATABASE":
        fail("Set RESTORE_TEST_ALLOW=I_UNDERSTAND_DISPOSABLE_DATABASE only for a disposable local PostgreSQL instance")
    host = os.environ.get("PGHOST", "")
    if host.lower() not in {"localhost", "127.0.0.1", "::1"}:
        fail("Restore test only connects to localhost/loopback PostgreSQL")
    if not os.environ.get("PGDATABASE", "").lower().endswith("_test"):
        fail("PGDATABASE must name a dedicated *_test database on the disposable test instance")
    if not os.environ.get("PGUSER"):
        fail("Set PGUSER to the disposable PostgreSQL test role")
    identity = os.environ.get("BACKUP_AGE_IDENTITY_FILE", "").strip()
    if not identity or not Path(identity).is_file():
        fail("Set BACKUP_AGE_IDENTITY_FILE to the protected age identity file")
    if os.name != "nt" and Path(identity).stat().st_mode & 0o077:
        fail("BACKUP_AGE_IDENTITY_FILE must not be accessible by group or other users")

    directory = backup_dir()
    backup, _, manifest = latest_backup(directory)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    database = f"barbearia_restore_test_{stamp}_{secrets.token_hex(4)}"
    if not TEST_DB_RE.fullmatch(database):
        fail("Generated restore-test database name failed validation")

    admin_connection = None
    created = False
    try:
        admin_connection = connect("postgres")
        admin_connection.autocommit = True
        exists = admin_connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,)).fetchone()
        if exists:
            fail("Generated restore database already exists; refusing to overwrite it")
        admin_connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        admin_connection.commit()
        created = True
        restore_pipeline(backup, identity, database)

        env = os.environ.copy()
        env.update({"APP_ENV": "test", "SECRET_KEY": "restore-test-only-secret-key-not-for-use-000000", "PYTHON_DOTENV_DISABLED": "1"})
        env["DATABASE_URL"] = URL.create(
            "postgresql+psycopg", username=env.get("PGUSER"), host=host,
            port=int(env["PGPORT"]) if env.get("PGPORT") else None, database=database,
        ).render_as_string(hide_password=True)
        try:
            subprocess.run([sys.executable, "-m", "alembic", "current"], cwd=BACKEND, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            fail("alembic current failed on the restored disposable database")

        restored = connect(database)
        try:
            tables = restored.execute(
                "SELECT schemaname, tablename FROM pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY schemaname, tablename"
            ).fetchall()
            actual: dict[str, int] = {}
            for schema, table in tables:
                key = f"{schema}.{table}"
                actual[key] = restored.execute(
                    sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))
                ).fetchone()[0]
            revision_rows = restored.execute("SELECT version_num FROM alembic_version").fetchall()
            revision = revision_rows[0][0] if len(revision_rows) == 1 else None
        finally:
            restored.close()
        if actual != manifest["table_counts"]:
            fail("Restored per-table row counts differ from the backup snapshot; database will be discarded")
        if revision != manifest.get("alembic_revision"):
            fail("Restored Alembic revision differs from the backup snapshot; database will be discarded")
        print(f"PASS: restored {backup.name}; Alembic revision and {len(actual)} table counts match the manifest")
    finally:
        if admin_connection is not None:
            if created:
                try:
                    admin_connection.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()", (database,))
                    admin_connection.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database)))
                    admin_connection.commit()
                except psycopg.Error:
                    admin_connection.rollback()
                    print("WARNING: could not drop the generated restore-test database; remove only this exact test database manually", file=sys.stderr)
            admin_connection.close()


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2 or sys.argv[1] not in {"backup", "restore-test"}:
            fail("Usage: backup.py backup|restore-test")
        create_backup() if sys.argv[1] == "backup" else restore_test()
    except (RuntimeError, ValueError, OSError, psycopg.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
