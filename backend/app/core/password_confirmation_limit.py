"""Failure limits for password confirmations outside POST /auth/login."""
from datetime import timedelta
import hashlib
import hmac
import math

from fastapi import HTTPException
from sqlalchemy import or_, text

from app.config import settings
from app.core.clock import utc_now_naive
from app.core.request_context import get_client_ip, rate_limit_key
from app.database import SessionLocal
from app.models.user import LoginAttempt

ACCOUNT_ERASURE_PATH = "/users/me:confirmacao-senha"


def _unavailable() -> HTTPException:
    return HTTPException(status_code=503,
                         detail="Não foi possível confirmar a senha agora. Tente novamente em instantes.",
                         headers={"Retry-After": "1"})


def account_key(user_id: int) -> str:
    return hmac.new(settings().secret_key.encode(), f"password-confirmation-user:{user_id}".encode(),
                    hashlib.sha256).hexdigest()


def _lock(db, ip: str, key: str) -> None:
    # Serializes check-and-insert per IP/account so concurrent requests cannot exceed the limit.
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        return
    db.connection(execution_options={"isolation_level": "READ COMMITTED"})
    scopes = ("password-confirmation-ip:" + ip, "password-confirmation-account:" + key)
    identifiers = sorted({int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], "big", signed=True)
                          for scope in scopes})
    for identifier in identifiers:
        db.execute(text("SELECT pg_advisory_xact_lock(:identifier)"), {"identifier": identifier})


def reserve(request, user_id: int, path: str = ACCOUNT_ERASURE_PATH) -> int:
    """Admit one confirmation or raise 429; the row counts as a failure until accepted."""
    configured = settings()
    ip = rate_limit_key(get_client_ip(request))
    key = account_key(user_id)
    maximum = configured.rate_limit_max_attempts
    window = timedelta(minutes=configured.rate_limit_block_minutes)
    db = SessionLocal()
    try:
        _lock(db, ip, key)
        now = utc_now_naive()
        failures = db.query(LoginAttempt.ip, LoginAttempt.account_key, LoginAttempt.ocorrido_em).filter(
            LoginAttempt.rota == path, LoginAttempt.sucesso.is_(False),
            LoginAttempt.ocorrido_em > now - window,
            or_(LoginAttempt.ip == ip, LoginAttempt.account_key == key),
        ).all()
        waits = []
        for scoped in ([row.ocorrido_em for row in failures if row.account_key == key],
                       [row.ocorrido_em for row in failures if row.ip == ip]):
            if len(scoped) >= maximum:
                release = sorted(scoped)[len(scoped) - maximum] + window
                waits.append((release - now).total_seconds())
        if waits:
            db.rollback()
            raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente mais tarde.",
                                headers={"Retry-After": str(max(1, math.ceil(max(waits))))})
        attempt = LoginAttempt(ip=ip, rota=path, account_key=key, sucesso=False, ocorrido_em=now)
        db.add(attempt)
        db.commit()
        return attempt.id
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise _unavailable() from None
    finally:
        db.close()


def _finish(identifier: int, accepted: bool) -> None:
    db = SessionLocal()
    try:
        query = db.query(LoginAttempt).filter(LoginAttempt.id == identifier)
        if accepted:
            query.update({LoginAttempt.sucesso: True}, synchronize_session=False)
        else:
            query.delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def accept(identifier: int) -> None:
    _finish(identifier, accepted=True)


def discard(identifier: int) -> None:
    """Drop an attempt that ended without a password verdict (e.g. saturation)."""
    _finish(identifier, accepted=False)
