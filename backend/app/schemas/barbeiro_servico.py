from pydantic import BaseModel
from typing import Optional
from app.models.user import RoleEnum


class BarbearioServicoBase(BaseModel):
    barbeiro_id: int
    service_id: int


class BarbearioServicoCreate(BarbearioServicoBase):
    pass


class BarbearioServicoResponse(BarbearioServicoBase):
    id: int

    class Config:
        orm_mode = True


class BarbearioServicoWithBarbeiroResponse(BaseModel):
    id: int
    barbeiro_id: int
    service_id: int
    barbeiro_nome: str

    class Config:
        orm_mode = True