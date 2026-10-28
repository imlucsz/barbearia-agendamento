import os

from sqlalchemy import Boolean, Column, DateTime, Float, String, create_engine, false, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.schema import CreateColumn
from sqlalchemy.orm import declarative_base, sessionmaker


APP_ENV = os.getenv("APP_ENV", "").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    if APP_ENV == "development":
        DATABASE_URL = "sqlite:///./barbearia.db"
    else:
        raise RuntimeError(
            "DATABASE_URL must be explicitly configured unless APP_ENV=development"
        )
if APP_ENV == "production":
    try:
        database_backend = make_url(DATABASE_URL).get_backend_name()
    except (ArgumentError, TypeError, ValueError):
        raise RuntimeError("DATABASE_URL is invalid") from None
    if database_backend == "sqlite":
        raise RuntimeError("SQLite DATABASE_URL is not allowed when APP_ENV=production")

engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_updates():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    with engine.begin() as connection:
        if "appointments" in tables:
            appointment_columns = {column["name"] for column in inspect(connection).get_columns("appointments")}
            if "valor_cobrado" not in appointment_columns:
                column = CreateColumn(Column("valor_cobrado", Float())).compile(dialect=connection.dialect)
                connection.exec_driver_sql(f"ALTER TABLE appointments ADD COLUMN {column}")
            if "nome_cliente" not in appointment_columns:
                column = CreateColumn(Column("nome_cliente", String())).compile(dialect=connection.dialect)
                connection.exec_driver_sql(f"ALTER TABLE appointments ADD COLUMN {column}")
        if "users" in tables:
            user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
            if "consentimento_lgpd" not in user_columns:
                column = CreateColumn(
                    Column("consentimento_lgpd", Boolean(), nullable=False, server_default=false())
                ).compile(dialect=connection.dialect)
                connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column}")
            if "consentimento_em" not in user_columns:
                column = CreateColumn(Column("consentimento_em", DateTime())).compile(dialect=connection.dialect)
                connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
