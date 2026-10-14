from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.booking import (
    BOOKING_WINDOW_DAYS,
    SLOT_INTERVAL_MINUTES,
    lock_barber_for_booking,
    normalize_datetime,
    validate_booking_slot,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    Avaliacao,
    BarbearioServico,
    JornadaTrabalho,
    RoleEnum,
    Service,
    User,
)
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AvaliacaoCreate,
    AvaliacaoResponse,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != RoleEnum.CLIENTE or current_user.bloqueado:
        raise HTTPException(status_code=403, detail="Apenas clientes ativos podem agendar")

    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    lock_barber_for_booking(db, appointment.barbeiro_id)
    start = validate_booking_slot(db, service, appointment.barbeiro_id, appointment.data_hora)
    db_appointment = Appointment(
        user_id=current_user.id,
        nome_cliente=current_user.nome,
        service_id=service.id,
        barbeiro_id=appointment.barbeiro_id,
        data_hora=start,
        status=AppointmentStatusEnum.PENDENTE,
        preco=service.preco,
        duracao_minutos=service.duracao_minutos,
    )

    try:
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O horário foi reservado por outra pessoa. Escolha outro horário.",
        ) from exc
    return db_appointment


@router.get("/", response_model=List[AppointmentResponse])
def get_user_appointments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Appointment)
        .filter(Appointment.user_id == current_user.id)
        .order_by(Appointment.data_hora.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/disponiveis", response_model=List[dict])
def get_available_slots(
    service_id: int,
    data: date,
    barbeiro_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    today = datetime.utcnow().date()
    if data < today or data > (datetime.utcnow() + timedelta(days=BOOKING_WINDOW_DAYS)).date():
        raise HTTPException(
            status_code=400,
            detail=f"Escolha uma data entre hoje e os próximos {BOOKING_WINDOW_DAYS} dias",
        )

    barbers_query = db.query(User).join(
        BarbearioServico, BarbearioServico.barbeiro_id == User.id
    ).filter(
        User.role == RoleEnum.BARBEIRO,
        User.ativo.is_(True),
        BarbearioServico.service_id == service_id,
    )
    if barbeiro_id is not None:
        barbers_query = barbers_query.filter(User.id == barbeiro_id)
    barbers = barbers_query.all()
    if barbeiro_id is not None and not barbers:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado ou não realiza este serviço")

    weekday = (data.weekday() + 1) % 7
    slots = []
    for barber in barbers:
        schedule = db.query(JornadaTrabalho).filter(
            JornadaTrabalho.barbeiro_id == barber.id,
            JornadaTrabalho.dia_semana == weekday,
            JornadaTrabalho.ativo.is_(True),
        ).first()
        if schedule is None:
            continue
        try:
            start_time = datetime.strptime(schedule.hora_inicio, "%H:%M").time()
            end_time = datetime.strptime(schedule.hora_fim, "%H:%M").time()
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Jornada do barbeiro possui horário inválido") from exc

        day_start = datetime.combine(data, start_time)
        day_end = datetime.combine(data, end_time)
        slot_start = day_start
        while slot_start + timedelta(minutes=service.duracao_minutos) <= day_end:
            try:
                valid_start = validate_booking_slot(db, service, barber.id, slot_start)
                slots.append({
                    "horario": valid_start.strftime("%H:%M"),
                    "data_hora": valid_start.isoformat(),
                    "barbeiro_id": barber.id,
                })
            except HTTPException as exc:
                if exc.status_code not in (400, 409):
                    raise
            slot_start += timedelta(minutes=SLOT_INTERVAL_MINUTES)

    return slots


@router.get("/avaliacoes", response_model=List[AvaliacaoResponse])
def get_avaliacoes(db: Session = Depends(get_db)):
    return (
        db.query(Avaliacao)
        .filter(Avaliacao.oculta.is_(False))
        .order_by(Avaliacao.criada_em.desc())
        .all()
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if (
        appointment.user_id != current_user.id
        and appointment.barbeiro_id != current_user.id
        and current_user.role != RoleEnum.ADMIN
    ):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    update_data = appointment_update.dict(exclude_unset=True)
    if any(value is None for value in update_data.values()):
        raise HTTPException(status_code=400, detail="Os campos enviados não podem ser nulos")
    if current_user.role == RoleEnum.CLIENTE and "status" in update_data and "data_hora" in update_data:
        raise HTTPException(status_code=400, detail="Cancele ou reagende em operações separadas")
    is_admin = current_user.role == RoleEnum.ADMIN
    is_assigned_barber = current_user.role == RoleEnum.BARBEIRO and appointment.barbeiro_id == current_user.id
    is_owner = current_user.role == RoleEnum.CLIENTE and appointment.user_id == current_user.id
    if not (is_admin or is_assigned_barber or is_owner):
        raise HTTPException(status_code=403, detail="Acesso negado")
    if not update_data:
        return appointment

    if "status" in update_data:
        new_status = update_data["status"]
        if is_owner and new_status != AppointmentStatusEnum.CANCELADO:
            raise HTTPException(status_code=403, detail="Clientes só podem cancelar seus próprios agendamentos")
        if not (is_admin or is_assigned_barber or (is_owner and new_status == AppointmentStatusEnum.CANCELADO)):
            raise HTTPException(status_code=403, detail="Acesso negado")
        if new_status == AppointmentStatusEnum.CANCELADO and not (is_admin or is_assigned_barber):
            if appointment.status not in (AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.CONFIRMADO):
                raise HTTPException(status_code=400, detail="Este agendamento não pode mais ser cancelado")
            if appointment.data_hora - datetime.utcnow() < timedelta(hours=24):
                raise HTTPException(status_code=400, detail="Cancelamentos exigem 24 horas de antecedência")
        appointment.status = new_status
        if new_status == AppointmentStatusEnum.CONCLUIDO and "valor_cobrado" not in update_data:
            appointment.valor_cobrado = appointment.preco

    if "valor_cobrado" in update_data:
        if not (is_admin or is_assigned_barber):
            raise HTTPException(status_code=403, detail="Apenas a equipe pode registrar o valor cobrado")
        appointment.valor_cobrado = update_data["valor_cobrado"]

    if "data_hora" in update_data:
        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Somente o cliente ou administrador pode reagendar")
        if is_owner and appointment.status not in (AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.CONFIRMADO):
            raise HTTPException(status_code=400, detail="Este agendamento não pode ser reagendado")
        if is_owner and appointment.data_hora - datetime.utcnow() < timedelta(hours=24):
            raise HTTPException(status_code=400, detail="Reagendamentos exigem 24 horas de antecedência")
        if is_owner and appointment.reschedule_count >= 2:
            raise HTTPException(status_code=400, detail="Limite máximo de 2 reagendamentos atingido")
        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        if service is None:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")
        lock_barber_for_booking(db, appointment.barbeiro_id)
        new_start = validate_booking_slot(
            db,
            service,
            appointment.barbeiro_id,
            update_data["data_hora"],
            exclude_appointment_id=appointment.id,
        )
        if new_start != appointment.data_hora and is_owner:
            appointment.reschedule_count += 1
        appointment.data_hora = new_start

    try:
        db.commit()
        db.refresh(appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="O horário foi reservado por outra pessoa") from exc
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_appointment(
        appointment_id,
        AppointmentUpdate(status=AppointmentStatusEnum.CANCELADO),
        db,
        current_user,
    )
    return None


@router.post(
    "/{appointment_id}/avaliacao",
    response_model=AvaliacaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_avaliacao(
    appointment_id: int,
    avaliacao: AvaliacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    if appointment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente dono do agendamento pode avaliá-lo")
    if appointment.status != AppointmentStatusEnum.CONCLUIDO:
        raise HTTPException(status_code=400, detail="Só é possível avaliar agendamentos concluídos")
    if db.query(Avaliacao).filter(Avaliacao.appointment_id == appointment_id).first():
        raise HTTPException(status_code=400, detail="Este agendamento já foi avaliado")

    db_avaliacao = Avaliacao(
        appointment_id=appointment_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario,
    )
    appointment.status = AppointmentStatusEnum.AVALIADO
    db.add(db_avaliacao)
    db.commit()
    db.refresh(db_avaliacao)
    return db_avaliacao
