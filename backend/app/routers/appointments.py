from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.booking import (
    BOOKING_WINDOW_DAYS,
    SLOT_INTERVAL_MINUTES,
    lock_barber_for_booking,
    normalize_datetime,
    now_local,
    validate_appointment_status_transition,
    validate_booking_slot,
    validate_slot_against_loaded_data,
)
from app.database import get_db
from app.dependencies import ensure_resource_owner, get_current_user, require_roles
from app.models.user import (
    Appointment,
    AppointmentStatusEnum,
    Avaliacao,
    BarbearioServico,
    BloqueioHorario,
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
from app.core.audit import record as record_audit

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appointment: AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.CLIENTE, detail="Apenas clientes ativos podem agendar")),
):
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
    record_audit(db, request, actor=current_user, acao="agendamento.criado", entidade="agendamento", entidade_id=db_appointment.id)
    db.commit()
    return db_appointment


@router.get("/", response_model=List[AppointmentResponse])
def get_user_appointments(
    skip: int = Query(default=0, ge=0),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Appointment)
        .filter(Appointment.user_id == current_user.id)
        .order_by(Appointment.data_hora.desc())
        .offset(skip)
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


@router.get("/disponiveis", response_model=List[dict])
def get_available_slots(
    service_id: int,
    data: date,
    barbeiro_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(
        RoleEnum.CLIENTE, RoleEnum.ADMIN,
        detail="Apenas clientes e administradores podem consultar horários disponíveis",
    )),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    now = now_local()
    today = now.date()
    if data < today or data > (now + timedelta(days=BOOKING_WINDOW_DAYS)).date():
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
    barber_ids = [barber.id for barber in barbers]
    if not barber_ids:
        return slots
    schedules = {
        schedule.barbeiro_id: schedule
        for schedule in db.query(JornadaTrabalho).filter(
            JornadaTrabalho.barbeiro_id.in_(barber_ids),
            JornadaTrabalho.dia_semana == weekday,
            JornadaTrabalho.ativo.is_(True),
        ).all()
    }
    day_start = datetime.combine(data, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    blocks_by_barber = {}
    for block in db.query(BloqueioHorario).filter(
        BloqueioHorario.barbeiro_id.in_(barber_ids),
        BloqueioHorario.ativo.is_(True),
        BloqueioHorario.inicio < day_end,
        BloqueioHorario.fim > day_start,
    ).all():
        blocks_by_barber.setdefault(block.barbeiro_id, []).append(block)
    appointments_by_barber = {}
    for appointment in db.query(Appointment).filter(
        Appointment.barbeiro_id.in_(barber_ids),
        Appointment.status.in_([AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.CONFIRMADO]),
        Appointment.data_hora < day_end,
    ).all():
        appointments_by_barber.setdefault(appointment.barbeiro_id, []).append(appointment)
    for barber in barbers:
        schedule = schedules.get(barber.id)
        if schedule is None:
            continue
        try:
            start_time = datetime.strptime(schedule.hora_inicio, "%H:%M").time()
            end_time = datetime.strptime(schedule.hora_fim, "%H:%M").time()
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Jornada do barbeiro possui horário inválido") from exc

        day_start = datetime.combine(data, start_time)
        day_end = datetime.combine(data, end_time)
        if day_end <= day_start:
            raise HTTPException(status_code=500, detail="Jornada do barbeiro possui intervalo inválido")
        slot_start = day_start
        while slot_start + timedelta(minutes=service.duracao_minutos) <= day_end:
            try:
                valid_start = validate_slot_against_loaded_data(
                    service,
                    barber.id,
                    slot_start,
                    schedule=schedule,
                    blocks=blocks_by_barber.get(barber.id, []),
                    appointments=appointments_by_barber.get(barber.id, []),
                    now=now,
                )
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
    ensure_resource_owner(
        appointment, current_user, owner_fields=("user_id", "barbeiro_id"), detail="Acesso negado",
    )
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    old_status, old_start, old_charge = appointment.status, appointment.data_hora, appointment.valor_cobrado
    update_data = appointment_update.model_dump(exclude_unset=True)
    if any(value is None for value in update_data.values()):
        raise HTTPException(status_code=400, detail="Os campos enviados não podem ser nulos")
    if current_user.role == RoleEnum.CLIENTE and "status" in update_data and "data_hora" in update_data:
        raise HTTPException(status_code=400, detail="Cancele ou reagende em operações separadas")
    is_admin = current_user.role == RoleEnum.ADMIN
    is_assigned_barber = current_user.role == RoleEnum.BARBEIRO and appointment.barbeiro_id == current_user.id
    is_owner = current_user.role == RoleEnum.CLIENTE and appointment.user_id == current_user.id
    ensure_resource_owner(
        appointment, current_user, owner_fields=("user_id", "barbeiro_id"), detail="Acesso negado",
    )
    if not update_data:
        return appointment

    if "status" in update_data:
        new_status = update_data["status"]
        validate_appointment_status_transition(
            db,
            appointment,
            new_status,
            current_user.role,
            validate_confirmation_slot="data_hora" not in update_data,
            target_start=update_data.get("data_hora"),
        )
        if "valor_cobrado" in update_data and new_status != AppointmentStatusEnum.CONCLUIDO:
            raise HTTPException(
                status_code=400,
                detail="O valor cobrado só pode acompanhar a conclusão do atendimento",
            )
        appointment.status = new_status
        if new_status == AppointmentStatusEnum.CONCLUIDO and "valor_cobrado" not in update_data:
            appointment.valor_cobrado = appointment.preco

    if "valor_cobrado" in update_data:
        if not (is_admin or is_assigned_barber):
            raise HTTPException(status_code=403, detail="Apenas a equipe pode registrar o valor cobrado")
        if "status" not in update_data:
            raise HTTPException(
                status_code=400,
                detail="O valor cobrado deve ser registrado ao concluir o atendimento",
            )
        appointment.valor_cobrado = update_data["valor_cobrado"]

    if "data_hora" in update_data:
        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Somente o cliente ou administrador pode reagendar")
        if is_owner and appointment.status not in (AppointmentStatusEnum.PENDENTE, AppointmentStatusEnum.CONFIRMADO):
            raise HTTPException(status_code=400, detail="Este agendamento não pode ser reagendado")
        if is_owner and appointment.data_hora - now_local() < timedelta(hours=24):
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
            duration_minutes=appointment.duracao_minutos,
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
    if appointment.status != old_status:
        record_audit(db, request, actor=current_user, acao="agendamento.cancelado" if appointment.status == AppointmentStatusEnum.CANCELADO else "agendamento.status_alterado", entidade="agendamento", entidade_id=appointment.id, detalhes={"status_anterior": old_status.value, "status_novo": appointment.status.value})
    if appointment.data_hora != old_start:
        record_audit(db, request, actor=current_user, acao="agendamento.reagendado", entidade="agendamento", entidade_id=appointment.id)
    if appointment.valor_cobrado != old_charge:
        record_audit(db, request, actor=current_user, acao="agendamento.valor_alterado", entidade="agendamento", entidade_id=appointment.id, detalhes={"valor_anterior": old_charge, "valor_novo": appointment.valor_cobrado})
    db.commit()
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_appointment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_appointment(
        appointment_id,
        AppointmentUpdate(status=AppointmentStatusEnum.CANCELADO),
        db=db,
        current_user=current_user,
        request=request,
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    ensure_resource_owner(
        appointment, current_user, owner_fields=("user_id",), allowed_roles=(),
        required_owner_role=RoleEnum.CLIENTE,
        detail="Apenas o cliente dono do agendamento pode avaliá-lo",
    )
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
    record_audit(db, request, actor=current_user, acao="avaliacao.criada", entidade="avaliacao", entidade_id=db_avaliacao.id, detalhes={"nota": db_avaliacao.nota})
    db.commit()
    return db_avaliacao
