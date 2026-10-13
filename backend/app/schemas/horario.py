from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user import RoleEnum


class JornadaTrabalhoBase(BaseModel):
    barbeiro_id: int
    dia_semana: int  # 0=Domingo, 1=Segunda, ..., 6=Sábado
    hora_inicio: str  # Format: "HH:MM"
    hora_fim: str     # Format: "HH:MM"
    ativo: Optional[bool] = True


class JornadaTrabalhoCreate(JornadaTrabalhoBase):
    pass


class JornadaTrabalhoUpdate(BaseModel):
    dia_semana: Optional[int] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    ativo: Optional[bool] = None


class JornadaTrabalhoResponse(JornadaTrabalhoBase):
    id: int

    class Config:
        orm_mode = True


class BloqueioHorarioBase(BaseModel):
    barbeiro_id: int
    inicio: datetime
    fim: datetime
    motivo: Optional[str] = None
    tipo: str  # e.g., "folga", "feriado", "bloqueio_ad_hoc"
    ativo: Optional[bool] = True


class BloqueioHorarioCreate(BloqueioHorarioBase):
    pass


class BloqueioHorarioUpdate(BaseModel):
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    motivo: Optional[str] = None
    tipo: Optional[str] = None
    ativo: Optional[bool] = None


class BloqueioHorarioResponse(BloqueioHorarioBase):
    id: int

    class Config:
        orm_mode = True