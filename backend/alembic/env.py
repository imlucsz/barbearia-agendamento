import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.database import Base
from app.models import user as _user_models  # noqa: F401


config = context.config
if config.config_file_name is not None:
    # Alembic may run inside a process that already has application loggers.
    # Do not disable them when loading the migration logging configuration.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline():
    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set in the environment or backend/.env")
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=database_url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection):
    is_sqlite = connection.dialect.name == "sqlite"
    if is_sqlite:
        # Batch table recreation must be able to replace a referenced table.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()

    try:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()
            if is_sqlite:
                violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise RuntimeError(
                        "SQLite migration produced foreign-key violations; transaction rolled back"
                    )
    finally:
        if is_sqlite:
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()


def run_migrations_online():
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        _run_migrations(supplied_connection)
        return

    from dotenv import load_dotenv

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set in the environment or backend/.env")

    connectable = create_engine(database_url, poolclass=NullPool)
    try:
        with connectable.connect() as connection:
            _run_migrations(connection)
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
