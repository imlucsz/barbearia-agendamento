import os
import re
from datetime import timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.clock import utc_now

_MIN_SECRET_KEY_BYTES = 32
_INSECURE_SECRET_MARKERS = (
    "replace",
    "placeholder",
    "example",
    "yoursecret",
    "changeme",
    "defaultsecret",
    "insecure",
    "developmentsecret",
)


def _load_secret_key(value: str | None) -> str:
    secret_key = (value or "").strip()
    normalized = re.sub(r"[^a-z0-9]", "", secret_key.lower())
    has_short_repeating_pattern = any(
        len(secret_key) % period == 0
        and secret_key == secret_key[:period] * (len(secret_key) // period)
        for period in range(1, min(16, len(secret_key) // 2 + 1))
    )

    if (
        len(secret_key.encode("utf-8")) < _MIN_SECRET_KEY_BYTES
        or len(set(secret_key)) < 8
        or secret_key.isdigit()
        or has_short_repeating_pattern
        or any(marker in normalized for marker in _INSECURE_SECRET_MARKERS)
        or normalized in {"secret", "secretkey", "password", "barbeariadevsecretkey"}
    ):
        raise RuntimeError(
            "SECRET_KEY must be explicitly configured with a strong, non-placeholder value "
            "of at least 32 UTF-8 bytes."
        )

    return secret_key


SECRET_KEY = _load_secret_key(os.getenv("SECRET_KEY"))
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise ValueError("Token inválido ou expirado") from exc
