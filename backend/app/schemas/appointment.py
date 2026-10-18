from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.models.user import AppointmentStatusEnum
from app.schemas.base import ORMModel


class AppointmentBase(ORMModel):
    service_id: int
    barbeiro_id: int
    data_hora: datetime


class AppointmentCreate(AppointmentBase):
    pass


class AdminAppointmentCreate(AppointmentBase):
    user_id: Optional[int] = None
    nome_cliente: Optional[str] = Field(default=None, min_length=1, max_length=120)

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


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatusEnum] = None
    data_hora: Optional[datetime] = None
    valor_cobrado: Optional[float] = Field(default=None, ge=0)


class AppointmentResponse(ORMModel):
    id: int
    user_id: Optional[int] = None
    nome_cliente: Optional[str] = None
    service_id: int
    barbeiro_id: int
    data_hora: datetime
    status: AppointmentStatusEnum
    # RN-05: Snapshot of service price and duration at time of booking
    preco: float
    duracao_minutos: int
    valor_cobrado: Optional[float] = None

class AvaliacaoBase(ORMModel):
    nota: int = Field(..., ge=1, le=5)  # Assuming 1-5 scale
    comentario: Optional[str] = None
    oculta: Optional[bool] = None


class AvaliacaoCreate(AvaliacaoBase):
    pass


class AvaliacaoResponse(AvaliacaoBase):
    id: int
    appointment_id: int
    criada_em: datetime
