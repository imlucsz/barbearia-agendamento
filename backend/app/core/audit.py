"""Best-effort audit persistence and JSON security event logging."""
import json
import logging
import re

from app.core.clock import utc_now_naive
from app.core.request_context import get_client_ip
from app.models.user import AuditLog

logger = logging.getLogger("security.audit")
_SECRET_KEY = re.compile(r"password|senha|token|hash|secret|credential|authorization|cookie|body|corpo", re.I)


def _safe_details(details):
    if not isinstance(details, dict):
        return {}
    safe = {}
    for key, value in details.items():
        key = str(key)[:80]
        if _SECRET_KEY.search(key):
            continue
        if value is None or isinstance(value, (bool, int, float)):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value[:500]
        elif isinstance(value, (list, tuple)):
            safe[key] = [str(item)[:200] for item in value[:20] if not isinstance(item, dict)]
    return safe


def record(db, request, *, actor=None, actor_role=None, acao, entidade, entidade_id=None, resultado="sucesso", detalhes=None):
    """Record an allowlisted metadata event without disrupting the operation."""
    user_id = getattr(actor, "id", None)
    role = actor_role or getattr(getattr(actor, "role", None), "value", getattr(actor, "role", None))
    try:
        ip = get_client_ip(request) if request is not None else None
    except Exception:
        ip = None
    safe = _safe_details(detalhes or {})
    try:
        # Isolate flush errors from the transaction containing the business operation.
        with db.begin_nested():
            db.add(AuditLog(
                usuario_id=user_id, ator_role=str(role)[:32] if role else None,
                acao=str(acao)[:100], entidade=str(entidade)[:100],
                entidade_id=str(entidade_id)[:100] if entidade_id is not None else None,
                ip=ip, resultado=str(resultado)[:32], detalhes=safe, ocorrido_em=utc_now_naive(),
            ))
            db.flush()
    except Exception:
        logger.warning(json.dumps({
            "event": "audit_persist_failed",
            "request_id": getattr(getattr(request, "state", None), "request_id", None),
        }, separators=(",", ":")))
    event = {
        "event": "security_audit", "request_id": getattr(getattr(request, "state", None), "request_id", None),
        "action": str(acao)[:100], "entity": str(entidade)[:100],
        "result": str(resultado)[:32], "actor_role": str(role)[:32] if role else None,
    }
    logger.info(json.dumps(event, separators=(",", ":"), ensure_ascii=True))
