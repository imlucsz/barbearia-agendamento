from datetime import timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.clock import utc_now
from app.config import settings as load_app_settings

_settings = load_app_settings()
SECRET_KEY = _settings.secret_key
ALGORITHM = _settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.access_token_expire_minutes

password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password_and_update(plain_password, hashed_password)[0]


def verify_password_and_update(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """Verify current Argon2 or legacy bcrypt hashes and upgrade legacy hashes."""
    try:
        return password_hash.verify_and_update(plain_password, hashed_password)
    except (UnknownHashError, ValueError, TypeError):
        return False, None

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        options={"require": ["exp"]},
        )
        return payload
    except InvalidTokenError as exc:
        raise ValueError("Token inválido ou expirado") from exc
