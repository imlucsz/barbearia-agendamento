
import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class RoleEnum(str, enum.Enum):
    CLIENTE = "cliente"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.CLIENTE)

    appointments = relationship("Appointment", back_populates="user")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    duracao_minutos = Column(Integer, default=30)

    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service_id = Column(Integer, ForeignKey("services.id"))
    data_hora = Column(DateTime, nullable=False)
    status = Column(String, default="agendado")

    user = relationship("User", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")