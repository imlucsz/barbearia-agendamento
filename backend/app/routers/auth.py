import hashlib
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.email import send_password_reset_email
from app.core.clock import utc_now_naive
from app.core.security import verify_password, get_password_hash, create_access_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, RoleEnum, PasswordResetToken
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserTokenResponse, EsqueciSenhaRequest, RedefinirSenhaRequest

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
        consentimento_em=utc_now_naive(),
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
    if user:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        reset = PasswordResetToken(
            user_id=user.id,
            token=token_hash,
            expires_at=utc_now_naive() + timedelta(hours=1),
        )
        try:
            # Only the newest outstanding token for this account remains usable.
            db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used.is_(False),
            ).update({PasswordResetToken.used: True}, synchronize_session=False)
            db.add(reset)
            db.flush()
        except Exception:
            db.rollback()
            raise

        try:
            send_password_reset_email(user.email, token)
        except Exception:
            # A failed delivery must not leave an undisclosed usable token behind.
            db.rollback()
            return {"mensagem": "Se o email existir, um link de redefinição foi gerado."}

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    # Same status and body for known/unknown addresses and delivery failures.
    return {"mensagem": "Se o email existir, um link de redefinição foi gerado."}


@router.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    now = utc_now_naive()
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token_hash,
        PasswordResetToken.used.is_(False),
        PasswordResetToken.expires_at > now,
    ).first()
    if not reset:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    # Conditional update makes token consumption atomic and prevents reuse.
    consumed = db.query(PasswordResetToken).filter(
        PasswordResetToken.id == reset.id,
        PasswordResetToken.used.is_(False),
        PasswordResetToken.expires_at > now,
    ).update({PasswordResetToken.used: True}, synchronize_session=False)
    if consumed != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        db.rollback()
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user.senha_hash = get_password_hash(payload.nova_senha)
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset.id,
        PasswordResetToken.used.is_(False),
    ).update({PasswordResetToken.used: True}, synchronize_session=False)
    db.commit()
    return {"mensagem": "Senha redefinida com sucesso"}
