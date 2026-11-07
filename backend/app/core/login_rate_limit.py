"""Distributed admission reservations exclusively for POST /auth/login."""
from dataclasses import dataclass, fields
from datetime import timedelta
from enum import Enum
import hashlib
import hmac
import math
import os
from threading import Event

from fastapi.responses import JSONResponse
from sqlalchemy import case, or_, text
from starlette.background import BackgroundTasks
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.clock import utc_now_naive
from app.core.email_identity import normalize_email
from app.core.request_context import get_client_ip
from app.database import SessionLocal
from app.models.user import LoginAttempt
from app.schemas.user import UserLogin
from pydantic import ValidationError

PATH = "/auth/login"


class Outcome(str, Enum):
    PENDING = "pendente"
    SUCCESS = "sucesso"
    REJECTED = "credencial_rejeitada"
    NEUTRAL = "neutro"


class Reason(str, Enum):
    AUTHENTICATED = "autenticada"
    REJECTED = "credencial_rejeitada"
    UNAVAILABLE = "indisponivel"
    AFTER_REJECTION_ERROR = "erro_apos_rejeicao"
    INTERRUPTED_AFTER_REJECTION = "interrompida_apos_rejeicao"
    CANCELLED = "cancelada"
    EXPIRED = "expirada"
    INVALIDATED = "invalidada"
    INVALID_PAYLOAD = "payload_invalido"
    ACCOUNT_UNAVAILABLE = "conta_indisponivel"
    CREDENTIAL_CHANGED = "credencial_alterada"


def record_login_outcome(request, outcome, reason):
    # One assignment also avoids observing a result paired with an older reason.
    request.state.login_outcome = (Outcome(outcome), Reason(reason))


@dataclass(frozen=True)
class Policy:
    account_failures: int = 5
    account_window_seconds: int = 60
    ip_failures: int = 30
    ip_window_seconds: int = 300
    ip_requests: int = 60
    request_window_seconds: int = 60
    account_concurrency: int = 2
    ip_concurrency: int = 4
    lease_seconds: int = 120

    @classmethod
    def from_env(cls):
        values = {}
        for field in fields(cls):
            name = "LOGIN_RATE_" + field.name.upper()
            try:
                value = int(os.environ.get(name, field.default))
            except ValueError:
                raise RuntimeError(f"{name} must be a positive integer") from None
            maximum = 86400 if field.name.endswith("seconds") else 10000
            if not 1 <= value <= maximum:
                raise RuntimeError(f"{name} must be between 1 and {maximum}")
            values[field.name] = value
        return cls(**values)


POLICY = Policy.from_env()


class Limited(Exception):
    def __init__(self, retry_after):
        self.retry_after = max(1, math.ceil(retry_after))


def account_key(email):
    # Keyed digest resists offline guessing of the stored email identities.
    return hmac.new(settings().secret_key.encode(), ("login-account:" + normalize_email(email)).encode(), hashlib.sha256).hexdigest()


def _lock(db, ip, key):
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    else:
        # A snapshot taken before a waited lock must not hide its committed row.
        db.connection(execution_options={"isolation_level": "READ COMMITTED"})
        # Fixed order avoids deadlocks; locks end at commit, before password work.
        scopes = ["login-ip:" + ip] + (["login-account:" + key] if key else [])
        identifiers = sorted({int.from_bytes(hashlib.sha256(scope.encode()).digest()[:8], "big", signed=True) for scope in scopes})
        for identifier in identifiers:
            db.execute(text("SELECT pg_advisory_xact_lock(:identifier)"), {"identifier": identifier})


def reserve(ip, email):
    key = account_key(email) if email is not None else None
    db = SessionLocal()
    try:
        _lock(db, ip, key)
        now = utc_now_naive()
        policy = POLICY
        horizon = now - timedelta(seconds=max(policy.account_window_seconds, policy.ip_window_seconds, policy.request_window_seconds))
        scope = LoginAttempt.ip == ip
        if key:
            scope = or_(scope, LoginAttempt.account_key == key)
        rows = db.query(LoginAttempt).filter(
            LoginAttempt.rota == PATH, scope,
            or_(LoginAttempt.ocorrido_em > horizon,
                (LoginAttempt.em_andamento.is_(True) & (LoginAttempt.expira_em > now))),
        ).all()
        waits = []

        def check(expirations, maximum):
            if len(expirations) >= maximum:
                # Handles lower limits after a configuration change, too.
                release = sorted(expirations)[len(expirations) - maximum]
                waits.append((release - now).total_seconds())

        def window(row, seconds):
            return row.ocorrido_em + timedelta(seconds=seconds)

        def consumes_failure_budget(row):
            if row.resultado is None:
                # All old binary history keeps its original window semantics.
                return not row.sucesso
            if row.resultado == Outcome.REJECTED.value:
                return True
            if row.resultado == Outcome.PENDING.value and row.em_andamento:
                # A lease borrows budget while alive; expiry is not a verdict.
                return bool(row.expira_em and row.expira_em > now)
            return False

        ip_rows = [row for row in rows if row.ip == ip]
        account_rows = [row for row in rows if key and row.account_key == key]
        for scoped, maximum, seconds, failures_only in (
            (account_rows, policy.account_failures, policy.account_window_seconds, True),
            (ip_rows, policy.ip_failures, policy.ip_window_seconds, True),
            (ip_rows, policy.ip_requests, policy.request_window_seconds, False),
        ):
            check([window(row, seconds) for row in scoped if window(row, seconds) > now and (not failures_only or consumes_failure_budget(row))], maximum)
        for scoped, maximum in ((account_rows, policy.account_concurrency), (ip_rows, policy.ip_concurrency)):
            check([row.expira_em for row in scoped if row.em_andamento and row.expira_em and row.expira_em > now], maximum)
        if waits:
            raise Limited(max(waits))
        reservation = LoginAttempt(ip=ip, rota=PATH, account_key=key, sucesso=False,
                                   resultado=Outcome.PENDING.value,
                                   em_andamento=True, ocorrido_em=now,
                                   expira_em=now + timedelta(seconds=policy.lease_seconds))
        db.add(reservation)
        db.flush()
        identifier = reservation.id
        db.commit()
        return identifier
    finally:
        db.close()


