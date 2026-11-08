"""Atomic, database-shared admission control. Never store email/IP in cleartext."""
import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import case, or_
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.user import PasswordResetLimit


def identity_key(scope, value, settings):
    digest = hmac.new(settings.secret_key.encode(), f"password-reset:{scope}:{value}".encode(), hashlib.sha256).hexdigest()
    return f"{scope}:{digest}"


def _reserve(db, key, maximum, now, settings, *, account=False):
    table = PasswordResetLimit.__table__
    dialect = db.get_bind().dialect.name
    insert = {"postgresql": postgres_insert, "sqlite": sqlite_insert}[dialect]
    boundary = now - timedelta(seconds=settings.password_reset_window_seconds)
    expired = table.c.window_started_at <= boundary
    nonce = secrets.token_hex(24) if account else None
    # SMTP has several socket operations; this is a bounded crash-recovery lease,
    # not a claim that socket timeouts impose an absolute delivery deadline.
    timeout = settings.email_timeout_seconds if settings.email_transport == "brevo_api" else settings.smtp_timeout_seconds
    lease_seconds = max(settings.password_reset_cooldown_seconds, 8 * timeout + 60) if account else 0
    values = dict(key=key, window_started_at=now, requests=1,
                  next_allowed_at=now + timedelta(seconds=settings.password_reset_cooldown_seconds if account else 0),
                  lease_until=now + timedelta(seconds=lease_seconds), reservation=nonce)
    statement = insert(table).values(**values).on_conflict_do_update(
        index_elements=[table.c.key],
        set_={"window_started_at": case((expired, now), else_=table.c.window_started_at),
              "requests": case((expired, 1), else_=table.c.requests + 1),
              "next_allowed_at": values["next_allowed_at"], "lease_until": values["lease_until"],
              "reservation": nonce},
        where=(table.c.next_allowed_at <= now) & (table.c.lease_until <= now)
              & or_(expired, table.c.requests < maximum),
    ).returning(table.c.key)
    accepted = db.execute(statement).scalar_one_or_none() is not None
    return accepted, nonce


def reserve_request(db, email, ip, now, settings):
    """Consume IP budget on every valid attempt; reserve account only if allowed."""
    ip_key = identity_key("ip", ip, settings)
    accepted, _ = _reserve(db, ip_key, settings.password_reset_ip_max_requests, now, settings)
    if not accepted:
        db.commit()
        return None
    key = identity_key("email", email, settings)
    accepted, nonce = _reserve(db, key, settings.password_reset_account_max_requests, now, settings, account=True)
    # Commit admission before email delivery. Rollback of a token cannot undo it.
    db.commit()
    return (key, nonce) if accepted else None


def finish_reservation(db, reservation, now):
    key, nonce = reservation
    return db.query(PasswordResetLimit).filter(
        PasswordResetLimit.key == key, PasswordResetLimit.reservation == nonce,
    ).update({PasswordResetLimit.lease_until: now, PasswordResetLimit.reservation: None}, synchronize_session=False) == 1


def prune_expired(db, now, settings):
    cutoff = now - timedelta(seconds=2 * settings.password_reset_window_seconds)
    keys = [row[0] for row in db.query(PasswordResetLimit.key).filter(
        PasswordResetLimit.window_started_at < cutoff,
        PasswordResetLimit.next_allowed_at <= now, PasswordResetLimit.lease_until <= now,
    ).order_by(PasswordResetLimit.window_started_at).limit(100).all()]
    if keys:
        # Recheck predicates after locking: another process may have renewed a key.
        db.query(PasswordResetLimit).filter(
            PasswordResetLimit.key.in_(keys), PasswordResetLimit.window_started_at < cutoff,
            PasswordResetLimit.next_allowed_at <= now, PasswordResetLimit.lease_until <= now,
        ).delete(synchronize_session=False)
