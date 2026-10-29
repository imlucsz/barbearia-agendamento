import atexit
import asyncio
import importlib
import importlib.util
import json
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


# Keep every test module on one isolated temporary SQLite file and prevent a
# local .env from replacing this setup. Individual fixtures create their schema.
TEST_SECRET_KEY = "qa03-test-only-secret-key-not-for-deployment"
_TEST_DB_DIR = tempfile.TemporaryDirectory(prefix="barbearia-tests-")
_TEST_DB_PATH = Path(_TEST_DB_DIR.name) / "tests.db"
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["SECRET_KEY"] = TEST_SECRET_KEY
os.environ["CORS_ALLOWED_ORIGINS"] = "https://frontend.test.invalid"
os.environ["APP_ENV"] = "test"
for _optional_email_setting in (
    "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "PASSWORD_RESET_URL",
):
    os.environ.pop(_optional_email_setting, None)

_TEST_BACKEND = os.environ.get("BOOKING_TEST_BACKEND", "sqlite").strip().lower()
if _TEST_BACKEND not in {"sqlite", "postgresql"}:
    raise RuntimeError("BOOKING_TEST_BACKEND must be 'sqlite' or 'postgresql'")
_POSTGRES_TEST_URL = (
    os.environ.get("BOOKING_TEST_POSTGRES_URL")
    if _TEST_BACKEND == "postgresql"
    else None
)
if _TEST_BACKEND == "postgresql" and not _POSTGRES_TEST_URL:
    raise RuntimeError(
        "PostgreSQL test mode requires an explicit BOOKING_TEST_POSTGRES_URL; DATABASE_URL is never used as fallback"
    )
_POSTGRES_ADMIN_ENGINE = None
_POSTGRES_APP_SCHEMA = None
main = None


def _postgres_url_for_schema(schema_name):
    parsed = make_url(_POSTGRES_TEST_URL)
    query = dict(parsed.query)
    query["options"] = f"-c search_path={schema_name}"
    # str(URL) deliberately masks passwords as '***'; only render the real
    # encoded credential into this in-memory environment value, never a log.
    return parsed.set(query=query).render_as_string(hide_password=False)


def _assert_test_database(engine, expected_url, expected_schema=None):
    """Verify the connected identity before allowing the harness to create schema."""
    with engine.connect() as connection:
        database, username, schema = connection.execute(
            text("SELECT current_database(), current_user, current_schema()")
        ).one()
    if database != expected_url.database or not database.lower().endswith("_test"):
        raise RuntimeError("PostgreSQL test URL did not connect to its explicitly named *_test database")
    if expected_url.username and username != expected_url.username:
        raise RuntimeError("PostgreSQL test connection user did not match the explicit test URL")
    if expected_schema is not None and schema != expected_schema:
        raise RuntimeError("Application engine did not select its isolated PostgreSQL test schema")


def _validate_postgres_test_host(host):
    normalized_host = (host or "").lower()
    if normalized_host.startswith("[") and normalized_host.endswith("]"):
        normalized_host = normalized_host[1:-1]
    if normalized_host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError(
            "PostgreSQL test URL host must be localhost, 127.0.0.1, or ::1"
        )


def _create_postgres_schema(schema_name):
    with _POSTGRES_ADMIN_ENGINE.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))


def create_isolated_postgres_test_schema(prefix="migration"):
    """Create a per-test schema inside the explicitly selected *_test database."""
    if not _POSTGRES_TEST_URL:
        raise RuntimeError("BOOKING_TEST_POSTGRES_URL is not configured")
    schema_name = f"barbearia_test_{prefix}_{uuid.uuid4().hex}"
    _create_postgres_schema(schema_name)
    return schema_name, _postgres_url_for_schema(schema_name)


def drop_isolated_postgres_test_schema(schema_name):
    if not schema_name.startswith("barbearia_test_") or not all(
        character.isalnum() or character == "_" for character in schema_name
    ):
        raise ValueError("Refusing to drop a schema not created by the test harness")
    with _POSTGRES_ADMIN_ENGINE.begin() as connection:
        connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


