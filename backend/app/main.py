import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes do import abaixo, que já lê DATABASE_URL

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.routers import auth, services, appointments, admin, institucional, users, horario, barbeiro_servico
from app.models.user import User, Service, RoleEnum
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Barbearia Agendamento",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/seed")
def seed_demo():
    """Seed initial data for testing"""
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

        return {
            "message": "Dados de demonstração criados com sucesso",
            "usuarios": {
                "admin": {"email": admin_email, "senha": "admin123"},
                "barbeiro": {"email": barbeiro_email, "senha": "barbeiro123"},
                "cliente": {"email": client_email, "senha": "cliente123"}
            }
        }
    finally:
        db.close()