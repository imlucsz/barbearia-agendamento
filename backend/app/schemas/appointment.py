from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.models.user import AppointmentStatusEnum
from app.schemas.base import ORMModel, SchemaModel


class AppointmentBase(ORMModel):
    service_id: StrictInt = Field(gt=0)
    barbeiro_id: StrictInt = Field(gt=0)
    data_hora: datetime


class AppointmentCreate(AppointmentBase):
    pass


class AdminAppointmentCreate(AppointmentBase):
    user_id: Optional[StrictInt] = Field(default=None, gt=0)
    nome_cliente: Optional[StrictStr] = Field(default=None, min_length=1, max_length=120)

    @field_validator("nome_cliente")
    @classmethod
    def clean_customer_name(cls, value):
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def validate_customer_identity(self):
        if (self.user_id is None) == (self.nome_cliente is None):
            raise ValueError("Informe um cliente cadastrado ou o nome de um cliente avulso")
        return self


class AppointmentUpdate(SchemaModel):
    status: Optional[AppointmentStatusEnum] = None
    data_hora: Optional[datetime] = None
    valor_cobrado: Optional[float] = Field(default=None, ge=0, le=100000, strict=True)


class AppointmentResponse(ORMModel):
    id: StrictInt = Field(gt=0)
    user_id: Optional[StrictInt] = Field(default=None, gt=0)
    nome_cliente: Optional[StrictStr] = Field(default=None, max_length=120)
    service_id: StrictInt = Field(gt=0)
    barbeiro_id: StrictInt = Field(gt=0)
    data_hora: datetime
    status: AppointmentStatusEnum
    # RN-05: Snapshot of service price and duration at time of booking
    preco: float = Field(gt=0, le=100000, strict=True)
    duracao_minutos: StrictInt = Field(ge=1, le=1440)
    valor_cobrado: Optional[float] = Field(default=None, ge=0, le=100000, strict=True)

class AvaliacaoBase(ORMModel):
    nota: StrictInt = Field(..., ge=1, le=5)
    comentario: Optional[StrictStr] = Field(default=None, max_length=2000)
    oculta: Optional[StrictBool] = None


class AvaliacaoCreate(AvaliacaoBase):
    pass


class AvaliacaoResponse(AvaliacaoBase):
    id: StrictInt = Field(gt=0)
    appointment_id: Optional[StrictInt] = Field(default=None, gt=0)
    criada_em: datetime
