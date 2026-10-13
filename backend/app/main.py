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

# Include routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(appointments.router)
app.include_router(admin.router)
app.include_router(institucional.router)
app.include_router(users.router)
app.include_router(horario.router)
app.include_router(barbeiro_servico.router)


@app.get("/seed")
def seed_demo():
    """Seed initial data for testing"""
    db = SessionLocal()
    try:
        # Create admin user if not exists
        admin_email = "admin@barbearia.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin_user = User(
                nome="Administrador",
                email=admin_email,
                senha_hash=get_password_hash("admin123"),
                role=RoleEnum.ADMIN
            )
            db.add(admin_user)

        # Create barbeiro user if not exists
        barbeiro_email = "barbeiro@barbearia.com"
        barbeiro = db.query(User).filter(User.email == barbeiro_email).first()
        if not barbeiro:
            barbeiro_user = User(
                nome="Barbeiro João",
                email=barbeiro_email,
                senha_hash=get_password_hash("barbeiro123"),
                role=RoleEnum.BARBEIRO
            )
            db.add(barbeiro_user)

        # Create client user if not exists
        client_email = "cliente@barbearia.com"
        client = db.query(User).filter(User.email == client_email).first()
        if not client:
            client_user = User(
                nome="Cliente Maria",
                email=client_email,
                senha_hash=get_password_hash("cliente123"),
                role=RoleEnum.CLIENTE
            )
            db.add(client_user)

        # Create services if not exist
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
                db_service = Service(nome=nome, preco=preco, duracao_minutos=duracao)
                db.add(db_service)

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


@app.get("/")
def root():
    return {"status": "Backend da Barbearia operando perfeitamente!"}