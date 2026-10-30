import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import validate_scheduling_timezone
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
SCHEDULING_TIMEZONE_ENV = "SCHEDULING_TIMEZONE"
DEFAULT_SCHEDULING_TIMEZONE = "America/Sao_Paulo"
ACTIVE_APPOINTMENT_STATUSES = [
    AppointmentStatusEnum.PENDENTE,
    AppointmentStatusEnum.CONFIRMADO,
]

ALLOWED_APPOINTMENT_STATUS_TRANSITIONS = {
    AppointmentStatusEnum.PENDENTE: {
        AppointmentStatusEnum.CONFIRMADO,
        AppointmentStatusEnum.CANCELADO,
    },
    AppointmentStatusEnum.CONFIRMADO: {
        AppointmentStatusEnum.CONCLUIDO,
        AppointmentStatusEnum.FALTA,
        AppointmentStatusEnum.CANCELADO,
    },
    AppointmentStatusEnum.CONCLUIDO: set(),
    AppointmentStatusEnum.CANCELADO: set(),
    AppointmentStatusEnum.FALTA: set(),
    AppointmentStatusEnum.AVALIADO: set(),
}


def schedule_bounds(day: date, schedule: JornadaTrabalho) -> tuple[datetime, datetime]:
    try:
        opening_time = time.fromisoformat(schedule.hora_inicio)
        closing_time = time.fromisoformat(schedule.hora_fim)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Jornada do barbeiro possui horário inválido") from exc

    if (
        opening_time.tzinfo is not None
        or closing_time.tzinfo is not None
        or opening_time.second
        or opening_time.microsecond
        or closing_time.second
        or closing_time.microsecond
    ):
        raise HTTPException(status_code=500, detail="Jornada do barbeiro possui horário inválido")
    opening = datetime.combine(day, opening_time)
    closing = datetime.combine(day, closing_time)
    if closing <= opening:
        raise HTTPException(status_code=500, detail="Jornada do barbeiro possui intervalo inválido")
    return opening, closing


def lock_barber_for_booking(db: Session, barber_id: int) -> None:
    if db.get_bind().dialect.name == "sqlite":
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        return

    db.query(User.id).filter(User.id == barber_id).with_for_update().first()


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(scheduling_timezone()).replace(tzinfo=None)
    return value


def scheduling_timezone() -> ZoneInfo:
    name = os.environ.get(SCHEDULING_TIMEZONE_ENV, DEFAULT_SCHEDULING_TIMEZONE)
    return validate_scheduling_timezone(name)


def now_local() -> datetime:
    """Return barbershop wall time as naive datetime for the existing DB/API contract."""
    return datetime.now(scheduling_timezone()).replace(tzinfo=None)


def validate_slot_against_loaded_data(
    service: Service,
    barber_id: int,
    start: datetime,
    *,
    schedule: JornadaTrabalho | None,
    blocks: list[BloqueioHorario],
    appointments: list[Appointment],
    now: datetime,
    exclude_appointment_id: int | None = None,
    duration_minutes: int | None = None,
) -> datetime:
    """Apply the reservation rule to data already loaded for this working day."""
    start = normalize_datetime(start)
    if start < now:
        raise HTTPException(status_code=400, detail="Não é possível agendar em um horário passado")
    if start > now + timedelta(days=BOOKING_WINDOW_DAYS):
        raise HTTPException(
            status_code=400,
            detail=f"Os agendamentos podem ser feitos com até {BOOKING_WINDOW_DAYS} dias de antecedência",
        )
    if schedule is None:
        raise HTTPException(status_code=400, detail="O barbeiro não atende nesta data")
    opening, closing = schedule_bounds(start.date(), schedule)
    duration = service.duracao_minutos if duration_minutes is None else duration_minutes
    if not isinstance(duration, int) or duration <= 0:
        raise HTTPException(status_code=500, detail="O serviço possui duração inválida")
    end = start + timedelta(minutes=duration)
    if start < opening or end > closing:
        raise HTTPException(status_code=400, detail="O horário não comporta a duração do serviço dentro da jornada")
    if any(block.inicio < end and block.fim > start for block in blocks):
        raise HTTPException(status_code=409, detail="O horário selecionado está bloqueado")
    for existing in appointments:
        if existing.id == exclude_appointment_id:
            continue
        existing_end = existing.data_hora + timedelta(minutes=existing.duracao_minutos)
        if start < existing_end and end > existing.data_hora:
            raise HTTPException(status_code=409, detail="O horário selecionado conflita com outro agendamento")
    return start