def finish(identifier, outcome, reason):
    outcome, reason = Outcome(outcome), Reason(reason)
    if outcome is Outcome.PENDING:
        raise ValueError("A final outcome is required")
    db = SessionLocal()
    try:
        expired = LoginAttempt.expira_em <= utc_now_naive()
        invalidated = LoginAttempt.em_andamento.is_(False)
        # A known rejection is evidence, not a provisional reservation. A later
        # timeout/cancellation cannot erase it; only an earlier terminal result wins.
        if outcome is Outcome.REJECTED:
            result_value, reason_value, success_value = outcome.value, reason.value, False
        else:
            result_value = case((expired, Outcome.NEUTRAL.value),
                                (invalidated, Outcome.NEUTRAL.value), else_=outcome.value)
            reason_value = case((expired, Reason.EXPIRED.value),
                                (invalidated, Reason.INVALIDATED.value), else_=reason.value)
            success_value = case((expired, False), (invalidated, False),
                                 else_=outcome is Outcome.SUCCESS)
        changed = db.query(LoginAttempt).filter(
            LoginAttempt.id == identifier, LoginAttempt.rota == PATH,
            LoginAttempt.resultado == Outcome.PENDING.value,
        ).update({
            LoginAttempt.resultado: result_value,
            LoginAttempt.motivo_finalizacao: reason_value,
            LoginAttempt.sucesso: success_value,
            LoginAttempt.em_andamento: False,
        }, synchronize_session=False)
        db.commit()
        return changed == 1
    finally:
        db.close()


def claim_login_reservation(db, request):
    """Consume live admission in the same transaction as credential CAS/session."""
    identifier = getattr(request.state, "login_reservation_id", None)
    cancelled = getattr(request.state, "login_cancelled", None)
    if identifier is None or cancelled is None or cancelled.is_set():
        record_login_outcome(request, Outcome.NEUTRAL,
                             Reason.CANCELLED if cancelled is not None and cancelled.is_set() else Reason.INVALIDATED)
        return False
    claimed = db.query(LoginAttempt).filter(
        LoginAttempt.id == identifier, LoginAttempt.rota == PATH,
        LoginAttempt.resultado == Outcome.PENDING.value,
        LoginAttempt.em_andamento.is_(True), LoginAttempt.expira_em > utc_now_naive(),
    ).update({LoginAttempt.em_andamento: False, LoginAttempt.sucesso: True,
              LoginAttempt.resultado: Outcome.SUCCESS.value,
              LoginAttempt.motivo_finalizacao: Reason.AUTHENTICATED.value}, synchronize_session=False)
    if claimed != 1 or cancelled.is_set():
        record_login_outcome(request, Outcome.NEUTRAL,
                             Reason.CANCELLED if cancelled.is_set() else Reason.INVALIDATED)
        return False
    return True


def unavailable():
    return JSONResponse({"detail": "Não foi possível entrar agora. Tente novamente em instantes."},
                        status_code=503, headers={"Retry-After": "1"})


async def limit_login(request, call_next, cleanup):
    ip = get_client_ip(request)
    email = None
    initial_reason = Reason.UNAVAILABLE
    try:
        payload = await request.json()
        email = UserLogin.model_validate(payload).email
    except (ValidationError, ValueError, TypeError):
        # Malformed credentials consume request frequency, not rejected-password budget.
        initial_reason = Reason.INVALID_PAYLOAD
    try:
        identifier = await run_in_threadpool(reserve, ip, email)
    except Limited as blocked:
        return JSONResponse({"detail": "Muitas tentativas. Tente novamente mais tarde."},
                            status_code=429, headers={"Retry-After": str(blocked.retry_after)})
    except Exception:
        return unavailable()
    request.state.login_reservation_id = identifier
    request.state.login_cancelled = Event()
    record_login_outcome(request, Outcome.NEUTRAL, initial_reason)
    try:
        response = await call_next(request)
    except BaseException as original:
        request.state.login_cancelled.set()
        outcome, _reason = request.state.login_outcome
        if not isinstance(original, Exception):
            if outcome is Outcome.REJECTED:
                reason = Reason.INTERRUPTED_AFTER_REJECTION
            else:
                outcome, reason = Outcome.NEUTRAL, Reason.CANCELLED
        else:
            reason = Reason.AFTER_REJECTION_ERROR if outcome is Outcome.REJECTED else Reason.UNAVAILABLE
        try:
            await run_in_threadpool(finish, identifier, outcome, reason)
        except Exception:
            if isinstance(original, Exception):
                return unavailable()
        if isinstance(original, Exception):
            return unavailable()
        raise
    try:
        await run_in_threadpool(finish, identifier, *request.state.login_outcome)
    except Exception:
        return unavailable()
    tasks = BackgroundTasks()
    if response.background is not None:
        tasks.add_task(response.background)
    tasks.add_task(cleanup)
    response.background = tasks
    return response
