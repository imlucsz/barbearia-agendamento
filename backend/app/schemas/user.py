from pydantic import EmailStr, Field, StrictBool, StrictStr, field_validator
from typing import Literal, Optional
from datetime import datetime
from app.schemas.base import ORMModel, SchemaModel


class UserBase(ORMModel):
    email: EmailStr = Field(max_length=254)
    nome: StrictStr = Field(min_length=1, max_length=120)


class UserCreate(UserBase):
    senha: StrictStr = Field(..., min_length=6, max_length=128)
    consentimento_lgpd: StrictBool


class UserLogin(SchemaModel):
    email: EmailStr = Field(max_length=254)
    senha: StrictStr = Field(min_length=1, max_length=128)


class PasswordConfirmation(SchemaModel):
    senha_atual: StrictStr = Field(min_length=1, max_length=128)


class UserResponse(UserBase):
    id: int = Field(gt=0)
    role: Literal["cliente", "barbeiro", "admin"]
    bloqueado: bool = False

class UserUpdate(SchemaModel):
    nome: Optional[StrictStr] = Field(default=None, min_length=1, max_length=120)
    email: Optional[EmailStr] = Field(default=None, max_length=254)
    # Note: Password changes should use a separate endpoint for security
    bloqueado: Optional[bool] = None

    @field_validator("nome", "email", mode="before")
    @classmethod
    def reject_null_for_nonnullable_fields(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value

    @field_validator("bloqueado", mode="before")
    @classmethod
    def validate_block_flag(cls, value):
        if value is not None and not isinstance(value, bool):
            raise ValueError("bloqueado deve ser booleano")
        return value


class EsqueciSenhaRequest(SchemaModel):
    email: EmailStr = Field(max_length=254)


class RedefinirSenhaRequest(SchemaModel):
    token: StrictStr = Field(min_length=1, max_length=128)
    nova_senha: StrictStr = Field(min_length=6, max_length=128)


class Token(ORMModel):
    access_token: StrictStr = Field(min_length=1, max_length=4096)
    token_type: StrictStr = Field(min_length=1, max_length=32)

class UserTokenResponse(ORMModel):
    user: UserResponse
    access_token: StrictStr = Field(min_length=1, max_length=4096)
    token_type: StrictStr = Field(min_length=1, max_length=32)
    refresh_token: StrictStr = Field(min_length=1, max_length=256)
