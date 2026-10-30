import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from app.schemas.base import ORMModel, SchemaModel


class JornadaTrabalhoBase(ORMModel):
    barbeiro_id: StrictInt = Field(gt=0)
    dia_semana: StrictInt = Field(ge=0, le=6)
    hora_inicio: StrictStr = Field(min_length=5, max_length=5)
    hora_fim: StrictStr = Field(min_length=5, max_length=5)
    ativo: Optional[StrictBool] = True

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


class JornadaTrabalhoUpdate(SchemaModel):
    dia_semana: Optional[StrictInt] = Field(default=None, ge=0, le=6)
    hora_inicio: Optional[StrictStr] = Field(default=None, min_length=5, max_length=5)
    hora_fim: Optional[StrictStr] = Field(default=None, min_length=5, max_length=5)
    ativo: Optional[StrictBool] = None

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
    barbeiro_id: StrictInt = Field(gt=0)
    inicio: datetime
    fim: datetime
    motivo: Optional[StrictStr] = Field(default=None, max_length=300)
    tipo: Literal["folga", "feriado", "bloqueio_ad_hoc"]
    ativo: Optional[StrictBool] = True


class BloqueioHorarioCreate(BloqueioHorarioBase):
    pass


class BloqueioHorarioUpdate(SchemaModel):
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    motivo: Optional[StrictStr] = Field(default=None, max_length=300)
    tipo: Optional[Literal["folga", "feriado", "bloqueio_ad_hoc"]] = None
    ativo: Optional[StrictBool] = None


class BloqueioHorarioResponse(BloqueioHorarioBase):
    id: int
