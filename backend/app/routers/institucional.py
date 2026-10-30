from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import InformacaoInstitucional, User, RoleEnum
from app.schemas.institucional import InformacaoInstitucionalCreate, InformacaoInstitucionalUpdate, InformacaoInstitucionalResponse
from app.dependencies import require_roles
from app.core.audit import record as record_audit

router = APIRouter(prefix="/informacoes", tags=["informacoes-institucionais"])


@router.get("/", response_model=InformacaoInstitucionalResponse)
def get_informacoes(
    db: Session = Depends(get_db)
):
    # RF20: Informações institucionais - público para visualização
    # (Em um sistema real, talvez queiramos permitir edição apenas por ADMIN)
    informacao = db.query(InformacaoInstitucional).first()
    if informacao is None:
        raise HTTPException(status_code=404, detail="Informações institucionais não encontradas")
    return informacao


@router.post("/", response_model=InformacaoInstitucionalResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_informacoes(
    informacao: InformacaoInstitucionalCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar informações institucionais."))
):
    # Check if already exists
    informacao_existente = db.query(InformacaoInstitucional).first()

    if informacao_existente:
        # Update existing
        for key, value in informacao.model_dump().items():
            setattr(informacao_existente, key, value)
        db.commit()
        db.refresh(informacao_existente)
        record_audit(db, request, actor=current_user, acao="institucional.alterada", entidade="informacoes_institucionais", entidade_id=informacao_existente.id)
        db.commit()
        return informacao_existente
    else:
        # Create new
        db_informacao = InformacaoInstitucional(**informacao.model_dump())
        db.add(db_informacao)
        db.commit()
        db.refresh(db_informacao)
        record_audit(db, request, actor=current_user, acao="institucional.criada", entidade="informacoes_institucionais", entidade_id=db_informacao.id)
        db.commit()
        return db_informacao


@router.put("/", response_model=InformacaoInstitucionalResponse)
def update_informacoes(
    informacao: InformacaoInstitucionalUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.ADMIN, detail="Acesso negado. Apenas administradores podem gerenciar informações institucionais."))
):
    informacao_existente = db.query(InformacaoInstitucional).first()
    if informacao_existente is None:
        raise HTTPException(status_code=404, detail="Informações institucionais não encontradas")

    update_data = informacao.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(informacao_existente, key, value)

    db.commit()
    db.refresh(informacao_existente)
    record_audit(db, request, actor=current_user, acao="institucional.alterada", entidade="informacoes_institucionais", entidade_id=informacao_existente.id)
    db.commit()
    return informacao_existente
