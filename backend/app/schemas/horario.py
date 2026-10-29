import re
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.schemas.base import ORMModel


class JornadaTrabalhoBase(ORMModel):
    barbeiro_id: int
    dia_semana: int  # 0=Domingo, 1=Segunda, ..., 6=Sábado
    hora_inicio: str  # Format: "HH:MM"
    hora_fim: str     # Format: "HH:MM"
    ativo: Optional[bool] = True

    @field_validator("dia_semana")
    @classmethod
    def validate_weekday(cls, value):
        if not 0 <= value <= 6:
            raise ValueError("dia_semana deve estar entre 0 e 6")
        return value

    @field_validator("hora_inicio", "hora_fim")
    @classmethod
    def validate_time_format(cls, value):
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Use o formato HH:MM para os horários")
        return value

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValueError("O fim da jornada deve ser posterior ao início")
        return self


class JornadaTrabalhoCreate(JornadaTrabalhoBase):
    pass


class JornadaTrabalhoUpdate(BaseModel):
    dia_semana: Optional[int] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("dia_semana")
    @classmethod
    def validate_weekday(cls, value):
        if value is not None and not 0 <= value <= 6:
            raise ValueError("dia_semana deve estar entre 0 e 6")
        return value

    @field_validator("hora_inicio", "hora_fim")
    @classmethod
    def validate_time_format(cls, value):
        if value is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
            raise ValueError("Use o formato HH:MM para os horários")
        return value

    @model_validator(mode="after")
    def validate_time_order_when_complete(self):
        if self.hora_inicio is not None and self.hora_fim is not None and self.hora_inicio >= self.hora_fim:
            raise ValueError("O fim da jornada deve ser posterior ao início")
        return self


class JornadaTrabalhoResponse(JornadaTrabalhoBase):
    id: int

class BloqueioHorarioBase(ORMModel):
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
