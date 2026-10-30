from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import Response
import csv
import io
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models.user import Appointment, User, Service, RoleEnum, AppointmentStatusEnum, Avaliacao
from app.schemas.appointment import AdminAppointmentCreate, AppointmentResponse, AvaliacaoResponse
from app.dependencies import require_roles
from app.models.user import AuditLog
from app.core.audit import record as record_audit
from app.booking import lock_barber_for_booking, validate_booking_slot

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/agendamentos", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_manual_appointment(
    appointment: AdminAppointmentCreate,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.BARBEIRO, detail="Apenas administradores podem criar agendamentos manuais"))
):
    assigned_barber_id = current_user.id if current_user.role == RoleEnum.BARBEIRO else appointment.barbeiro_id

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

    lock_barber_for_booking(db, assigned_barber_id)
    start = validate_booking_slot(db, service, assigned_barber_id, appointment.data_hora)
    manual_appointment = Appointment(
        user_id=client.id if client else None,
        nome_cliente=client.nome if client else appointment.nome_cliente,
        service_id=service.id,
        barbeiro_id=assigned_barber_id,
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
    record_audit(db, request, actor=current_user, acao="agendamento.criado", entidade="agendamento", entidade_id=manual_appointment.id)
    db.commit()
    return manual_appointment


@router.get("/agenda", response_model=List[AppointmentResponse])
def get_agenda_by_date(
    data: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem visualizar a agenda completa."))
):
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
    current_user: User = Depends(require_roles(RoleEnum.BARBEIRO, RoleEnum.ADMIN, detail="Acesso negado. Apenas barbeiros e administradores podem visualizar agendas."))
):
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
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem moderar avaliações."))
):
    return db.query(Avaliacao).order_by(Avaliacao.criada_em.desc()).all()


@router.get("/relatorio", response_model=dict)
def get_financial_report(
    inicio: date,
    fim: date,
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem acessar relatórios financeiros."))
):
    # Validate date range
    if inicio > fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de início deve ser anterior ou igual à data de fim"
        )

    # Older appointments may not have a recorded charged amount.
    financial_statuses = (AppointmentStatusEnum.CONCLUIDO, AppointmentStatusEnum.AVALIADO)
    period_start = datetime.combine(inicio, datetime.min.time())
    period_end = datetime.combine(fim + timedelta(days=1), datetime.min.time())
    appointment_filter = (
        Appointment.data_hora >= period_start,
        Appointment.data_hora < period_end,
    )
    resultado = db.query(
        func.count(Appointment.id).label('total_agendamentos'),
        func.sum(func.coalesce(Appointment.valor_cobrado, Appointment.preco)).label('total_receita'),
        func.avg(func.coalesce(Appointment.valor_cobrado, Appointment.preco)).label('ticket_medio')
    ).filter(
        Appointment.status.in_(financial_statuses),
        *appointment_filter,
    ).first()

    barber_rows = db.query(
        User.id, User.nome, func.count(Appointment.id),
        func.sum(func.coalesce(Appointment.valor_cobrado, Appointment.preco)),
    ).join(Appointment, Appointment.barbeiro_id == User.id).filter(
        Appointment.status.in_(financial_statuses), *appointment_filter,
    ).group_by(User.id, User.nome).order_by(User.nome, User.id).all()
    service_rows = db.query(
        Service.id, Service.nome, func.count(Appointment.id),
        func.sum(func.coalesce(Appointment.valor_cobrado, Appointment.preco)),
    ).join(Appointment, Appointment.service_id == Service.id).filter(
        Appointment.status.in_(financial_statuses), *appointment_filter,
    ).group_by(Service.id, Service.nome).order_by(Service.nome, Service.id).all()
    day_rows = db.query(
        func.date(Appointment.data_hora), func.count(Appointment.id),
        func.sum(func.coalesce(Appointment.valor_cobrado, Appointment.preco)),
    ).filter(
        Appointment.status.in_(financial_statuses), *appointment_filter,
    ).group_by(func.date(Appointment.data_hora)).order_by(func.date(Appointment.data_hora)).all()
    status_rows = db.query(Appointment.status, func.count(Appointment.id)).filter(
        Appointment.data_hora >= period_start, Appointment.data_hora < period_end,
        Appointment.status.in_((AppointmentStatusEnum.CONCLUIDO, AppointmentStatusEnum.AVALIADO,
                                AppointmentStatusEnum.CANCELADO, AppointmentStatusEnum.FALTA)),
    ).group_by(Appointment.status).all()
    status_counts = {row.status: row[1] for row in status_rows}

    record_audit(db, request, actor=current_user, acao="dados.exportados", entidade="relatorio_financeiro", detalhes={"inicio": inicio.isoformat(), "fim": fim.isoformat()})
    db.commit()
    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat()
        },
        "total_agendamentos": resultado.total_agendamentos or 0,
        "total_receita": float(resultado.total_receita or 0),
        "ticket_medio": float(resultado.ticket_medio or 0),
        "por_barbeiro": [
            {"barbeiro_id": row[0], "barbeiro": row[1], "total_agendamentos": row[2], "receita": float(row[3] or 0)}
            for row in barber_rows
        ],
        "por_servico": [
            {"servico_id": row[0], "servico": row[1], "total_agendamentos": row[2], "receita": float(row[3] or 0)}
            for row in service_rows
        ],
        "por_dia": [
            {"dia": str(row[0]), "total_agendamentos": row[1], "receita": float(row[2] or 0)}
            for row in day_rows
        ],
        "contagem_status": {
            "concluido": status_counts.get(AppointmentStatusEnum.CONCLUIDO, 0)
                          + status_counts.get(AppointmentStatusEnum.AVALIADO, 0),
            "cancelado": status_counts.get(AppointmentStatusEnum.CANCELADO, 0),
            "falta": status_counts.get(AppointmentStatusEnum.FALTA, 0),
        },
    }


