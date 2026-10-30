import hashlib
import os
import secrets
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core.email import send_password_reset_email
from app.core.clock import utc_now_naive
from app.core.security import verify_password_and_update, get_password_hash, create_access_token
from app.core.request_context import get_client_ip
from app.config import parse_cors_origins
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import ConsentimentoLGPD, User, RoleEnum, PasswordResetToken, RefreshToken
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserTokenResponse, EsqueciSenhaRequest, RedefinirSenhaRequest
from app.core.audit import record as record_audit

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_TOKEN_TTL = timedelta(days=30)
REFRESH_COOKIE_NAME = "refresh_token"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token(db: Session, user_id: int, family_id: str | None = None):
    token = secrets.token_urlsafe(48)
    row = RefreshToken(
        user_id=user_id,
        token_hash=_token_hash(token),
        family_id=family_id or str(uuid.uuid4()),
        expires_at=utc_now_naive() + REFRESH_TOKEN_TTL,
    )
    db.add(row)
    db.flush()
    return token, row


def revoke_user_refresh_tokens(db: Session, user_id: int, now=None) -> None:
    now = now or utc_now_naive()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).update({RefreshToken.revoked_at: now}, synchronize_session=False)


def _set_refresh_cookie(response: Response, token: str | None) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token or "",
        httponly=True,
        secure=os.environ.get("APP_ENV", "").strip().lower() == "production",
        samesite="lax",
        path="/auth",
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()) if token else 0,
    )


def _require_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(status_code=403, detail="Origem não autorizada")
    environment = os.environ.get("APP_ENV", "test").strip().lower()
    if environment not in {"development", "production", "test"}:
        environment = "test"
    try:
        normalized = parse_cors_origins(origin, "development")
        configured = parse_cors_origins(os.environ.get("CORS_ALLOWED_ORIGINS"), environment)
    except RuntimeError:
        normalized = ()
        configured = ()
    if not normalized or normalized[0] not in configured:
        raise HTTPException(status_code=403, detail="Origem não autorizada")


def _terms_version() -> str:
    version = os.environ.get("TERMS_VERSION", "1.0").strip()
    if not version or len(version) > 100:
        raise RuntimeError("TERMS_VERSION must contain between 1 and 100 characters")
    return version


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
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
    db.flush()
    db.add(ConsentimentoLGPD(
        user_id=db_user.id,
        versao_termos=_terms_version(),
        aceito_em=db_user.consentimento_em,
        ip_origem=get_client_ip(request),
        origem=(request.headers.get("origin") or "direct")[:255],
    ))
    record_audit(db, request, actor=db_user, acao="usuario.cadastrado", entidade="usuario", entidade_id=db_user.id)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=UserTokenResponse)
def login_user(user: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    # Find user by email
    db_user = db.query(User).filter(User.email == user.email).first()
    password_valid, upgraded_hash = (
        verify_password_and_update(user.senha, db_user.senha_hash)
        if db_user else (False, None)
    )
    if not db_user or not password_valid:
        record_audit(db, request, actor=None, acao="auth.login", entidade="sessao", resultado="falha")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Check if user is active
    if not db_user.ativo:
        record_audit(db, request, actor=db_user, acao="auth.login", entidade="sessao", resultado="falha", detalhes={"motivo": "conta_inativa"})
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta inativa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if db_user.bloqueado:
        record_audit(db, request, actor=db_user, acao="auth.login", entidade="sessao", resultado="falha", detalhes={"motivo": "conta_bloqueada"})
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta bloqueada")

    if upgraded_hash:
        db_user.senha_hash = upgraded_hash

    # Create access token
    access_token = create_access_token(data={"sub": db_user.email})
    refresh_token, _refresh_row = _new_refresh_token(db, db_user.id)
    record_audit(db, request, actor=db_user, acao="auth.login", entidade="sessao")
    db.commit()
    _set_refresh_cookie(response, refresh_token)

    return {
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
    }


@router.post("/refresh")
def refresh_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    _require_allowed_origin(request)
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    now = utc_now_naive()
    current = db.query(RefreshToken).filter(RefreshToken.token_hash == _token_hash(raw_token)).first()
    if current is None:
        raise HTTPException(status_code=401, detail="Sessão expirada")
    if current.replaced_by_id is not None:
        user = db.query(User).filter(User.id == current.user_id).first()
        record_audit(db, request, actor=user, acao="auth.refresh_reuse", entidade="refresh_token", resultado="falha")
        db.query(RefreshToken).filter(
            RefreshToken.family_id == current.family_id,
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: now}, synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=401, detail="Sessão revogada")
    if current.revoked_at is not None or current.expires_at <= now:
        raise HTTPException(status_code=401, detail="Sessão expirada")

    user = db.query(User).filter(User.id == current.user_id).first()
    if user is None or not user.ativo or user.bloqueado:
        revoke_user_refresh_tokens(db, current.user_id, now)
        db.commit()
        raise HTTPException(status_code=401, detail="Sessão revogada")

    replacement_token, replacement = _new_refresh_token(db, user.id, current.family_id)
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == current.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now, replaced_by_id=replacement.id)
    )
    if result.rowcount != 1:
        db.rollback()
        current = db.query(RefreshToken).filter(RefreshToken.token_hash == _token_hash(raw_token)).first()
        if current is not None and current.replaced_by_id is not None:
            db.query(RefreshToken).filter(
                RefreshToken.family_id == current.family_id,
                RefreshToken.revoked_at.is_(None),
            ).update({RefreshToken.revoked_at: now}, synchronize_session=False)
            db.commit()
        raise HTTPException(status_code=401, detail="Sessão revogada")
    db.commit()
    _set_refresh_cookie(response, replacement_token)
    return {"access_token": create_access_token(data={"sub": user.email}), "token_type": "bearer"}


@router.post("/logout")
def logout_session(request: Request, response: Response, db: Session = Depends(get_db)):
    _require_allowed_origin(request)
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        row = db.query(RefreshToken).filter(RefreshToken.token_hash == _token_hash(raw_token)).first()
        user = db.query(User).filter(User.id == row.user_id).first() if row else None
        db.query(RefreshToken).filter(
            RefreshToken.token_hash == _token_hash(raw_token),
            RefreshToken.revoked_at.is_(None),
        ).update({RefreshToken.revoked_at: utc_now_naive()}, synchronize_session=False)
        record_audit(db, request, actor=user, acao="auth.logout", entidade="sessao")
        db.commit()
    else:
        record_audit(db, request, actor=None, acao="auth.logout", entidade="sessao")
        db.commit()
    _set_refresh_cookie(response, None)
    return {"mensagem": "Sessão encerrada"}


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/esqueci-senha")
def esqueci_senha(payload: EsqueciSenhaRequest, request: Request, db: Session = Depends(get_db)):
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

    record_audit(db, request, actor=user if user else None, acao="auth.redefinicao_solicitada", entidade="credencial", resultado="sucesso")
    db.commit()
    # Same status and body for known/unknown addresses and delivery failures.
    return {"mensagem": "Se o email existir, um link de redefinição foi gerado."}


@router.post("/redefinir-senha")
def redefinir_senha(payload: RedefinirSenhaRequest, request: Request, db: Session = Depends(get_db)):
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
    revoke_user_refresh_tokens(db, user.id)
    record_audit(db, request, actor=user, acao="auth.senha_redefinida", entidade="credencial")
    db.commit()
    return {"mensagem": "Senha redefinida com sucesso"}
