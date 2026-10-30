"""Central environment configuration and fail-closed validation."""

from dataclasses import dataclass, field
import ipaddress
import math
import os
import re
from typing import Mapping
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


_SECRET_MIN_BYTES = 32
_BASE_SECRET_MARKERS = (
    "replace", "placeholder", "example", "yoursecret", "changeme",
    "defaultsecret", "insecure", "developmentsecret",
)
_PRODUCTION_SECRET_MARKERS = (
    "test", "development", "devsecret", "local", "sample", "demo", "fake",
    "notforproduction", "notfordeployment",
)
_CORS_ORIGIN_ERROR = (
    "CORS_ALLOWED_ORIGINS entries must be valid HTTP(S) origins without wildcards, "
    "credentials, paths, queries, or fragments"
)
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_SUPPORTED_ENVIRONMENTS = {"development", "production", "test"}
_SUPPORTED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}
_SECURE_SSL_MODES = {"require", "verify-ca", "verify-full"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    installation_name: str
    database_url: str = field(repr=False)
    database_backend: str
    secret_key: str = field(repr=False)
    jwt_algorithm: str
    access_token_expire_minutes: int
    terms_version: str
    client_ip_source: str
    allowed_hosts: tuple[str, ...]
    rate_limit_max_attempts: int
    rate_limit_block_minutes: int
    force_https: bool
    cors_allowed_origins: tuple[str, ...]
    scheduling_timezone: str
    smtp_host: str
    smtp_port: int
    smtp_username: str = field(repr=False)
    smtp_password: str = field(repr=False)
    smtp_from: str
    smtp_timeout_seconds: float
    password_reset_url: str = field(repr=False)
    retention_days: int = 365
    metrics_token: str = field(default="", repr=False)


def _get(source: Mapping[str, str], name: str, default: str = "") -> str:
    return source.get(name, default).strip()


def _normalize_cors_hostname(hostname: str) -> str:
    if "*" in hostname:
        raise RuntimeError(_CORS_ORIGIN_ERROR)
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if not hostname or any(character.isspace() for character in hostname):
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        if all(character in "0123456789." for character in hostname):
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        try:
            dns_name = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        labels = dns_name[:-1].split(".") if dns_name.endswith(".") else dns_name.split(".")
        if (
            len(dns_name) > 254
            or any(not label or len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in labels)
        ):
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        return dns_name

    if isinstance(address, ipaddress.IPv6Address):
        if address.scope_id is not None:
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        return f"[{address.compressed.lower()}]"
    return str(address)


def parse_cors_origins(configured: str | None, environment: str) -> tuple[str, ...]:
    environment = environment.strip().lower()
    if configured is None:
        if environment == "production":
            raise RuntimeError("CORS_ALLOWED_ORIGINS must be explicitly configured in production")
        return ("http://127.0.0.1:5500",) if environment == "development" else ()

    origins = []
    seen = set()
    for origin in (value.strip() for value in configured.split(",")):
        if not origin:
            continue
        if any(character.isspace() for character in origin) or "?" in origin or "#" in origin:
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        try:
            parsed = urlsplit(origin)
        except ValueError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        if (
            scheme not in {"http", "https"}
            or not parsed.netloc
            or hostname is None
            or parsed.path not in {"", "/"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise RuntimeError(_CORS_ORIGIN_ERROR)
        if environment == "production" and scheme != "https":
            raise RuntimeError("Production CORS origins must use HTTPS")
        try:
            port = parsed.port
        except ValueError:
            raise RuntimeError(_CORS_ORIGIN_ERROR) from None
        if parsed.netloc.endswith(":") or (port is not None and not 1 <= port <= 65535):
            raise RuntimeError(_CORS_ORIGIN_ERROR)

        normalized_host = _normalize_cors_hostname(hostname)
        default_port = 80 if scheme == "http" else 443
        normalized = f"{scheme}://{normalized_host}"
        if port is not None and port != default_port:
            normalized += f":{port}"
        if normalized not in seen:
            seen.add(normalized)
            origins.append(normalized)

    if environment == "production" and not origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must contain at least one HTTPS origin in production")
    return tuple(origins)


def parse_allowed_hosts(configured: str | None, environment: str) -> tuple[str, ...]:
    """Validate HTTP Host allowlist; production must always be explicit."""
    environment = environment.strip().lower()
    if configured is None or not configured.strip():
        if environment == "production":
            raise RuntimeError("ALLOWED_HOSTS must be explicitly configured in production")
        return ("*",)

    hosts: list[str] = []
    seen: set[str] = set()
    for raw_host in configured.split(","):
        host = raw_host.strip().lower()
        if not host:
            continue
        if host == "*" and environment != "production":
            if host not in seen:
                seen.add(host)
                hosts.append(host)
            continue
        wildcard = host.startswith("*.")
        candidate = host[2:] if wildcard else host
        if "*" in candidate or ":" in candidate or "/" in candidate or "@" in candidate:
            raise RuntimeError("ALLOWED_HOSTS entries must be hostnames or leading subdomain wildcards")
        try:
            normalized = _normalize_cors_hostname(candidate).rstrip(".")
        except RuntimeError:
            raise RuntimeError("ALLOWED_HOSTS contains an invalid hostname") from None
        normalized = f"*.{normalized}" if wildcard else normalized
        if normalized not in seen:
            seen.add(normalized)
            hosts.append(normalized)

    if environment == "production" and not hosts:
        raise RuntimeError("ALLOWED_HOSTS must contain at least one hostname in production")
    return tuple(hosts)


def validate_secret_key(value: str | None, *, production: bool = False) -> str:
    secret = (value or "").strip()
    normalized = re.sub(r"[^a-z0-9]", "", secret.lower())
    repeated = any(
        len(secret) % period == 0 and secret == secret[:period] * (len(secret) // period)
        for period in range(1, min(16, len(secret) // 2 + 1))
    )
    markers = _BASE_SECRET_MARKERS + (_PRODUCTION_SECRET_MARKERS if production else ())
    if (
        len(secret.encode("utf-8")) < _SECRET_MIN_BYTES
        or len(set(secret)) < 8
        or secret.isdigit()
        or repeated
        or any(marker in normalized for marker in markers)
        or normalized in {"secret", "secretkey", "password", "barbeariadevsecretkey"}
    ):
        raise RuntimeError(
            "SECRET_KEY must be explicitly configured with a strong, non-placeholder value "
            "of at least 32 UTF-8 bytes."
        )
    if production and len(set(secret)) < 16:
        raise RuntimeError("SECRET_KEY must use a high-entropy value in production")
    return secret


def get_app_environment(source: Mapping[str, str] | None = None) -> str:
    source = os.environ if source is None else source
    environment = _get(source, "APP_ENV").lower()
    if environment not in _SUPPORTED_ENVIRONMENTS:
        raise RuntimeError("APP_ENV must be explicitly set to development, test, or production")
    return environment


def _validate_database_url(value: str, environment: str) -> tuple[URL, str]:
    try:
        parsed = make_url(value)
    except (ArgumentError, TypeError, ValueError):
        raise RuntimeError("DATABASE_URL is invalid") from None

    backend = parsed.get_backend_name()
    if backend == "sqlite":
        if environment == "production":
            raise RuntimeError("SQLite DATABASE_URL is not allowed in production")
        if parsed.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise RuntimeError("DATABASE_URL uses an unsupported SQLite driver")
        return parsed, backend

    if backend == "postgresql" and parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    if backend != "postgresql" or parsed.drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use the supported postgresql+psycopg driver")
    if environment == "production":
        if not parsed.database or not parsed.host or not parsed.username:
            raise RuntimeError("Production DATABASE_URL must define a database, host, and user")
        sslmode = parsed.query.get("sslmode")
        host = parsed.host.strip("[]").lower()
        try:
            is_local = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_local = False
        if sslmode is not None and sslmode not in _SECURE_SSL_MODES:
            raise RuntimeError("Production DATABASE_URL has an insecure PostgreSQL sslmode")
        if not is_local and sslmode is None:
            parsed = parsed.update_query_dict({"sslmode": "require"})
    return parsed, backend


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise RuntimeError("SCHEDULING_TIMEZONE must be a valid IANA time zone") from None
    return value


def validate_scheduling_timezone(value: str) -> ZoneInfo:
    return ZoneInfo(_validate_timezone(value))


def _validate_smtp_host(host: str) -> str:
    if not host or any(character.isspace() for character in host) or any(char in host for char in "/@\\"):
        raise RuntimeError("SMTP_HOST must be a hostname or IP address without a scheme or port")
    candidate = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        if ":" in candidate:
            raise RuntimeError("SMTP_HOST must be a valid hostname or IP address") from None
        try:
            normalized = candidate.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise RuntimeError("SMTP_HOST must be a valid hostname or IP address") from None
        labels = normalized.split(".")
        if any(not label or len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in labels):
            raise RuntimeError("SMTP_HOST must be a valid hostname or IP address")
    return host


def _validate_sender(value: str) -> str:
    from email.utils import parseaddr

    if "\r" in value or "\n" in value:
        raise RuntimeError("SMTP_FROM must be a valid sender email address")
    _display_name, address = parseaddr(value)
    local_part, separator, domain = address.rpartition("@")
    try:
        normalized_domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError:
        normalized_domain = ""
    domain_labels = normalized_domain.split(".") if normalized_domain else []
    if (
        not separator
        or not local_part
        or len(local_part) > 64
        or re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local_part) is None
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or len(normalized_domain) > 253
        or len(domain_labels) < 2
        or any(not label or len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in domain_labels)
    ):
        raise RuntimeError("SMTP_FROM must be a valid sender email address")
    return value


def _validate_reset_url(value: str, *, production: bool) -> tuple[str, str]:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise RuntimeError("PASSWORD_RESET_URL must be an absolute HTTP(S) URL") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or (port is not None and not 1 <= port <= 65535)
        or any(character.isspace() for character in value)
    ):
        raise RuntimeError("PASSWORD_RESET_URL must be an absolute HTTP(S) URL without credentials")
    if production:
        if parsed.scheme.lower() != "https" or parsed.query or parsed.fragment:
            raise RuntimeError("Production PASSWORD_RESET_URL must use HTTPS without query or fragment")
        if not parsed.path.lower().endswith("reset.html"):
            raise RuntimeError("Production PASSWORD_RESET_URL must point to reset.html")

    origin = f"{parsed.scheme.lower()}://{parsed.netloc}"
    normalized_origin = parse_cors_origins(origin, "development")
    return value, normalized_origin[0]


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    """Read and validate the complete configuration without echoing values."""
    source = os.environ if source is None else source
    environment = get_app_environment(source)
    installation_name = _get(source, "INSTALLATION_NAME", "Barbearia")
    if (
        not installation_name or len(installation_name) > 80
        or any(ord(character) < 32 or ord(character) == 127 for character in installation_name)
    ):
        raise RuntimeError("INSTALLATION_NAME must contain between 1 and 80 printable characters")

    database_url = _get(source, "DATABASE_URL")
    if not database_url:
        if environment == "development":
            database_url = "sqlite:///./barbearia.db"
        else:
            raise RuntimeError("DATABASE_URL must be explicitly configured unless APP_ENV=development")
    _parsed_database_url, database_backend = _validate_database_url(database_url, environment)
    if database_backend == "postgresql":
        database_url = _parsed_database_url.render_as_string(hide_password=False)

    secret_key = validate_secret_key(_get(source, "SECRET_KEY"), production=environment == "production")
    algorithm = _get(source, "ALGORITHM", "HS256").upper()
    if algorithm not in _SUPPORTED_JWT_ALGORITHMS:
        raise RuntimeError("ALGORITHM must be one of HS256, HS384, or HS512")
    try:
        token_minutes = int(_get(source, "ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    except ValueError:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer") from None
    if not 5 <= token_minutes <= 60:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 5 and 60")

    terms_version = _get(source, "TERMS_VERSION", "1.0")
    if not terms_version or len(terms_version) > 100:
        raise RuntimeError("TERMS_VERSION must contain between 1 and 100 characters")
    client_ip_source = _get(source, "CLIENT_IP_SOURCE", "direct").lower()
    if client_ip_source not in {"direct", "cf-connecting-ip"}:
        raise RuntimeError("CLIENT_IP_SOURCE must be 'direct' or 'cf-connecting-ip'")
    allowed_hosts = parse_allowed_hosts(source.get("ALLOWED_HOSTS"), environment)

    try:
        rate_limit_max_attempts = int(_get(source, "RATE_LIMIT_MAX_ATTEMPTS", "5"))
        rate_limit_block_minutes = int(_get(source, "RATE_LIMIT_BLOCK_MINUTES", "15"))
    except ValueError:
        raise RuntimeError("Rate limit settings must be positive integers") from None
    if not 1 <= rate_limit_max_attempts <= 100:
        raise RuntimeError("RATE_LIMIT_MAX_ATTEMPTS must be between 1 and 100")
    if not 1 <= rate_limit_block_minutes <= 1440:
        raise RuntimeError("RATE_LIMIT_BLOCK_MINUTES must be between 1 and 1440")
    try:
        retention_days = int(_get(source, "RETENTION_DAYS", "365"))
    except ValueError:
        raise RuntimeError("RETENTION_DAYS must be a positive integer") from None
    if not 1 <= retention_days <= 36500:
        raise RuntimeError("RETENTION_DAYS must be between 1 and 36500")
    metrics_token = _get(source, "METRICS_TOKEN")
    if metrics_token and (len(metrics_token.encode("utf-8")) < 32 or any(char.isspace() or ord(char) < 32 for char in metrics_token)):
        raise RuntimeError("METRICS_TOKEN must contain at least 32 non-whitespace characters")
    raw_force_https = _get(source, "FORCE_HTTPS", "true" if environment == "production" else "false").lower()
    if raw_force_https not in {"true", "false", "1", "0", "yes", "no"}:
        raise RuntimeError("FORCE_HTTPS must be a boolean")
    force_https = raw_force_https in {"true", "1", "yes"}

    cors_origins = parse_cors_origins(source.get("CORS_ALLOWED_ORIGINS"), environment)
    timezone_value = _get(source, "SCHEDULING_TIMEZONE")
    if not timezone_value:
        if environment == "production":
            raise RuntimeError("SCHEDULING_TIMEZONE must be explicitly configured in production")
        timezone_value = "America/Sao_Paulo"
    scheduling_timezone = _validate_timezone(timezone_value)

    smtp_host = _get(source, "SMTP_HOST")
    smtp_username = _get(source, "SMTP_USERNAME")
    smtp_password = source.get("SMTP_PASSWORD", "")
    smtp_from = _get(source, "SMTP_FROM")
    password_reset_url = _get(source, "PASSWORD_RESET_URL")
    try:
        smtp_port = int(_get(source, "SMTP_PORT", "587"))
        smtp_timeout = float(_get(source, "SMTP_TIMEOUT_SECONDS", "10"))
    except ValueError:
        raise RuntimeError("SMTP_PORT and SMTP_TIMEOUT_SECONDS must be valid numeric values") from None
    if not 1 <= smtp_port <= 65535 or not math.isfinite(smtp_timeout) or not 0 < smtp_timeout <= 120:
        raise RuntimeError("SMTP_PORT or SMTP_TIMEOUT_SECONDS is outside the supported range")

    email_partially_configured = bool(smtp_host or smtp_username or smtp_password or smtp_from)
    email_required = environment == "production"
    if email_required or email_partially_configured:
        if not smtp_host or not smtp_from or not password_reset_url:
            raise RuntimeError(
                "Configure SMTP_HOST, SMTP_FROM, and PASSWORD_RESET_URL together to enable password recovery"
            )
        _validate_smtp_host(smtp_host)
        _validate_sender(smtp_from)
        if bool(smtp_username) != bool(smtp_password):
            raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")
        _reset_url, reset_origin = _validate_reset_url(
            password_reset_url,
            production=email_required,
        )
        if email_required and reset_origin not in cors_origins:
            raise RuntimeError("Production PASSWORD_RESET_URL origin must be listed in CORS_ALLOWED_ORIGINS")
    elif password_reset_url:
        _validate_reset_url(password_reset_url, production=False)

    return Settings(
        app_env=environment,
        installation_name=installation_name,
        database_url=database_url,
        database_backend=database_backend,
        secret_key=secret_key,
        jwt_algorithm=algorithm,
        access_token_expire_minutes=token_minutes,
        terms_version=terms_version,
        client_ip_source=client_ip_source,
        allowed_hosts=allowed_hosts,
        rate_limit_max_attempts=rate_limit_max_attempts,
        rate_limit_block_minutes=rate_limit_block_minutes,
        force_https=force_https,
        cors_allowed_origins=cors_origins,
        scheduling_timezone=scheduling_timezone,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_from=smtp_from,
        smtp_timeout_seconds=smtp_timeout,
        password_reset_url=password_reset_url,
        retention_days=retention_days,
        metrics_token=metrics_token,
    )


def settings() -> Settings:
    return load_settings()
