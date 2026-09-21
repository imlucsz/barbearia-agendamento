import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Em produção/PostgreSQL, defina DATABASE_URL no ambiente, por exemplo:
# postgresql+psycopg2://usuario:senha@localhost:5432/barbearia
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")

# connect_args com check_same_thread só existe (e só é necessário) no SQLite.
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # evita erro de conexão "caída" ao reconectar no Postgres
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()