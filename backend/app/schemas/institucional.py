from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.base import ORMModel


class InformacaoInstitucionalBase(ORMModel):
    nome: str
    endereco: str
    telefone: str
    email: Optional[str] = None
    site: Optional[str] = None
    horario_funcionamento: str
    dias_atendimento: str
    endereco_maps: Optional[str] = None


class InformacaoInstitucionalCreate(InformacaoInstitucionalBase):
    pass


class InformacaoInstitucionalUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    site: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    dias_atendimento: Optional[str] = None
    endereco_maps: Optional[str] = None


class InformacaoInstitucionalResponse(InformacaoInstitucionalBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime
