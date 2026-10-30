"""Database-backed consecutive failure limits for authentication endpoints."""

from datetime import timedelta
import math

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings as load_settings
from app.core.clock import utc_now_naive
from app.core.request_context import get_client_ip
from app.database import SessionLocal
from app.models.user import LoginAttempt

RATE_SETTINGS = load_settings()

AUTH_PATHS = {
    "/auth/login", "/auth/register", "/auth/esqueci-senha", "/auth/redefinir-senha",
}
EXPORT_PATH = "/users/me/exportacao"
EXPORT_PATHS = {EXPORT_PATH, "/users/me/export"}


def _cleanup_old_attempts():
    db = SessionLocal()
    try:
        cutoff = utc_now_naive() - timedelta(days=30)
        old = (db.query(LoginAttempt.id).filter(LoginAttempt.ocorrido_em < cutoff)
               .order_by(LoginAttempt.ocorrido_em).limit(500).all())
        if old:
            db.query(LoginAttempt).filter(LoginAttempt.id.in_([row[0] for row in old])).delete(synchronize_session=False)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        is_export = request.url.path in EXPORT_PATHS and request.method == "GET"
        is_auth = request.url.path in AUTH_PATHS and request.method == "POST"
        if not is_export and not is_auth:
            return await call_next(request)
        try:
            ip = get_client_ip(request)
        except Exception:
            raise
        now = utc_now_naive()
        window_start = now - timedelta(minutes=RATE_SETTINGS.rate_limit_block_minutes)
        db = SessionLocal()
        try:
            if is_export:
                attempts = (db.query(LoginAttempt).filter(
                    LoginAttempt.ip == ip, LoginAttempt.rota == EXPORT_PATH,
                    LoginAttempt.ocorrido_em >= window_start,
                ).order_by(LoginAttempt.ocorrido_em.asc(), LoginAttempt.id.asc())
                    .limit(RATE_SETTINGS.rate_limit_max_attempts).all())
                if len(attempts) >= RATE_SETTINGS.rate_limit_max_attempts:
                    remaining = math.ceil((attempts[0].ocorrido_em + timedelta(minutes=RATE_SETTINGS.rate_limit_block_minutes) - now).total_seconds())
                    if remaining > 0:
                        return JSONResponse({"detail": "Muitas exportações. Tente novamente mais tarde."}, status_code=429,
                                            headers={"Retry-After": str(remaining)})
                history = []
            else:
                history = (db.query(LoginAttempt).filter(
                    LoginAttempt.ip == ip, LoginAttempt.rota == request.url.path,
                    LoginAttempt.ocorrido_em >= window_start,
                ).order_by(LoginAttempt.ocorrido_em.desc(), LoginAttempt.id.desc())
                    .limit(RATE_SETTINGS.rate_limit_max_attempts).all())
            failures = 0
            last_failure = None
            for row in history:
                if row.sucesso:
                    break
                if last_failure is None:
                    last_failure = row.ocorrido_em
                failures += 1
            configured = RATE_SETTINGS
            if failures >= configured.rate_limit_max_attempts and last_failure:
                remaining = math.ceil((last_failure + timedelta(minutes=configured.rate_limit_block_minutes) - now).total_seconds())
                if remaining > 0:
                    return JSONResponse({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status_code=429,
                                        headers={"Retry-After": str(remaining)})
        finally:
            db.close()

        response = await call_next(request)
        db = SessionLocal()
        try:
            success = response.status_code < 400 and request.url.path != "/auth/esqueci-senha"
            db.add(LoginAttempt(ip=ip, rota=EXPORT_PATH if is_export else request.url.path, sucesso=success, ocorrido_em=now))
            db.commit()
            if is_export:
                tasks = BackgroundTasks()
                if response.background is not None:
                    tasks.add_task(response.background)
                tasks.add_task(_cleanup_old_attempts)
                response.background = tasks
                return response
            recent = (db.query(LoginAttempt).filter(
                LoginAttempt.ip == ip, LoginAttempt.rota == request.url.path,
                LoginAttempt.ocorrido_em >= window_start,
            ).order_by(LoginAttempt.ocorrido_em.desc(), LoginAttempt.id.desc())
             .limit(RATE_SETTINGS.rate_limit_max_attempts).all())
            if len(recent) >= RATE_SETTINGS.rate_limit_max_attempts and all(not row.sucesso for row in recent):
                configured = RATE_SETTINGS
                retry = math.ceil((recent[0].ocorrido_em + timedelta(minutes=configured.rate_limit_block_minutes) - now).total_seconds())
                if retry > 0:
                    return JSONResponse({"detail": "Muitas tentativas. Tente novamente mais tarde."}, status_code=429,
                                        headers={"Retry-After": str(retry)})
            tasks = BackgroundTasks()
            if response.background is not None:
                tasks.add_task(response.background)
            tasks.add_task(_cleanup_old_attempts)
            response.background = tasks
        except Exception:
            db.rollback()
        finally:
            db.close()
        return response
