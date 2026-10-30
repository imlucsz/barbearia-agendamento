from pydantic import Field, StrictInt, StrictStr, field_validator
from typing import Optional
from app.schemas.base import ORMModel, SchemaModel


class ServiceBase(ORMModel):
    nome: StrictStr = Field(min_length=1, max_length=120)
    descricao: Optional[StrictStr] = Field(default=None, max_length=500)
    preco: float = Field(gt=0, le=100000, strict=True)
    duracao_minutos: int = Field(ge=1, le=1440, strict=True)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(SchemaModel):
    nome: Optional[StrictStr] = Field(default=None, min_length=1, max_length=120)
    descricao: Optional[StrictStr] = Field(default=None, max_length=500)
    preco: Optional[float] = Field(default=None, gt=0, le=100000, strict=True)
    duracao_minutos: Optional[int] = Field(default=None, ge=1, le=1440, strict=True)

    @field_validator("nome", "preco", "duracao_minutos", mode="before")
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value


class ServiceResponse(ServiceBase):
    id: StrictInt = Field(gt=0)
