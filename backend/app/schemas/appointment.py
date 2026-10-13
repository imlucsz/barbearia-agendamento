from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.user import AppointmentStatusEnum


class AppointmentBase(BaseModel):
    service_id: int
    data_hora: datetime


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatusEnum] = None
    data_hora: Optional[datetime] = None


class AppointmentResponse(BaseModel):
    id: int
    user_id: int
    service_id: int
    data_hora: datetime
    status: AppointmentStatusEnum
    # RN-05: Snapshot of service price and duration at time of booking
    preco: float
    duracao_minutos: int

    class Config:
        orm_mode = True


class AvaliacaoBase(BaseModel):
    nota: int = Field(..., ge=1, le=5)  # Assuming 1-5 scale
    comentario: Optional[str] = None
    oculta: Optional[bool] = None


class AvaliacaoCreate(AvaliacaoBase):
    pass


class AvaliacaoResponse(AvaliacaoBase):
    id: int
    appointment_id: int
    criada_em: datetime

    class Config:
        orm_mode = True