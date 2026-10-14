from pydantic import BaseModel
from typing import Optional
from app.schemas.base import ORMModel


class ServiceBase(ORMModel):
    nome: str
    preco: float
    duracao_minutos: int


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    nome: Optional[str] = None
    preco: Optional[float] = None
    duracao_minutos: Optional[int] = None


class ServiceResponse(ServiceBase):
    id: int