def _csv_safe(value):
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@router.get("/relatorio/csv")
def export_financial_report_csv(
    inicio: date,
    fim: date,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem acessar relatórios financeiros.")),
):
    if inicio > fim:
        raise HTTPException(status_code=400, detail="Data de início deve ser anterior ou igual à data de fim")
    period_start = datetime.combine(inicio, datetime.min.time())
    period_end = datetime.combine(fim + timedelta(days=1), datetime.min.time())
    rows = db.query(Appointment, User.nome, Service.nome).join(
        User, Appointment.barbeiro_id == User.id
    ).join(Service, Appointment.service_id == Service.id).filter(
        Appointment.data_hora >= period_start, Appointment.data_hora < period_end,
        Appointment.status.in_((AppointmentStatusEnum.CONCLUIDO, AppointmentStatusEnum.AVALIADO,
                                AppointmentStatusEnum.CANCELADO, AppointmentStatusEnum.FALTA)),
    ).order_by(Appointment.data_hora, Appointment.id).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["data_hora", "barbeiro", "servico", "status", "valor_cobrado"])
    for appointment, barber_name, service_name in rows:
        charge = appointment.valor_cobrado if appointment.valor_cobrado is not None else appointment.preco
        writer.writerow([_csv_safe(appointment.data_hora.isoformat()), _csv_safe(barber_name),
                         _csv_safe(service_name), _csv_safe(appointment.status.value), _csv_safe(charge)])
    record_audit(db, request, actor=current_user, acao="dados.exportados", entidade="relatorio_financeiro_csv",
                 detalhes={"inicio": inicio.isoformat(), "fim": fim.isoformat(), "quantidade": len(rows)})
    db.commit()
    filename = f"relatorio-financeiro-{inicio.isoformat()}-{fim.isoformat()}.csv"
    return Response(
        content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/avaliacoes/{avaliacao_id}/ocultar", response_model=AvaliacaoResponse)
def toggle_avaliacao_oculta(
    avaliacao_id: int,
    ocultar: bool,  # True to hide, False to unhide
    db: Session = Depends(get_db),
    request: Request = None,
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem moderar avaliações."))
):
    avaliacao = db.query(Avaliacao).filter(Avaliacao.id == avaliacao_id).first()
    if avaliacao is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada")

    avaliacao.oculta = ocultar
    db.commit()
    db.refresh(avaliacao)
    record_audit(db, request, actor=current_user, acao="avaliacao.moderada", entidade="avaliacao", entidade_id=avaliacao.id, detalhes={"oculta": ocultar})
    db.commit()
    return avaliacao


@router.get("/auditoria")
def listar_auditoria(
    request: Request,
    usuario: Optional[int] = Query(default=None, ge=1),
    acao: Optional[str] = Query(default=None, max_length=100),
    entidade: Optional[str] = Query(default=None, max_length=100),
    de: Optional[datetime] = None,
    ate: Optional[datetime] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado")),
):
    if de is not None and ate is not None and de > ate:
        raise HTTPException(status_code=400, detail="A data inicial deve ser anterior ou igual à data final")
    query = db.query(AuditLog)
    if usuario is not None:
        query = query.filter(AuditLog.usuario_id == usuario)
    if acao:
        query = query.filter(AuditLog.acao == acao)
    if entidade:
        query = query.filter(AuditLog.entidade == entidade)
    if de:
        query = query.filter(AuditLog.ocorrido_em >= de)
    if ate:
        query = query.filter(AuditLog.ocorrido_em <= ate)
    total = query.count()
    rows = query.order_by(AuditLog.ocorrido_em.desc(), AuditLog.id.desc()).offset(skip).limit(limit).all()
    record_audit(db, request, actor=current_user, acao="auditoria.consultada", entidade="audit_logs", detalhes={"quantidade": len(rows)})
    db.commit()
    return {"items": [
        {"id": row.id, "usuario_id": row.usuario_id, "ator_role": row.ator_role,
         "acao": row.acao, "entidade": row.entidade, "entidade_id": row.entidade_id,
         "ip": row.ip, "resultado": row.resultado, "detalhes": row.detalhes,
         "ocorrido_em": row.ocorrido_em.isoformat()}
        for row in rows
    ], "total": total, "skip": skip, "limit": limit}
