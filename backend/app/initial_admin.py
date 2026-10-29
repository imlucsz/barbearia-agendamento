"""One-time interactive bootstrap for the first installation administrator."""

import getpass
import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

load_dotenv()

from app.database import Base, DATABASE_URL, SessionLocal, engine
from app.models.user import RoleEnum, User


def validate_installation_for_admin_bootstrap() -> None:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    if app_env not in {"development", "production"}:
        raise RuntimeError("Bootstrap requires APP_ENV=development or APP_ENV=production")
    if not DATABASE_URL:
        raise RuntimeError("Configure DATABASE_URL for this installation")
    if app_env == "production" and engine.dialect.name != "postgresql":
        raise RuntimeError("Production administrator bootstrap requires PostgreSQL")
    if engine.dialect.name not in {"sqlite", "postgresql"}:
        raise RuntimeError("Bootstrap supports local SQLite or PostgreSQL only")

    try:
        tables = set(inspect(engine).get_table_names())
        required_tables = set(Base.metadata.tables) | {"alembic_version"}
        if not required_tables.issubset(tables):
            raise RuntimeError("Run Alembic migrations before administrator bootstrap")

        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        heads = set(ScriptDirectory.from_config(config).get_heads())
        with engine.connect() as connection:
            versions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        if versions != heads:
            raise RuntimeError("Upgrade the database to the current Alembic revision before bootstrap")
    except SQLAlchemyError:
        raise RuntimeError("Could not verify database schema and migrations") from None


def create_initial_admin(db: Session, *, nome: str, email: str, password: str) -> User:
    nome = nome.strip()
    email = email.strip().lower()
    if not nome or len(password) < 12:
        raise ValueError("Provide a name and a password with at least 12 characters")

    if db.bind.dialect.name == "postgresql":
        # Serialize one-time attempts before reading whether an administrator exists.
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": 842760184203})
    elif db.bind.dialect.name == "sqlite":
        # SQLite is permitted only for explicit local development bootstrap.
        db.execute(text("BEGIN IMMEDIATE"))
    else:
        raise RuntimeError("Bootstrap supports SQLite or PostgreSQL only")

    if db.query(User).filter(User.role == RoleEnum.ADMIN).first():
        raise ValueError("This installation already has an administrator")
    if db.query(User).filter(User.email == email).first():
        raise ValueError("This email is already registered")

    from app.core.security import get_password_hash

    admin = User(
        nome=nome,
        email=email,
        senha_hash=get_password_hash(password),
        role=RoleEnum.ADMIN,
        ativo=True,
        bloqueado=False,
        consentimento_lgpd=False,
        consentimento_em=None,
    )
    db.add(admin)
    try:
        db.commit()
        db.refresh(admin)
    except Exception:
        db.rollback()
        raise RuntimeError("Could not create the initial administrator") from None
    return admin


def main() -> None:
    load_dotenv()
    validate_installation_for_admin_bootstrap()

    with SessionLocal() as db:
        if db.query(User).filter(User.role == RoleEnum.ADMIN).first():
            raise SystemExit("This installation already has an administrator")

    nome = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError:
        raise SystemExit("Provide a valid email address") from None

    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    if len(password) < 12:
        raise SystemExit("Use a password with at least 12 characters")

    with SessionLocal() as db:
        create_initial_admin(db, nome=nome, email=email, password=password)
    print("Initial administrator created.")


if __name__ == "__main__":
    main()
