from app.core.email_identity import email_key, normalize_email
from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import RoleEnum, User


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não informado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem usuário válido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(email_key(User.email) == normalize_email(email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta inativa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.bloqueado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta bloqueada",
        )

    return user


def require_roles(*roles: RoleEnum, detail: str = "Acesso negado") -> Callable:
    """Build a reusable FastAPI dependency that requires one of the given roles."""
    allowed = frozenset(roles)

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        return current_user

    role_dependency.__name__ = "require_roles_" + "_".join(role.value for role in roles)
    return role_dependency


def ensure_resource_owner(
    resource: object,
    current_user: User,
    *,
    owner_fields: Iterable[str],
    allowed_roles: Iterable[RoleEnum] = (RoleEnum.ADMIN,),
    required_owner_role: RoleEnum | None = None,
    detail: str = "Acesso negado",
) -> None:
    """Raise the established 403 when a loaded resource is outside the user's scope."""
    if current_user.role in frozenset(allowed_roles):
        return
    owns_resource = any(getattr(resource, field, None) == current_user.id for field in owner_fields)
    if owns_resource and (required_owner_role is None or current_user.role == required_owner_role):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_owner_id(
    owner_id: int,
    current_user: User,
    *,
    allowed_roles: Iterable[RoleEnum] = (RoleEnum.ADMIN,),
    detail: str = "Acesso negado",
) -> None:
    if current_user.role not in frozenset(allowed_roles) and current_user.id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
