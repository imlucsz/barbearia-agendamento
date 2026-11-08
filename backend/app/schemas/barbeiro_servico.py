from pydantic import Field, StrictInt
from app.schemas.base import ORMModel


class BarbearioServicoBase(ORMModel):
    barbeiro_id: StrictInt = Field(gt=0)
    service_id: StrictInt = Field(gt=0)


class BarbearioServicoCreate(BarbearioServicoBase):
    pass


class BarbearioServicoResponse(BarbearioServicoBase):
    id: int

class BarbearioServicoWithBarbeiroResponse(ORMModel):
    id: int
    barbeiro_id: int
    service_id: int
    barbeiro_nome: str
