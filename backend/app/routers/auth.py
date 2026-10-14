from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, RoleEnum, PasswordResetToken
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserTokenResponse, EsqueciSenhaRequest, RedefinirSenhaRequest
from app.core.security import verify_password, get_password_hash, create_access_token
import secrets
import os
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if not user.consentimento_lgpd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O consentimento para tratamento de dados é obrigatório")

    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )

    # Create new user
    hashed_password = get_password_hash(user.senha)
    db_user = User(
        nome=user.nome,
        email=user.email,
        senha_hash=hashed_password,
        role=RoleEnum.CLIENTE,
        consentimento_lgpd=True,
        consentimento_em=datetime.utcnow(),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=UserTokenResponse)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.senha, db_user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Check if user is active
    if not db_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta inativa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if db_user.bloqueado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta bloqueada")

    # Create access token
    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/esqueci-senha")
def esqueci_senha(payload: EsqueciSenhaRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Sempre retorna a mesma mensagem, exista ou não o email (evita enumeração de usuários)
    if user:
        token = secrets.token_urlsafe(32)
        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset)
        db.commit()
        response = {"mensagem": "Se o email existir, um link de redefinição foi gerado."}
        if os.getenv("APP_ENV", "development").lower() == "development":
            response["dev_token"] = token
        return response
    return {"mensagem": "Se o email existir, um link de redefinição foi gerado."}


@router.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == payload.token,
        PasswordResetToken.used == False,
    ).first()

    if not reset or reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user = db.query(User).filter(User.id == reset.user_id).first()
    user.senha_hash = get_password_hash(payload.nova_senha)  # usa a função de hash já existente
    reset.used = True
    db.commit()
    return {"mensagem": "Senha redefinida com sucesso"}