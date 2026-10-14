import os

from sqlalchemy import Boolean, Column, DateTime, Float, String, create_engine, false, inspect
from sqlalchemy.schema import CreateColumn
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")
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