if _POSTGRES_TEST_URL:
    _test_url = make_url(_POSTGRES_TEST_URL)
    if _test_url.get_backend_name() != "postgresql" or _test_url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "BOOKING_TEST_POSTGRES_URL must use postgresql+psycopg:// and target a dedicated test database"
        )
    _validate_postgres_test_host(_test_url.host)
    if not (_test_url.database or "").lower().endswith("_test"):
        raise RuntimeError("Refusing PostgreSQL tests unless the database name ends with '_test'")
    if not _test_url.password:
        raise RuntimeError("BOOKING_TEST_POSTGRES_URL must include the dedicated test database credential")
    if importlib.util.find_spec("psycopg") is None:
        raise RuntimeError(
            "BOOKING_TEST_POSTGRES_URL is set but psycopg is unavailable; "
            "install the declared PostgreSQL driver dependency first"
        )

    _POSTGRES_ADMIN_ENGINE = create_engine(_POSTGRES_TEST_URL, pool_pre_ping=True)
    # Authenticate and verify the target database/user before creating any schema.
    _assert_test_database(_POSTGRES_ADMIN_ENGINE, _test_url)
    _POSTGRES_APP_SCHEMA = f"barbearia_test_app_{uuid.uuid4().hex}"
    _create_postgres_schema(_POSTGRES_APP_SCHEMA)
    _APP_DATABASE_URL = _postgres_url_for_schema(_POSTGRES_APP_SCHEMA)
    _APP_TEST_URL = make_url(_APP_DATABASE_URL)
    if (
        _APP_TEST_URL.drivername != _test_url.drivername
        or _APP_TEST_URL.host != _test_url.host
        or _APP_TEST_URL.port != _test_url.port
        or _APP_TEST_URL.database != _test_url.database
        or _APP_TEST_URL.username != _test_url.username
        or _APP_TEST_URL.password != _test_url.password
    ):
        drop_isolated_postgres_test_schema(_POSTGRES_APP_SCHEMA)
        raise RuntimeError("Derived application URL differs from the explicit PostgreSQL test connection")
    _APP_PREFLIGHT_ENGINE = create_engine(_APP_TEST_URL, pool_pre_ping=True)
    try:
        _assert_test_database(_APP_PREFLIGHT_ENGINE, _test_url, _POSTGRES_APP_SCHEMA)
    except Exception:
        _APP_PREFLIGHT_ENGINE.dispose()
        drop_isolated_postgres_test_schema(_POSTGRES_APP_SCHEMA)
        raise
    _APP_PREFLIGHT_ENGINE.dispose()
else:
    _APP_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

# Set this explicitly before importing app.main. Its dotenv loader is disabled,
# so a repository .env can never override either isolated test database.
os.environ["DATABASE_URL"] = _APP_DATABASE_URL

def _cleanup_postgres_test_schemas():
    if main is not None:
        main.engine.dispose()
    if _POSTGRES_ADMIN_ENGINE is not None:
        if _POSTGRES_APP_SCHEMA is not None:
            drop_isolated_postgres_test_schema(_POSTGRES_APP_SCHEMA)
        _POSTGRES_ADMIN_ENGINE.dispose()


atexit.register(_TEST_DB_DIR.cleanup)
if _POSTGRES_TEST_URL:
    atexit.register(_cleanup_postgres_test_schemas)

from app.database import Base, engine as _configured_app_engine  # noqa: E402

if _POSTGRES_TEST_URL:
    if (
        _configured_app_engine.url.drivername != _APP_TEST_URL.drivername
        or _configured_app_engine.url.host != _APP_TEST_URL.host
        or _configured_app_engine.url.port != _APP_TEST_URL.port
        or _configured_app_engine.url.database != _APP_TEST_URL.database
        or _configured_app_engine.url.username != _APP_TEST_URL.username
        or _configured_app_engine.url.password != _APP_TEST_URL.password
    ):
        raise RuntimeError("SQLAlchemy database engine differs from the explicit PostgreSQL test URL")
    _assert_test_database(_configured_app_engine, _test_url, _POSTGRES_APP_SCHEMA)

from app import main  # noqa: E402

if _POSTGRES_TEST_URL:
    if main.engine is not _configured_app_engine:
        raise RuntimeError("app.main replaced the validated PostgreSQL test engine")
else:
    atexit.register(main.engine.dispose)


def load_app_for_environment(app_env):
    if app_env is None:
        os.environ["APP_ENV"] = "test"
    else:
        os.environ["APP_ENV"] = app_env
    return importlib.reload(main)


def asgi_request(application, method, path, payload=None, headers=None, return_headers=False, client_ip="127.0.0.1", scheme="https"):
    if not isinstance(application, FastAPI):
        raise TypeError("ASGI client requires the FastAPI instance, not its module")

    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    parsed_path = urlsplit(path)
    request_headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
    ]
    request_headers.extend(
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    )
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": scheme,
        "path": parsed_path.path,
        "raw_path": parsed_path.path.encode("ascii"),
        "query_string": parsed_path.query.encode("ascii"),
        "root_path": "",
        "headers": request_headers,
        "client": (client_ip, 12345),
        "server": ("testserver", 80),
    }
    asyncio.run(application(scope, receive, send))
    status = next(
        message["status"]
        for message in messages
        if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    if response_body:
        try:
            body = json.loads(response_body)
        except json.JSONDecodeError:
            body = response_body.decode("utf-8")
    else:
        body = None
    if return_headers:
        response_headers = next(
            message.get("headers", [])
            for message in messages
            if message["type"] == "http.response.start"
        )
        return status, body, {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in response_headers}
    return status, body


def reset_database():
    """Reset only the temporary test database between test cases."""
    Base.metadata.drop_all(bind=main.engine)
    Base.metadata.create_all(bind=main.engine)
