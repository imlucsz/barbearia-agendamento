from pydantic import BaseModel
from typing import Optional
from app.schemas.base import ORMModel


class BarbearioServicoBase(ORMModel):
    barbeiro_id: int
    service_id: int


class BarbearioServicoCreate(BarbearioServicoBase):
    pass


class BarbearioServicoResponse(BarbearioServicoBase):
    id: int

class BarbearioServicoWithBarbeiroResponse(ORMModel):
    id: int
    barbeiro_id: int
    service_id: int
    barbeiro_nome: str
