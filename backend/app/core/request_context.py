"""Validated client request context shared by security and audit features."""

import ipaddress
import os

from fastapi import HTTPException, Request, status


def _parse_ip(value: str) -> str:
    if not value or value != value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço IP de origem inválido",
        )
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço IP de origem inválido",
        ) from None


IPV6_RATE_LIMIT_PREFIX = 64


def rate_limit_key(ip: str) -> str:
    """Group addresses one client controls: IPv4 /32, IPv6 /64."""
    address = ipaddress.ip_address(ip)
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if address.version == 4:
        return str(address)
    return str(ipaddress.ip_network(f"{address}/{IPV6_RATE_LIMIT_PREFIX}", strict=False))


def get_client_ip(request: Request) -> str:
    """Use the socket peer by default or one explicitly trusted edge header."""
    source = os.environ.get("CLIENT_IP_SOURCE", "direct").strip().lower()
    if source not in {"direct", "cf-connecting-ip"}:
        raise RuntimeError("CLIENT_IP_SOURCE must be 'direct' or 'cf-connecting-ip'")

    if source == "cf-connecting-ip":
        forwarded_values = request.headers.getlist("cf-connecting-ip")
        if len(forwarded_values) != 1 or not forwarded_values[0]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IP de origem encaminhado indisponível",
            )
        return _parse_ip(forwarded_values[0])

    if request.client is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço IP de origem indisponível",
        )
    return _parse_ip(request.client.host)
