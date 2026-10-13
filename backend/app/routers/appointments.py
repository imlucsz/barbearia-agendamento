from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import Appointment, Service, User, RoleEnum
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentResponse, AvaliacaoResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify service exists
    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    # Create appointment with snapshot of service price and duration (RN-05)
    db_appointment = Appointment(
        user_id=current_user.id,
        service_id=appointment.service_id,
        data_hora=appointment.data_hora,
        status="agendado",
        # RN-05: Snapshot of service data at time of booking
        preco=service.preco,
        duracao_minutos=service.duracao_minutos
    )

    try:
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horário já agendado para este serviço. Por favor, escolha outro horário."
        )

    return db_appointment


@router.get("/", response_model=List[AppointmentResponse])
def get_user_appointments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointments = db.query(Appointment)\
        .filter(Appointment.user_id == current_user.id)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Check if user owns the appointment or is admin
    if appointment.user_id != current_user.id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return appointment


@router.get("/disponiveis/", response_model=List[dict])
def get_available_slots(
    service_id: int,
    data: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna horários disponíveis para um serviço em uma data específica.
    Implementação básica: retorna horários de 08:00 às 18:00 em intervalos de 30 minutos
    que não estejam já agendados para o serviço especificado.
    RN-01: Verifica se não há conflito com agendamentos existentes.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    # Define working hours (simplified - should come from barbeiro schedule in future)
    WORK_START_HOUR = 8
    WORK_END_HOUR = 18
    SLOT_DURATION_MINUTES = 30  # Slot size for checking availability

    # Generate all possible slots for the day
    available_slots = []
    current_time = datetime.combine(data, datetime.min.time().replace(hour=WORK_START_HOUR))
    end_time = datetime.combine(data, datetime.min.time().replace(hour=WORK_END_HOUR))

    while current_time < end_time:
        slot_end = current_time + timedelta(minutes=service.duracao_minutos)

        # Check if slot is within working hours
        if slot_end > end_time:
            break

        # Check if there's already an appointment for this service at this time
        existing_appointment = db.query(Appointment).filter(
            Appointment.service_id == service_id,
            Appointment.data_hora >= current_time,
            Appointment.data_hora < slot_end
        ).first()

        if not existing_appointment:
            available_slots.append({
                "horario": current_time.time().strftime("%H:%M"),
                "data_hora": current_time.isoformat()
            })

        # Move to next slot
        current_time += timedelta(minutes=SLOT_DURATION_MINUTES)

    return available_slots


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Check if user owns the appointment or is admin
    if appointment.user_id != current_user.id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso negado")

    update_data = appointment_update.dict(exclude_unset=True)

    # Prevent changing service_id or user_id after creation (would break RN-05 snapshot)
    if "service_id" in update_data or "user_id" in update_data:
        raise HTTPException(
            status_code=400,
            detail="Não é possível alterar o serviço ou cliente do agendamento"
        )

    # RN-02: Check rescheduling rules
    if "data_hora" in update_data:
        new_data_hora = update_data["data_hora"]

        # Check if less than 24h until appointment
        time_until_appointment = new_data_hora - datetime.utcnow()
        if time_until_appointment.total_seconds() < 24 * 3600:  # 24 hours in seconds
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível reagendar com menos de 24 horas de antecedência"
            )

        # Check if already rescheduled too many times (Y=2 means max 2 reschedules)
        if appointment.reschedule_count >= 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limite máximo de reagendamentos atingido (máximo 2 reagendamentos permitidos)"
            )

        # If we're actually changing the time (not just setting to same value), increment reschedule count
        if appointment.data_hora != new_data_hora:
            appointment.reschedule_count += 1

    for key, value in update_data.items():
        setattr(appointment, key, value)

    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # Check if user owns the appointment or is admin
    if appointment.user_id != current_user.id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Acesso negado")

    db.delete(appointment)
    db.commit()
    return None


@router.post("/{appointment_id}/avaliacao", response_model=AvaliacaoResponse)
def create_avaliacao(
    appointment_id: int,
    avaliacao: AvaliacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify appointment exists
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")

    # RN-04: Only the appointment owner can evaluate
    if appointment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o cliente dono do agendamento pode avaliá-lo"
        )

    # RN-04: Only completed appointments can be evaluated
    if appointment.status != AppointmentStatusEnum.CONCLUIDO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Só é possível avaliar agendamentos concluídos"
        )

    # Check if already evaluated
    existing_avaliacao = db.query(Avaliacao).filter(Avaliacao.appointment_id == appointment_id).first()
    if existing_avaliacao:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este agendamento já foi avaliado"
        )

    # Create evaluation
    db_avaliacao = Avaliacao(
        appointment_id=appointment_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario
    )
    db.add(db_avaliacao)

    # Update appointment status to avaliado
    appointment.status = AppointmentStatusEnum.AVALIADO

    db.commit()
    db.refresh(db_avaliacao)
    return db_avaliacao


@router.get("/avaliacoes", response_model=List[AvaliacaoResponse])
def get_avaliacoes(
    db: Session = Depends(get_db)
):
    # RF03: Public endpoint for average rating in catalog
    avaliacoes = db.query(Avaliacao).all()
    return avaliacoes