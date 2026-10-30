import logging
import os
import uuid
import asyncio
import hmac
from types import SimpleNamespace
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes do import abaixo, que já lê DATABASE_URL
from app.config import get_app_environment, parse_allowed_hosts, parse_cors_origins

APP_ENV = get_app_environment()
INSTALLATION_NAME = os.environ.get("INSTALLATION_NAME", "Barbearia").strip() or "Barbearia"
def _security_settings():
    raw = os.environ.get("FORCE_HTTPS", "true" if APP_ENV == "production" else "false").strip().lower()
    force_https = raw in {"true", "1", "yes"}
    return SimpleNamespace(
        app_env=APP_ENV,
        force_https=force_https,
        allowed_hosts=parse_allowed_hosts(os.getenv("ALLOWED_HOSTS"), APP_ENV),
    )


SECURITY_SETTINGS = _security_settings()


def _configured_cors_origins(app_env: str | None = None) -> list[str]:
    environment = APP_ENV if app_env is None else app_env.strip().lower()
    return list(parse_cors_origins(os.getenv("CORS_ALLOWED_ORIGINS"), environment))


CORS_ALLOWED_ORIGINS = _configured_cors_origins()
METRICS_TOKEN = os.environ.get("METRICS_TOKEN", "").strip()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.database import check_schema_revision, engine, SessionLocal
from app.routers import auth, services, appointments, admin, institucional, users, horario, barbeiro_servico
from app.models.user import User, Service, RoleEnum
from app.core.security import get_password_hash
from app.core.rate_limit import AuthRateLimitMiddleware
from app.core.observability import RequestObservabilityMiddleware, metrics_text

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
    title=f"API {INSTALLATION_NAME}",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if APP_ENV == "production" else "/docs",
    redoc_url=None if APP_ENV == "production" else "/redoc",
    openapi_url=None if APP_ENV == "production" else "/openapi.json",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        incoming_request_id = request.headers.get("x-request-id", "")
        request.state.request_id = incoming_request_id if incoming_request_id and len(incoming_request_id) <= 64 and incoming_request_id.isascii() and incoming_request_id.replace("-", "").isalnum() else str(uuid.uuid4())
        configured = SECURITY_SETTINGS
        if configured.force_https:
            scheme = request.url.scheme
            if scheme == "http":
                target = request.url.replace(scheme="https")
                response = RedirectResponse(str(target), status_code=307)
                response.headers["X-Request-ID"] = request.state.request_id
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
                response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                response.headers["X-Frame-Options"] = "DENY"
                if configured.app_env == "production":
                    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                return response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Frame-Options"] = "DENY"
        if configured.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(AuthRateLimitMiddleware)


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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestObservabilityMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=list(SECURITY_SETTINGS.allowed_hosts),
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
    return {"status": "Backend da instalação operando perfeitamente!"}


@app.get("/health")
async def health():
    """Liveness plus a bounded database connectivity check (SELECT 1)."""
    try:
        await asyncio.wait_for(asyncio.to_thread(_ping_database), timeout=1.0)
    except Exception:
        raise HTTPException(status_code=503, detail="Application unavailable") from None
    return {"status": "ok"}


def _ping_database():
    from sqlalchemy import text

    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics(request: Request):
    if not METRICS_TOKEN:
        raise HTTPException(status_code=404, detail="Not Found")
    authorization = request.headers.get("authorization", "")
    scheme, separator, supplied_token = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(supplied_token.encode("utf-8"), METRICS_TOKEN.encode("utf-8"))
    ):
        raise HTTPException(status_code=401, detail="Invalid metrics credentials")
    return Response(content=metrics_text(), media_type="text/plain; version=0.0.4; charset=utf-8")


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
