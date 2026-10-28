import ipaddress
import os
import re
from datetime import datetime
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes do import abaixo, que já lê DATABASE_URL
APP_ENV = os.getenv("APP_ENV", "").strip().lower()
_CORS_ORIGIN_ERROR = (
    "CORS_ALLOWED_ORIGINS entries must be valid HTTP(S) origins without wildcards, "
    "credentials, paths, queries, or fragments"
)
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def _normalize_cors_hostname(hostname: str) -> str:
    if "*" in hostname:
        raise RuntimeError(_CORS_ORIGIN_ERROR)

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if not hostname or any(character.isspace() for character in hostname):
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        if all(character in "0123456789." for character in hostname):
            raise RuntimeError(_CORS_ORIGIN_ERROR)

        try:
            dns_name = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        labels = dns_name[:-1].split(".") if dns_name.endswith(".") else dns_name.split(".")
        if (
            len(dns_name) > 254
            or any(not label or len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in labels)
        ):
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        return dns_name

    if isinstance(address, ipaddress.IPv6Address):
        if address.scope_id is not None:
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        return f"[{address.compressed.lower()}]"
    return str(address)


def _configured_cors_origins(app_env: str | None = None) -> list[str]:
    environment = APP_ENV if app_env is None else app_env.strip().lower()
    configured = os.getenv("CORS_ALLOWED_ORIGINS")
    if configured is None:
        if environment == "production":
            raise RuntimeError(
                "CORS_ALLOWED_ORIGINS must be explicitly configured in production"
            )
        return ["http://127.0.0.1:5500"] if environment == "development" else []

    origins = []
    seen = set()
    for origin in (value.strip() for value in configured.split(",")):
        if not origin:
            continue
        if any(character.isspace() for character in origin) or "?" in origin or "#" in origin:
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None

        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        if (
            scheme not in {"http", "https"}
            or not parsed.netloc
            or hostname is None
            or parsed.path not in {"", "/"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        if environment == "production" and scheme != "https":
            raise RuntimeError("Production CORS origins must use HTTPS")

        try:
            port = parsed.port
        except ValueError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        if parsed.netloc.endswith(":") or (port is not None and not 1 <= port <= 65535):
            raise RuntimeError(_CORS_ORIGIN_ERROR)

        normalized_host = _normalize_cors_hostname(hostname)
        default_port = 80 if scheme == "http" else 443
        normalized = f"{scheme}://{normalized_host}"
        if port is not None and port != default_port:
            normalized += f":{port}"
        if normalized not in seen:
            seen.add(normalized)
            origins.append(normalized)
    if environment == "production" and not origins:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must contain at least one HTTPS origin in production"
        )
    return origins


CORS_ALLOWED_ORIGINS = _configured_cors_origins()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal, ensure_schema_updates
from app.routers import auth, services, appointments, admin, institucional, users, horario, barbeiro_servico
from app.models.user import User, Service, RoleEnum
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)
ensure_schema_updates()

app = FastAPI(
    title="API Barbearia Agendamento",
    version="1.0.0"
)

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


if APP_ENV == "development":
    @app.get("/seed")
    def seed_demo():
        """Create local demonstration users and services."""
        db = SessionLocal()
        try:
            admin_email = "admin@barbearia.com"
            admin_user = db.query(User).filter(User.email == admin_email).first()
            if not admin_user:
                admin_user = User(
                    nome="Administrador",
                    email=admin_email,
                    senha_hash=get_password_hash("admin123"),
                    role=RoleEnum.ADMIN
                )
                db.add(admin_user)

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
