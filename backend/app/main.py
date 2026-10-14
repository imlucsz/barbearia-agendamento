import os
from datetime import date, datetime

from dotenv import load_dotenv

load_dotenv()  # precisa rodar antes do import abaixo, que já lê DATABASE_URL

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.database import Base, engine, get_db
from app.dependencies import get_current_user
from app.models.user import Appointment, RoleEnum, Service, User, InformacaoInstitucional
from app.routers.appointments import router as appointments_router
from app.routers.barbeiro_servico import router as barbeiro_servico_router


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

app.include_router(appointments_router)
app.include_router(barbeiro_servico_router)

@app.get("/")
def root():
    return {"status": "Backend da Barbearia operando perfeitamente!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register_user(payload: dict, db: Session = Depends(get_db)):
    nome = str(payload.get("nome") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    senha = str(payload.get("senha") or "")

    if not nome or not email or len(senha) < 6:
        raise HTTPException(status_code=400, detail="Nome, email e senha são obrigatórios.")

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido.")

    existente = db.query(User).filter(User.email == email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Usuário já cadastrado.")

    usuario = User(
        nome=nome,
        email=email,
        senha_hash=get_password_hash(senha),
        role=RoleEnum.CLIENTE,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "role": usuario.role.value,
    }


@app.post("/auth/login")
def login_user(payload: dict, db: Session = Depends(get_db)):
    email = str(payload.get("email") or "").strip().lower()
    senha = str(payload.get("senha") or "")

    if not email or not senha:
        raise HTTPException(status_code=400, detail="E-mail e senha são obrigatórios.")

    usuario = db.query(User).filter(User.email == email).first()
    if not usuario or not verify_password(senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas.")

    token = create_access_token({"sub": usuario.email, "role": usuario.role.value, "user_id": usuario.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "role": usuario.role.value,
        },
    }


@app.get("/services")
def listar_servicos(db: Session = Depends(get_db)):
    servicos = db.query(Service).order_by(Service.nome.asc()).all()
    return [{
        "id": s.id,
        "nome": s.nome,
        "preco": s.preco,
        "duracao_minutos": s.duracao_minutos,
    } for s in servicos]


@app.post("/appointments")
def criar_agendamento(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service_id = payload.get("service_id")
    profissional = str(payload.get("profissional") or "Barbeiro").strip() or "Barbeiro"
    data_hora = payload.get("data_hora")

    if not service_id or not data_hora:
        raise HTTPException(status_code=400, detail="service_id e data_hora são obrigatórios.")

    servico = db.query(Service).filter(Service.id == service_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")

    try:
        if isinstance(data_hora, str):
            data_hora_dt = datetime.fromisoformat(data_hora)
        else:
            data_hora_dt = datetime.fromisoformat(str(data_hora))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Formato de data_hora inválido. Use ISO 8601.") from exc

    agendamento = Appointment(
        user_id=current_user.id,
        service_id=servico.id,
        data_hora=data_hora_dt,
        profissional_nome=profissional,
        status=str(payload.get("status") or "pendente").lower(),
    )
    db.add(agendamento)
    db.commit()
    db.refresh(agendamento)

    return {
        "id": agendamento.id,
        "user_id": agendamento.user_id,
        "service_id": agendamento.service_id,
        "horario": agendamento.data_hora.strftime("%H:%M"),
        "data": agendamento.data_hora.strftime("%Y-%m-%d"),
        "profissional": agendamento.profissional_nome,
        "status": agendamento.status,
    }


@app.get("/admin/agenda")
def listar_agenda_admin(
    data: str = Query(..., description="Data em formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador.")

    try:
        data_obj = datetime.strptime(data, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Data inválida. Use o formato YYYY-MM-DD.") from exc

    agendamentos = (
        db.query(Appointment)
        .filter(func.date(Appointment.data_hora) == data_obj)
        .order_by(Appointment.data_hora.asc())
        .all()
    )

    resultado = []
    for agendamento in agendamentos:
        resultado.append({
            "id": agendamento.id,
            "horario": agendamento.data_hora.strftime("%H:%M"),
            "cliente": agendamento.user.nome if agendamento.user else "Cliente",
            "servico": agendamento.service.nome if agendamento.service else "Serviço",
            "profissional": agendamento.profissional_nome or "Barbeiro",
            "status": agendamento.status,
        })

    return resultado


@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "role": current_user.role.value,
    }


@app.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    admin_email = "admin@barbearia.com"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        admin = User(
            nome="Administrador",
            email=admin_email,
            senha_hash=get_password_hash("admin123"),
            role=RoleEnum.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    servicos = [
        ("Corte", 35.00, 40),
        ("Barba", 25.00, 30),
        ("Corte + Barba", 55.00, 60),
    ]

    for nome, preco, duracao in servicos:
        existente = db.query(Service).filter(Service.nome == nome).first()
        if not existente:
            db.add(Service(nome=nome, preco=preco, duracao_minutos=duracao))

    db.commit()

    cliente = db.query(User).filter(User.email == "cliente@barbearia.com").first()
    if not cliente:
        cliente = User(
            nome="Cliente Demo",
            email="cliente@barbearia.com",
            senha_hash=get_password_hash("cliente123"),
            role=RoleEnum.CLIENTE,
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    servico = db.query(Service).filter(Service.nome == "Corte").first()
    if servico:
        hoje = datetime.now()
        agendado = db.query(Appointment).filter(
            Appointment.user_id == cliente.id,
            Appointment.service_id == servico.id,
            Appointment.data_hora >= hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        ).first()

        if not agendado:
            db.add(Appointment(
                user_id=cliente.id,
                service_id=servico.id,
                data_hora=hoje.replace(hour=9, minute=30, second=0, microsecond=0),
                profissional_nome="Rafael",
                status="confirmado",
            ))
            db.commit()

    return {
        "message": "Dados demo criados com sucesso.",
        "admin": {"email": admin_email, "senha": "admin123"},
        "cliente": {"email": "cliente@barbearia.com", "senha": "cliente123"},
    }


@app.get("/informacoes")
def get_informacoes(db: Session = Depends(get_db)):
    informacao = db.query(InformacaoInstitucional).first()
    if informacao is None:
        # Return a default or empty structure? We'll return an empty dict or raise 404?
        # For the frontend, it expects certain fields. We'll return a default with empty strings.
        return {
            "nome": "",
            "endereco": "",
            "telefone": "",
            "email": "",
            "site": "",
            "horario_funcionamento": "",
            "dias_atendimento": "",
            "endereco_maps": ""
        }
    return {
        "nome": informacao.nome,
        "endereco": informacao.endereco,
        "telefone": informacao.telefone,
        "email": informacao.email,
        "site": informacao.site,
        "horario_funcionamento": informacao.horario_funcionamento,
        "dias_atendimento": informacao.dias_atendimento,
        "endereco_maps": informacao.endereco_maps
    }