def validate_booking_slot(
    db: Session,
    service: Service,
    barber_id: int,
    start: datetime,
    exclude_appointment_id: int | None = None,
    duration_minutes: int | None = None,
) -> datetime:
    start = normalize_datetime(start)
    now = now_local()
    if start < now:
        raise HTTPException(status_code=400, detail="N?o ? poss?vel agendar em um hor?rio passado")
    if start > now + timedelta(days=BOOKING_WINDOW_DAYS):
        raise HTTPException(status_code=400, detail=f"Os agendamentos podem ser feitos com at? {BOOKING_WINDOW_DAYS} dias de anteced?ncia")
    barber = db.query(User).filter(User.id == barber_id, User.role == RoleEnum.BARBEIRO, User.ativo.is_(True)).first()
    if barber is None:
        raise HTTPException(status_code=404, detail="Barbeiro n?o encontrado")
    association = db.query(BarbearioServico).filter(
        BarbearioServico.barbeiro_id == barber_id, BarbearioServico.service_id == service.id,
    ).first()
    if association is None:
        raise HTTPException(status_code=400, detail="Este barbeiro n?o realiza o servi?o selecionado")
    weekday = (start.weekday() + 1) % 7
    schedule = db.query(JornadaTrabalho).filter(
        JornadaTrabalho.barbeiro_id == barber_id, JornadaTrabalho.dia_semana == weekday,
        JornadaTrabalho.ativo.is_(True),
    ).first()
    if schedule is None:
        raise HTTPException(status_code=400, detail="O barbeiro n?o atende nesta data")
    duration = service.duracao_minutos if duration_minutes is None else duration_minutes
    if not isinstance(duration, int) or duration <= 0:
        raise HTTPException(status_code=500, detail="O servi?o possui dura??o inv?lida")
    end = start + timedelta(minutes=duration)
    block = db.query(BloqueioHorario).filter(
        BloqueioHorario.barbeiro_id == barber_id, BloqueioHorario.ativo.is_(True),
        BloqueioHorario.inicio < end, BloqueioHorario.fim > start,
    ).first()
    appointments_query = db.query(Appointment).filter(
        Appointment.barbeiro_id == barber_id,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES), Appointment.data_hora < end,
    )
    if exclude_appointment_id is not None:
        appointments_query = appointments_query.filter(Appointment.id != exclude_appointment_id)
    return validate_slot_against_loaded_data(
        service, barber_id, start, schedule=schedule, blocks=[block] if block is not None else [],
        appointments=appointments_query.all(), now=now, exclude_appointment_id=exclude_appointment_id,
        duration_minutes=duration_minutes,
    )


def validate_appointment_status_transition(
    db: Session,
    appointment: Appointment,
    target_status: AppointmentStatusEnum,
    actor_role: RoleEnum,
    *,
    validate_confirmation_slot: bool = True,
    target_start: datetime | None = None,
) -> None:
    """Enforce the RF14 status matrix and transition-specific domain rules."""
    if actor_role == RoleEnum.CLIENTE:
        if target_status != AppointmentStatusEnum.CANCELADO:
            raise HTTPException(status_code=403, detail="Clientes sÃ³ podem cancelar seus prÃ³prios agendamentos")
    elif actor_role not in (RoleEnum.ADMIN, RoleEnum.BARBEIRO):
        raise HTTPException(status_code=403, detail="Acesso negado")

    if target_status == AppointmentStatusEnum.AVALIADO:
        raise HTTPException(status_code=400, detail="O status avaliado sÃ³ pode ser definido por uma avaliaÃ§Ã£o vÃ¡lida")

    allowed_targets = ALLOWED_APPOINTMENT_STATUS_TRANSITIONS.get(appointment.status, set())
    if target_status not in allowed_targets:
        raise HTTPException(status_code=400, detail="TransiÃ§Ã£o de status invÃ¡lida para este agendamento")

    now = now_local()
    effective_start = normalize_datetime(target_start or appointment.data_hora)
    if target_status == AppointmentStatusEnum.CANCELADO and actor_role == RoleEnum.CLIENTE:
        if appointment.data_hora - now < timedelta(hours=24):
            raise HTTPException(status_code=400, detail="Cancelamentos exigem 24 horas de antecedÃªncia")

    if target_status in (AppointmentStatusEnum.CONCLUIDO, AppointmentStatusEnum.FALTA):
        if now < effective_start:
            raise HTTPException(status_code=400, detail="O status sÃ³ pode ser registrado apÃ³s o inÃ­cio do atendimento")

    if target_status == AppointmentStatusEnum.CONFIRMADO and validate_confirmation_slot:
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        if service is None:
            raise HTTPException(status_code=404, detail="ServiÃ§o nÃ£o encontrado")
        lock_barber_for_booking(db, appointment.barbeiro_id)
        validate_booking_slot(
            db,
            service,
            appointment.barbeiro_id,
            appointment.data_hora,
            exclude_appointment_id=appointment.id,
            duration_minutes=appointment.duracao_minutos,
        )
