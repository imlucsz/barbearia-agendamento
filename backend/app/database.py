from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from app.config import settings as load_app_settings
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker


_settings = load_app_settings()
APP_ENV = _settings.app_env
DATABASE_URL = _settings.database_url

engine_options = {"connect_args": {"check_same_thread": False}} if _settings.database_backend == "sqlite" else {}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def expected_migration_heads():
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    return set(ScriptDirectory.from_config(Config(str(config_path))).get_heads())


def check_schema_revision(database_engine=engine):
    """Return revision readiness without issuing DDL or exposing connection details."""
    try:
        with database_engine.connect() as connection:
            inspector = inspect(connection)
            if "alembic_version" not in inspector.get_table_names():
                return False, "missing"
            revisions = set(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
            if revisions != expected_migration_heads():
                return False, ",".join(sorted(revisions)) or "empty"
            return True, ",".join(sorted(revisions))
    except SQLAlchemyError:
        return False, "unavailable"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
