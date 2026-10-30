import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import (
    User, RoleEnum, Appointment, Avaliacao, ConsentimentoLGPD, RefreshToken,
    PasswordResetToken, JornadaTrabalho, BloqueioHorario, BarbearioServico,
    Service, AuditLog,
)
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, PasswordConfirmation
from app.dependencies import get_current_user, require_roles
from app.routers.auth import revoke_user_refresh_tokens
from app.core.audit import record as record_audit
from app.core.clock import utc_now_naive
from app.core.security import verify_password, get_password_hash

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar clientes."))
):
    # Only return users with role = CLIENTE for client management
    # (Barbeiros and Admins are managed separately if needed)
    users = db.query(User)\
        .filter(User.role == RoleEnum.CLIENTE)\
        .offset(skip)\
        .limit(limit)\
        .all()
    return users


@router.get("/barbeiros", response_model=List[UserResponse])
def get_barbers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar barbeiros."))
):
    return db.query(User).filter(User.role == RoleEnum.BARBEIRO, User.ativo.is_(True)).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar clientes."))
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Only allow viewing CLIENTE users through this endpoint
    if user.role != RoleEnum.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint é apenas para gerenciamento de clientes"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar clientes."))
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Only allow updating CLIENTE users through this endpoint
    if user.role != RoleEnum.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint é apenas para gerenciamento de clientes"
        )

    update_data = user_update.model_dump(exclude_unset=True)
    previous_blocked = user.bloqueado
    if update_data.get("bloqueado") is True and not user.bloqueado:
        revoke_user_refresh_tokens(db, user.id)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    if "bloqueado" in update_data and previous_blocked != user.bloqueado:
        record_audit(db, request, actor=current_user, acao="usuario.bloqueado" if user.bloqueado else "usuario.desbloqueado", entidade="usuario", entidade_id=user.id)
        db.commit()
    return user


# Note: Password changes should be handled through a separate endpoint for security
# Block/unblock is handled via the bloqueado field in the update endpoint above


@router.delete("/me")
def excluir_minha_conta(
    request: Request,
    confirmation: PasswordConfirmation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(confirmation.senha_atual, current_user.senha_hash):
        raise HTTPException(status_code=403, detail="A senha atual está incorreta")
    if current_user.role == RoleEnum.ADMIN:
        active_admins = db.query(User.id).filter(
            User.role == RoleEnum.ADMIN, User.ativo.is_(True),
        ).order_by(User.id).with_for_update().all()
        if len(active_admins) <= 1:
            raise HTTPException(status_code=409, detail="A exclusão não é permitida porque esta é a última conta administradora ativa.")

    user_id, old_role = current_user.id, current_user.role.value
    now = utc_now_naive()
    appointment_ids = [row[0] for row in db.query(Appointment.id).filter(Appointment.user_id == user_id).all()]
    if appointment_ids:
        db.query(Avaliacao).filter(Avaliacao.appointment_id.in_(appointment_ids)).update(
            {Avaliacao.appointment_id: None, Avaliacao.comentario: None}, synchronize_session=False,
        )
    db.query(Appointment).filter(Appointment.user_id == user_id).update(
        {Appointment.user_id: None, Appointment.nome_cliente: None}, synchronize_session=False,
    )
    # The barber account row is anonymized in place, so its historical financial
    # appointments retain the required FK without retaining a real-world identity.
    if current_user.role == RoleEnum.BARBEIRO:
        db.query(JornadaTrabalho).filter(JornadaTrabalho.barbeiro_id == user_id).delete(synchronize_session=False)
        db.query(BloqueioHorario).filter(BloqueioHorario.barbeiro_id == user_id).delete(synchronize_session=False)
        db.query(BarbearioServico).filter(BarbearioServico.barbeiro_id == user_id).delete(synchronize_session=False)

    db.query(ConsentimentoLGPD).filter(ConsentimentoLGPD.user_id == user_id).update(
        {ConsentimentoLGPD.user_id: None, ConsentimentoLGPD.ip_origem: None, ConsentimentoLGPD.origem: "account_erasure"},
        synchronize_session=False,
    )
    revoke_user_refresh_tokens(db, user_id, now)
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update(
        {RefreshToken.user_id: None}, synchronize_session=False,
    )
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.usuario_id == user_id).update(
        {AuditLog.usuario_id: None, AuditLog.entidade_id: None, AuditLog.ip: None, AuditLog.detalhes: {}},
        synchronize_session=False,
    )

    current_user.ativo = False
    current_user.bloqueado = True
    current_user.nome = "Conta anonimizada"
    current_user.email = f"anonimizado-{user_id}-{secrets.token_hex(8)}@invalid.local"
    current_user.senha_hash = get_password_hash(secrets.token_urlsafe(48))
    current_user.consentimento_lgpd = False
    current_user.consentimento_em = None
    record_audit(db, request, actor_role=old_role, acao="usuario.excluido", entidade="usuario", resultado="sucesso")
    db.commit()
    return {"mensagem": "Conta excluída e dados pessoais anonimizados"}


@router.get("/me/export")
@router.get("/me/exportacao")
def exportar_meus_dados(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointments = db.query(Appointment, Service.nome).outerjoin(
        Service, Service.id == Appointment.service_id,
    ).filter(Appointment.user_id == current_user.id).order_by(Appointment.data_hora.desc()).all()
    evaluations = db.query(Avaliacao, Appointment.data_hora).join(
        Appointment, Appointment.id == Avaliacao.appointment_id,
    ).filter(Appointment.user_id == current_user.id).order_by(Avaliacao.criada_em.desc()).all()
    consents = db.query(ConsentimentoLGPD).filter(
        ConsentimentoLGPD.user_id == current_user.id,
    ).order_by(ConsentimentoLGPD.aceito_em.asc()).all()
    result = {
        "schema_version": "1.0",
        "exported_at": utc_now_naive().isoformat(),
        "usuario": {"id": current_user.id, "nome": current_user.nome, "email": current_user.email,
                    "role": current_user.role.value, "consentimento_lgpd": current_user.consentimento_lgpd,
                    "consentimento_em": current_user.consentimento_em.isoformat() if current_user.consentimento_em else None},
        "consentimentos": [{"versao_termos": item.versao_termos, "aceito_em": item.aceito_em.isoformat()} for item in consents],
        "agendamentos": [{"id": item.id, "servico": service_name,
                           "barbeiro": "profissional associado", "data_hora": item.data_hora.isoformat(),
                           "status": item.status.value, "preco": item.preco,
                           "duracao_minutos": item.duracao_minutos, "valor_cobrado": item.valor_cobrado}
                          for item, service_name in appointments],
        "avaliacoes": [{"nota": review.nota, "comentario": review.comentario,
                        "criada_em": review.criada_em.isoformat(),
                        "data_agendamento": appointment_date.isoformat()}
                       for review, appointment_date in evaluations],
    }
    record_audit(db, request, actor=current_user, acao="dados.exportados", entidade="dados_pessoais", entidade_id=current_user.id,
                 detalhes={"agendamentos": len(appointments)})
    db.commit()
    return result
