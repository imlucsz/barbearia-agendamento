from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.user import Appointment, User, Service, RoleEnum, AppointmentStatusEnum, Avaliacao
from app.schemas.appointment import AdminAppointmentCreate, AppointmentResponse, AvaliacaoResponse
from app.dependencies import get_current_user
from app.booking import lock_barber_for_booking, validate_booking_slot

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/agendamentos", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_manual_appointment(
    appointment: AdminAppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar agendamentos manuais")

    client = None
    if appointment.user_id is not None:
        client = db.query(User).filter(
            User.id == appointment.user_id,
            User.role == RoleEnum.CLIENTE,
            User.ativo.is_(True),
            User.bloqueado.is_(False),
        ).first()
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente ativo não encontrado")

    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    if service is None:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    lock_barber_for_booking(db, appointment.barbeiro_id)
    start = validate_booking_slot(db, service, appointment.barbeiro_id, appointment.data_hora)
    manual_appointment = Appointment(
        user_id=client.id if client else None,
        nome_cliente=client.nome if client else appointment.nome_cliente,
        service_id=service.id,
        barbeiro_id=appointment.barbeiro_id,
        data_hora=start,
        status=AppointmentStatusEnum.CONFIRMADO,
        preco=service.preco,
        duracao_minutos=service.duracao_minutos,
    )
    db.add(manual_appointment)
    try:
        db.commit()
        db.refresh(manual_appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="O horário foi reservado por outra pessoa") from exc
    return manual_appointment


@router.get("/agenda", response_model=List[AppointmentResponse])
def get_agenda_by_date(
    data: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only ADMIN can view the full agenda
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem visualizar a agenda completa."
        )

    # Get appointments for the specified date
    appointments = db.query(Appointment)\
        .filter(Appointment.data_hora >= datetime.combine(data, datetime.min.time()))\
        .filter(Appointment.data_hora < datetime.combine(data + timedelta(days=1), datetime.min.time()))\
        .order_by(Appointment.data_hora.asc())\
        .all()

    return appointments


@router.get("/me/agenda", response_model=List[AppointmentResponse])
def get_my_agenda_by_date(
    data: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # BARBEIRO can view their own agenda for a specific date
    if current_user.role not in [RoleEnum.BARBEIRO, RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas barbeiros e administradores podem visualizar agendas."
        )

    # Barbers see appointments assigned to them; admins can use this route for their own barber account.
    query = db.query(Appointment)\
        .filter(Appointment.data_hora >= datetime.combine(data, datetime.min.time()))\
        .filter(Appointment.data_hora < datetime.combine(data + timedelta(days=1), datetime.min.time()))\
        .filter(Appointment.barbeiro_id == current_user.id)\
        .order_by(Appointment.data_hora.asc())

    # For BARBEIRO, we might want to filter by services they can perform
    # For now, we'll show all their appointments
    appointments = query.all()

    return appointments


@router.get("/avaliacoes", response_model=List[AvaliacaoResponse])
def get_all_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem moderar avaliações."
        )

    return db.query(Avaliacao).order_by(Avaliacao.criada_em.desc()).all()


@router.get("/relatorio", response_model=dict)
def get_financial_report(
    inicio: date,
    fim: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF21: Financial report - only ADMIN can access
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem acessar relatórios financeiros."
        )

    # Validate date range
    if inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de início deve ser anterior ou igual à data de fim"
        )

    # Older appointments may not have a recorded charged amount.
    resultado = db.query(
        func.count(Appointment.id).label('total_agendamentos'),
        func.sum(func.coalesce(Appointment.valor_cobrado, Appointment.preco)).label('total_receita'),
        func.avg(func.coalesce(Appointment.valor_cobrado, Appointment.preco)).label('ticket_medio')
    ).filter(
        Appointment.status.in_(
            (AppointmentStatusEnum.CONCLUIDO, AppointmentStatusEnum.AVALIADO)
        ),
        Appointment.data_hora >= datetime.combine(inicio, datetime.min.time()),
        Appointment.data_hora < datetime.combine(fim + timedelta(days=1), datetime.min.time())
    ).first()

    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat()
        },
        "total_agendamentos": resultado.total_agendamentos or 0,
        "total_receita": float(resultado.total_receita or 0),
        "ticket_medio": float(resultado.ticket_medio or 0)
    }


@router.patch("/avaliacoes/{avaliacao_id}/ocultar", response_model=AvaliacaoResponse)
def toggle_avaliacao_oculta(
    avaliacao_id: int,
    ocultar: bool,  # True to hide, False to unhide
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF22: Moderar avaliações - only ADMIN can hide/unhide evaluations
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem moderar avaliações."
        )

    avaliacao = db.query(Avaliacao).filter(Avaliacao.id == avaliacao_id).first()
    if avaliacao is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")

    avaliacao.oculta = ocultar
    db.commit()
    db.refresh(avaliacao)
    return avaliacao