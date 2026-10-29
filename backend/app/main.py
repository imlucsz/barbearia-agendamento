import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes do import abaixo, que já lê DATABASE_URL
from app.config import get_app_environment, parse_cors_origins

APP_ENV = get_app_environment()


def _configured_cors_origins(app_env: str | None = None) -> list[str]:
    environment = APP_ENV if app_env is None else app_env.strip().lower()
    return list(parse_cors_origins(os.getenv("CORS_ALLOWED_ORIGINS"), environment))


CORS_ALLOWED_ORIGINS = _configured_cors_origins()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import check_schema_revision, engine, SessionLocal
from app.routers import auth, services, appointments, admin, institucional, users, horario, barbeiro_servico
from app.models.user import User, Service, RoleEnum
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)


def verify_database_migrations():
    current, _revision = check_schema_revision(engine)
    if not current:
        logger.warning(
            "Banco indisponível ou fora da revisão Alembic esperada; "
            "execute `python -m alembic upgrade head` antes de servir requisições.",
        )


@asynccontextmanager
async def lifespan(_app):
    verify_database_migrations()
    yield


app = FastAPI(
    title="API Barbearia Agendamento",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(request: Request, exc: RequestValidationError):
    """Keep validation details useful without echoing submitted secrets or PII."""
    details = [
        {key: error[key] for key in ("loc", "msg", "type") if key in error}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(appointments.router)
app.include_router(admin.router)
app.include_router(institucional.router)
app.include_router(users.router)
app.include_router(horario.router)
app.include_router(barbeiro_servico.router)


@app.get("/")
def root():
    return {"status": "Backend da Barbearia operando perfeitamente!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    """Readiness requires the expected Alembic schema revision."""
    current, _revision = check_schema_revision(engine)
    if not current:
        raise HTTPException(status_code=503, detail="Application unavailable") from None
    return {"status": "ready"}


if APP_ENV == "development":
    @app.get("/seed")
    def seed_demo():
        """Create local demonstration users and services."""
        db = SessionLocal()
        try:
            barbeiro_email = "barbeiro@barbearia.com"
            barbeiro = db.query(User).filter(User.email == barbeiro_email).first()
            if not barbeiro:
                barbeiro = User(
                    nome="Barbeiro João",
                    email=barbeiro_email,
                    senha_hash=get_password_hash("barbeiro123"),
                    role=RoleEnum.BARBEIRO
                )
                db.add(barbeiro)

            client_email = "cliente@barbearia.com"
            client = db.query(User).filter(User.email == client_email).first()
            if not client:
                client = User(
                    nome="Cliente Maria",
                    email=client_email,
                    senha_hash=get_password_hash("cliente123"),
                    role=RoleEnum.CLIENTE
                )
                db.add(client)

            services_data = [
                ("Corte", 35.00, 40),
                ("Barba", 25.00, 30),
                ("Corte + Barba", 55.00, 60),
                ("Tratamento Capilar", 45.00, 50),
                ("Sobrancelha", 15.00, 20)
            ]
            for nome, preco, duracao in services_data:
                service = db.query(Service).filter(Service.nome == nome).first()
                if not service:
                    db.add(Service(nome=nome, preco=preco, duracao_minutos=duracao))

            db.commit()

            return {"message": "Dados de demonstração criados com sucesso"}
        finally:
            db.close()
