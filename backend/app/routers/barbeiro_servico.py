from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import BarbearioServico, User, Service, RoleEnum
from app.schemas.barbeiro_servico import BarbearioServicoCreate, BarbearioServicoResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/barbeiro-servico", tags=["barbeiro-servico"])


@router.get("/barbeiro/{barbeiro_id}", response_model=List[BarbearioServicoResponse])
def get_servicos_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Apenas o próprio barbeiro ou admin pode ver quais serviços um barbeiro pode executar
    if current_user.role != RoleEnum.ADMIN and current_user.id != barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar serviços do barbeiro."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    servicos = db.query(BarbeiroServico).filter(BarbeiroServico.barbeiro_id == barbeiro_id).all()
    return servicos


@router.get("/servico/{service_id}/barbeiros", response_model=List[BarbearioServicoResponse])
def get_barbeiros_servico(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Apenas admin pode ver quais barbeiros podem executar um serviço específico
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administrador pode visualizar/gerenciar quais barbeiros executam um serviço."
        )

    # Verify that the service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    barbeiros = db.query(BarbeiroServico).filter(BarbeiroServico.service_id == service_id).all()
    return barbeiros


@router.post("/", response_model=BarbearioServicoResponse, status_code=status.HTTP_201_CREATED)
def assign_servico_barbeiro(
    barbeiro_servico: BarbearioServicoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Apenas admin pode atribuir serviços a barbeiros
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administrador pode gerenciar quais serviços cada barbeiro pode executar."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_servico.barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    # Verify that the service exists
    service = db.query(Service).filter(Service.id == barbeiro_servico.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    # Check if already assigned
    existing = db.query(BarbeiroServico).filter(
        BarbearioServico.barbeiro_id == barbeiro_servico.barbeiro_id,
        BarbearioServico.service_id == barbeiro_servico.service_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este serviço já está atribuído a este barbeiro"
        )

    db_barbeiro_servico = BarbearioServico(**barbeiro_servico.dict())
    db.add(db_barbeiro_servico)
    db.commit()
    db.refresh(db_barbeiro_servico)
    return db_barbeiro_servico


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def remove_servico_barbeiro(
    barbeiro_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF17: Gerenciar barbeiros e serviços que cada um executa
    # Apenas admin pode remover serviços de barbeiros
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administrador pode gerenciar quais serviços cada barbeiro pode executar."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    # Verify that the service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")

    barbeiro_servico = db.query(BarbeiroServico).filter(
        BarbearioServico.barbeiro_id == barbeiro_id,
        BarbearioServico.service_id == service_id
    ).first()
    if barbeiro_servico is None:
        raise HTTPException(status_code=404, detail="Associação não encontrada")

    db.delete(barbeiro_servico)
    db.commit()
    return None