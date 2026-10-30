from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import JornadaTrabalho, BloqueioHorario, User, RoleEnum
from app.schemas.horario import JornadaTrabalhoCreate, JornadaTrabalhoUpdate, JornadaTrabalhoResponse, BloqueioHorarioCreate, BloqueioHorarioUpdate, BloqueioHorarioResponse
from app.dependencies import ensure_owner_id, ensure_resource_owner, get_current_user
from app.booking import normalize_datetime
from app.core.audit import record as record_audit

router = APIRouter(prefix="/horario", tags=["horario"])


# ===== JORNADAS DE TRABALHO =====
@router.get("/jornadas/{barbeiro_id}", response_model=List[JornadaTrabalhoResponse])
def get_jornadas_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode ver suas jornadas
    ensure_owner_id(barbeiro_id, current_user, detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar jornadas.")

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    jornadas = db.query(JornadaTrabalho).filter(JornadaTrabalho.barbeiro_id == barbeiro_id).all()
    return jornadas


@router.post("/jornadas", response_model=JornadaTrabalhoResponse, status_code=status.HTTP_201_CREATED)
def create_jornada(
    jornada: JornadaTrabalhoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode criar
    ensure_owner_id(jornada.barbeiro_id, current_user, detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar jornadas.")

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == jornada.barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    db_jornada = JornadaTrabalho(**jornada.model_dump())
    db.add(db_jornada)
    db.commit()
    db.refresh(db_jornada)
    record_audit(db, request, actor=current_user, acao="jornada.criada", entidade="jornada", entidade_id=db_jornada.id)
    db.commit()
    return db_jornada


@router.put("/jornadas/{jornada_id}", response_model=JornadaTrabalhoResponse)
def update_jornada(
    jornada_id: int,
    jornada_update: JornadaTrabalhoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode atualizar
    jornada = db.query(JornadaTrabalho).filter(JornadaTrabalho.id == jornada_id).first()
    if jornada is None:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    ensure_resource_owner(jornada, current_user, owner_fields=("barbeiro_id",), detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar jornadas.")

    update_data = jornada_update.model_dump(exclude_unset=True)
    if any(value is None for value in update_data.values()):
        raise HTTPException(status_code=400, detail="Os campos enviados não podem ser nulos")
    hora_inicio = update_data.get("hora_inicio", jornada.hora_inicio)
    hora_fim = update_data.get("hora_fim", jornada.hora_fim)
    if hora_inicio >= hora_fim:
        raise HTTPException(status_code=400, detail="O fim da jornada deve ser posterior ao início")
    for key, value in update_data.items():
        setattr(jornada, key, value)

    db.commit()
    db.refresh(jornada)
    record_audit(db, request, actor=current_user, acao="jornada.alterada", entidade="jornada", entidade_id=jornada.id)
    db.commit()
    return jornada


@router.delete("/jornadas/{jornada_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_jornada(
    jornada_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jornada = db.query(JornadaTrabalho).filter(JornadaTrabalho.id == jornada_id).first()
    if jornada is None:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")
    ensure_resource_owner(
        jornada, current_user, owner_fields=("barbeiro_id",),
        detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode remover jornadas.",
    )
    deleted_id = jornada.id
    db.delete(jornada)
    db.commit()
    record_audit(db, request, actor=current_user, acao="jornada.excluida", entidade="jornada", entidade_id=deleted_id)
    db.commit()
    return None


# ===== BLOQUEIOS DE HORÁRIO =====
@router.get("/bloqueios/{barbeiro_id}", response_model=List[BloqueioHorarioResponse])
def get_bloqueios_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode ver seus bloqueios
    ensure_owner_id(barbeiro_id, current_user, detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar bloqueios.")

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    bloqueios = db.query(BloqueioHorario).filter(BloqueioHorario.barbeiro_id == barbeiro_id).all()
    return bloqueios


@router.post("/bloqueios", response_model=BloqueioHorarioResponse, status_code=status.HTTP_201_CREATED)
def create_bloqueio(
    bloqueio: BloqueioHorarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode criar
    ensure_resource_owner(bloqueio, current_user, owner_fields=("barbeiro_id",), detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios.")

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == bloqueio.barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    data = bloqueio.model_dump()
    data["inicio"] = normalize_datetime(data["inicio"])
    data["fim"] = normalize_datetime(data["fim"])
    if data["fim"] <= data["inicio"]:
        raise HTTPException(status_code=400, detail="O fim do bloqueio deve ser posterior ao início")
    db_bloqueio = BloqueioHorario(**data)
    db.add(db_bloqueio)
    db.commit()
    db.refresh(db_bloqueio)
    record_audit(db, request, actor=current_user, acao="bloqueio.criado", entidade="bloqueio", entidade_id=db_bloqueio.id)
    db.commit()
    return db_bloqueio


@router.put("/bloqueios/{bloqueio_id}", response_model=BloqueioHorarioResponse)
def update_bloqueio(
    bloqueio_id: int,
    bloqueio_update: BloqueioHorarioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode atualizar
    bloqueio = db.query(BloqueioHorario).filter(BloqueioHorario.id == bloqueio_id).first()
    if bloqueio is None:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

    ensure_resource_owner(bloqueio, current_user, owner_fields=("barbeiro_id",), detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios.")

    update_data = bloqueio_update.model_dump(exclude_unset=True)
    inicio = normalize_datetime(update_data.get("inicio", bloqueio.inicio))
    fim = normalize_datetime(update_data.get("fim", bloqueio.fim))
    if fim <= inicio:
        raise HTTPException(status_code=400, detail="O fim do bloqueio deve ser posterior ao início")
    if "inicio" in update_data:
        update_data["inicio"] = inicio
    if "fim" in update_data:
        update_data["fim"] = fim
    for key, value in update_data.items():
        setattr(bloqueio, key, value)

    db.commit()
    db.refresh(bloqueio)
    record_audit(db, request, actor=current_user, acao="bloqueio.alterado", entidade="bloqueio", entidade_id=bloqueio.id)
    db.commit()
    return bloqueio


@router.delete("/bloqueios/{bloqueio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bloqueio(
    bloqueio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode deletar
    bloqueio = db.query(BloqueioHorario).filter(BloqueioHorario.id == bloqueio_id).first()
    if bloqueio is None:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

    ensure_resource_owner(bloqueio, current_user, owner_fields=("barbeiro_id",), detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios.")

    deleted_id = bloqueio.id
    db.delete(bloqueio)
    db.commit()
    record_audit(db, request, actor=current_user, acao="bloqueio.excluido", entidade="bloqueio", entidade_id=deleted_id)
    db.commit()
    return None
