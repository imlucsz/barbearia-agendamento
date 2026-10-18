from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    BarbearioServico,
    BloqueioHorario,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)


BOOKING_WINDOW_DAYS = 14
SLOT_INTERVAL_MINUTES = 30
ACTIVE_APPOINTMENT_STATUSES = [
    AppointmentStatusEnum.PENDENTE,
    AppointmentStatusEnum.CONFIRMADO,
]


def lock_barber_for_booking(db: Session, barber_id: int) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        return

    db.query(User.id).filter(User.id == barber_id).with_for_update().first()


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def validate_booking_slot(
    db: Session,
    service: Service,
    barber_id: int,
    start: datetime,
    exclude_appointment_id: int | None = None,
) -> datetime:
    start = normalize_datetime(start)
    now = datetime.utcnow()
    if start < now:
        raise HTTPException(status_code=400, detail="Não é possível agendar em um horário passado")
    if start.date() > (now + timedelta(days=BOOKING_WINDOW_DAYS)).date():
        raise HTTPException(
            status_code=400,
            detail=f"Os agendamentos podem ser feitos com até {BOOKING_WINDOW_DAYS} dias de antecedência",
        )

    barber = db.query(User).filter(User.id == barber_id, User.role == RoleEnum.BARBEIRO, User.ativo.is_(True)).first()
    if barber is None:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    association = db.query(BarbearioServico).filter(
        BarbearioServico.barbeiro_id == barber_id,
        BarbearioServico.service_id == service.id,
    ).first()
    if association is None:
        raise HTTPException(status_code=400, detail="Este barbeiro não realiza o serviço selecionado")

    weekday = (start.weekday() + 1) % 7
    schedule = db.query(JornadaTrabalho).filter(
        JornadaTrabalho.barbeiro_id == barber_id,
        JornadaTrabalho.dia_semana == weekday,
        JornadaTrabalho.ativo.is_(True),
    ).first()
    if schedule is None:
        raise HTTPException(status_code=400, detail="O barbeiro não atende nesta data")

    try:
        opening = datetime.combine(start.date(), time.fromisoformat(schedule.hora_inicio))
        closing = datetime.combine(start.date(), time.fromisoformat(schedule.hora_fim))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Jornada do barbeiro possui horário inválido") from exc

    end = start + timedelta(minutes=service.duracao_minutos)
    if start < opening or end > closing:
        raise HTTPException(status_code=400, detail="O horário não comporta a duração do serviço dentro da jornada")

    block = db.query(BloqueioHorario).filter(
        BloqueioHorario.barbeiro_id == barber_id,
        BloqueioHorario.ativo.is_(True),
        BloqueioHorario.inicio < end,
        BloqueioHorario.fim > start,
    ).first()
    if block is not None:
        raise HTTPException(status_code=409, detail="O horário selecionado está bloqueado")

    appointments = db.query(Appointment).filter(
        Appointment.barbeiro_id == barber_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.data_hora < end,
    )
    if exclude_appointment_id is not None:
        appointments = appointments.filter(Appointment.id != exclude_appointment_id)
    for existing in appointments.all():
        existing_end = existing.data_hora + timedelta(minutes=existing.duracao_minutos)
        if start < existing_end and end > existing.data_hora:
            raise HTTPException(status_code=409, detail="O horário selecionado conflita com outro agendamento")

    return start
