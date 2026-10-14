from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.schemas.base import ORMModel


class UserBase(ORMModel):
    email: EmailStr
    nome: str


class UserCreate(UserBase):
    senha: str = Field(..., min_length=6)
    consentimento_lgpd: bool


class UserLogin(BaseModel):
    email: EmailStr
    senha: str


class UserResponse(UserBase):
    id: int
    role: str
    bloqueado: bool = False

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    # Note: Password changes should use a separate endpoint for security
    bloqueado: Optional[bool] = None


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=6)


class Token(ORMModel):
    access_token: str
    token_type: str

class UserTokenResponse(ORMModel):
    user: UserResponse
    access_token: str
    token_type: str
