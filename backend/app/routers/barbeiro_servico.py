from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import ensure_owner_id, get_current_user, require_roles
from app.models.user import BarbearioServico, User, Service, RoleEnum
from app.core.audit import record as record_audit
from app.schemas.barbeiro_servico import (
    BarbearioServicoCreate,
    BarbearioServicoResponse,
    BarbearioServicoWithBarbeiroResponse,
)

router = APIRouter(prefix="/barbeiro-servico", tags=["barbeiro-servico"])


@router.get("/barbeiro/{barbeiro_id}", response_model=List[BarbearioServicoResponse])
def get_servicos_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Apenas o próprio barbeiro ou admin pode ver quais serviços um barbeiro pode executar
    ensure_owner_id(
        barbeiro_id, current_user,
        detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar serviços do barbeiro.",
    )
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    servicos = db.query(BarbearioServico).filter(BarbearioServico.barbeiro_id == barbeiro_id).all()
    return servicos


@router.get("/servico/{service_id}/barbeiros", response_model=List[BarbearioServicoWithBarbeiroResponse])
def get_barbeiros_servico(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.CLIENTE, detail="Acesso negado. Apenas administrador ou cliente pode visualizar quais barbeiros executam um serviço."))
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Admin e cliente podem ver quais barbeiros podem executar um serviço específico
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    barbeiros = db.query(BarbearioServico, User.nome).join(
        User, BarbearioServico.barbeiro_id == User.id
    ).filter(
        BarbearioServico.service_id == service_id
    ).all()

    result = []
    for barbeiro_servico, barbeiro_nome in barbeiros:
        result.append(BarbearioServicoWithBarbeiroResponse(
            id=barbeiro_servico.id,
            barbeiro_id=barbeiro_servico.barbeiro_id,
            service_id=barbeiro_servico.service_id,
            barbeiro_nome=barbeiro_nome
        ))
    return result


@router.post("/", response_model=BarbearioServicoResponse, status_code=status.HTTP_201_CREATED)
def assign_servico_barbeiro(
    barbeiro_servico: BarbearioServicoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administrador pode gerenciar quais serviços cada barbeiro pode executar."))
):
    barbeiro = db.query(User).filter(User.id == barbeiro_servico.barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    service = db.query(Service).filter(Service.id == barbeiro_servico.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    existing = db.query(BarbearioServico).filter(
        BarbearioServico.barbeiro_id == barbeiro_servico.barbeiro_id,
        BarbearioServico.service_id == barbeiro_servico.service_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este serviço já está atribuído a este barbeiro"
        )

    db_barbeiro_servico = BarbearioServico(**barbeiro_servico.model_dump())
    db.add(db_barbeiro_servico)
    db.commit()
    db.refresh(db_barbeiro_servico)
    record_audit(db, request, actor=current_user, acao="associacao.criada", entidade="barbeiro_servico", entidade_id=db_barbeiro_servico.id)
    db.commit()
    return db_barbeiro_servico


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def remove_servico_barbeiro(
    barbeiro_id: int,
    service_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administrador pode gerenciar quais serviços cada barbeiro pode executar."))
):
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    barbeiro_servico = db.query(BarbearioServico).filter(
        BarbearioServico.barbeiro_id == barbeiro_id,
        BarbearioServico.service_id == service_id
    ).first()
    if barbeiro_servico is None:
        raise HTTPException(status_code=404, detail="Associação não encontrada")

    association_id = barbeiro_servico.id
    db.delete(barbeiro_servico)
    db.commit()
    record_audit(db, request, actor=current_user, acao="associacao.excluida", entidade="barbeiro_servico", entidade_id=association_id, detalhes={"barbeiro_id": barbeiro_id, "service_id": service_id})
    db.commit()
    return None
