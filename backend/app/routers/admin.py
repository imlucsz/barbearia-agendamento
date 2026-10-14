from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.user import Appointment, User, Service, RoleEnum, AppointmentStatusEnum
from app.schemas.appointment import AppointmentResponse, AvaliacaoResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


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
        .filter(Appointment.data_hora < datetime.combine(date, datetime.max.time()))\
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

    # Get appointments for the specified date belonging to the current user
    query = db.query(Appointment)\
        .filter(Appointment.data_hora >= datetime.combine(data, datetime.min.time()))\
        .filter(Appointment.data_hora < datetime.combine(date, datetime.max.time()))\
        .filter(Appointment.user_id == current_user.id)\
        .order_by(Appointment.data_hora.asc())

    # For BARBEIRO, we might want to filter by services they can perform
    # For now, we'll show all their appointments
    appointments = query.all()

    return appointments


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

    # Get completed appointments in the date range and sum the preco field (snapshot of what was paid)
    # RF21: Baseado em RF14 (agendamentos concluídos)
    resultado = db.query(
        func.count(Appointment.id).label('total_agendamentos'),
        func.sum(Appointment.preco).label('total_receita'),
        func.avg(Appointment.preco).label('ticket_medio')
    ).filter(
        Appointment.status == AppointmentStatusEnum.CONCLUIDO,
        Appointment.data_hora >= datetime.combine(inicio, datetime.min.time()),
        Appointment.data_hora < datetime.combine(fim, datetime.max.time()) + timedelta(days=1)
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