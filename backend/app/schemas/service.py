from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.schemas.base import ORMModel


class ServiceBase(ORMModel):
    nome: str
    preco: float
    duracao_minutos: int = Field(ge=1)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    duracao_minutos: Optional[int] = Field(default=None, ge=1)

    @field_validator("duracao_minutos", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value


class ServiceResponse(ServiceBase):
    id: int
