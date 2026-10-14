import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class RoleEnum(str, enum.Enum):
    CLIENTE = "cliente"
    BARBEIRO = "barbeiro"
    ADMIN = "admin"


class AppointmentStatusEnum(str, enum.Enum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"
    FALTA = "falta"
    AVALIADO = "avaliado"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.CLIENTE)
    bloqueado = Column(Boolean, default=False)  # RF19: Para bloquear clientes
    ativo = Column(Boolean, default=True)  # RNF-04: Para exclusão lógica de conta

    # Relacionamentos
    appointments = relationship("User", back_populates="user")  # CLIENTE relation
    barbeiro_appointments = relationship("Appointment", foreign_keys="Appointment.barbeiro_id")


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
    barbeiro_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    data_hora = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.PENDENTE)
    # RN-05: Snapshot of service price and duration at time of booking
    preco = Column(Float, nullable=False)
    duracao_minutos = Column(Integer, nullable=False)
    # RN-02: Track number of reschedules (limit Y=2)
    reschedule_count = Column(Integer, default=0)

    # Relacionamentos
    user = relationship("User", foreign_keys=[user_id])
    service = relationship("Service", foreign_keys=[service_id])
    barbeiro = relationship("User", foreign_keys=[barbeiro_id])

    # Note: The unique constraint below is a simplification. Real conflict detection
    # happens in the query for available slots (considering duration, working hours, blocks).
    __table_args__ = (UniqueConstraint('service_id', 'data_hora', name='_service_date_uc'),)


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True)
    nota = Column(Integer, nullable=False)  # Assuming 1-5 scale
    comentario = Column(String, nullable=True)
    criada_em = Column(DateTime, default=datetime.utcnow)
    oculta = Column(Boolean, default=False)  # RF22: Para moderação de avaliações

    appointment = relationship("Appointment")


class InformacaoInstitucional(Base):
    __tablename__ = "informacoes_institucionais"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    endereco = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    site = Column(String, nullable=True)
    horario_funcionamento = Column(String, nullable=False)  # e.g., "08:00-18:00"
    dias_atendimento = Column(String, nullable=False)  # e.g., "Segunda a Sexta"
    endereco_maps = Column(String, nullable=True)  # URL or embed code for map
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JornadaTrabalho(Base):
    __tablename__ = "jornadas_trabalho"

    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 0=Domingo, 1=Segunda, ..., 6=Sábado
    hora_inicio = Column(String, nullable=False)  # Format: "HH:MM"
    hora_fim = Column(String, nullable=False)     # Format: "HH:MM"
    ativo = Column(Boolean, default=True)

    barbeiro = relationship("User", foreign_keys=[barbeiro_id])


class BloqueioHorario(Base):
    __tablename__ = "bloqueios_horario"

    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inicio = Column(DateTime, nullable=False)
    fim = Column(DateTime, nullable=False)
    motivo = Column(String, nullable=True)  # e.g., "Folga", "Feriado", "Consulta médica"
    tipo = Column(String, nullable=False)   # e.g., "folga", "feriado", "bloqueio_ad_hoc"
    ativo = Column(Boolean, default=True)

    barbeiro = relationship("User", foreign_keys=[barbeiro_id])


class BarbearioServico(Base):
    __tablename__ = "barbeiros_servicos"

    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)

    barbeiro = relationship("User", foreign_keys=[barbeiro_id])
    service = relationship("Service")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)