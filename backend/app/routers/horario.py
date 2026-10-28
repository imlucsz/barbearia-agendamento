from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import JornadaTrabalho, BloqueioHorario, User, RoleEnum
from app.schemas.horario import JornadaTrabalhoCreate, JornadaTrabalhoUpdate, JornadaTrabalhoResponse, BloqueioHorarioCreate, BloqueioHorarioUpdate, BloqueioHorarioResponse
from app.dependencies import get_current_user
from app.booking import normalize_datetime

router = APIRouter(prefix="/horario", tags=["horario"])


# ===== JORNADAS DE TRABALHO =====
@router.get("/jornadas/{barbeiro_id}", response_model=List[JornadaTrabalhoResponse])
def get_jornadas_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode ver suas jornadas
    if current_user.role != RoleEnum.ADMIN and current_user.id != barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar jornadas."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    jornadas = db.query(JornadaTrabalho).filter(JornadaTrabalho.barbeiro_id == barbeiro_id).all()
    return jornadas


@router.post("/jornadas", response_model=JornadaTrabalhoResponse, status_code=status.HTTP_201_CREATED)
def create_jornada(
    jornada: JornadaTrabalhoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode criar
    if current_user.role != RoleEnum.ADMIN and current_user.id != jornada.barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar jornadas."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == jornada.barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    db_jornada = JornadaTrabalho(**jornada.model_dump())
    db.add(db_jornada)
    db.commit()
    db.refresh(db_jornada)
    return db_jornada


@router.put("/jornadas/{jornada_id}", response_model=JornadaTrabalhoResponse)
def update_jornada(
    jornada_id: int,
    jornada_update: JornadaTrabalhoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar jornadas - só o próprio barbeiro ou admin pode atualizar
    jornada = db.query(JornadaTrabalho).filter(JornadaTrabalho.id == jornada_id).first()
    if jornada is None:
        raise HTTPException(status_code=404, detail="Jornada não encontrada")

    if current_user.role != RoleEnum.ADMIN and current_user.id != jornada.barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar jornadas."
        )

    update_data = jornada_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(jornada, key, value)

    db.commit()
    db.refresh(jornada)
    return jornada


# ===== BLOQUEIOS DE HORÁRIO =====
@router.get("/bloqueios/{barbeiro_id}", response_model=List[BloqueioHorarioResponse])
def get_bloqueios_barbeiro(
    barbeiro_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode ver seus bloqueios
    if current_user.role != RoleEnum.ADMIN and current_user.id != barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode visualizar/gerenciar bloqueios."
        )

    # Verify that the user is actually a barbeiro
    barbeiro = db.query(User).filter(User.id == barbeiro_id).first()
    if not barbeiro or barbeiro.role != RoleEnum.BARBEIRO:
        raise HTTPException(status_code=404, detail="Barbeiro não encontrado")

    bloqueios = db.query(BloqueioHorario).filter(BloqueioHorario.barbeiro_id == barbeiro_id).all()
    return bloqueios


@router.post("/bloqueios", response_model=BloqueioHorarioResponse, status_code=status.HTTP_201_CREATED)
def create_bloqueio(
    bloqueio: BloqueioHorarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode criar
    if current_user.role != RoleEnum.ADMIN and current_user.id != bloqueio.barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios."
        )

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
    return db_bloqueio


@router.put("/bloqueios/{bloqueio_id}", response_model=BloqueioHorarioResponse)
def update_bloqueio(
    bloqueio_id: int,
    bloqueio_update: BloqueioHorarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode atualizar
    bloqueio = db.query(BloqueioHorario).filter(BloqueioHorario.id == bloqueio_id).first()
    if bloqueio is None:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

    if current_user.role != RoleEnum.ADMIN and current_user.id != bloqueio.barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios."
        )

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
    return bloqueio


@router.delete("/bloqueios/{bloqueio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bloqueio(
    bloqueio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF18: Gerenciar bloqueios - só o próprio barbeiro ou admin pode deletar
    bloqueio = db.query(BloqueioHorario).filter(BloqueioHorario.id == bloqueio_id).first()
    if bloqueio is None:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")

    if current_user.role != RoleEnum.ADMIN and current_user.id != bloqueio.barbeiro_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas o próprio barbeiro ou administrador pode criar/alterar bloqueios."
        )

    db.delete(bloqueio)
    db.commit()
    return None
