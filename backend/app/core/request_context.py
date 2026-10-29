"""Validated client request context shared by security and audit features."""

import ipaddress
import os

from fastapi import HTTPException, Request, status


def _trusted_proxy_count() -> int:
    raw_count = os.environ.get("TRUSTED_PROXY_COUNT", "0").strip()
    try:
        count = int(raw_count)
    except ValueError:
        raise RuntimeError("TRUSTED_PROXY_COUNT must be between 0 and 32") from None
    if not 0 <= count <= 32:
        raise RuntimeError("TRUSTED_PROXY_COUNT must be between 0 and 32")
    return count


def _parse_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço IP de origem inválido",
        ) from None


def get_client_ip(request: Request) -> str:
    """Return the client IP, honoring X-Forwarded-For only for configured proxies."""
    trusted_proxy_count = _trusted_proxy_count()
    forwarded_for = request.headers.get("x-forwarded-for")
    if trusted_proxy_count and forwarded_for:
        items = forwarded_for.split(",")
        if not items or len(items) > 32:
            raise HTTPException(status_code=400, detail="Cabeçalho X-Forwarded-For inválido")
        forwarded = [_parse_ip(item) for item in items]
        client_index = max(0, len(forwarded) - trusted_proxy_count)
        return forwarded[client_index]

    if request.client is None:
        raise HTTPException(status_code=400, detail="Endereço IP de origem indisponível")
    return _parse_ip(request.client.host)
