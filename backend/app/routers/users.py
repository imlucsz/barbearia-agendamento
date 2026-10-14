from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User, RoleEnum
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate
from app.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF19: Gerenciar clientes - apenas ADMIN pode listar todos os clientes
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar clientes."
        )

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
    current_user: User = Depends(get_current_user)
):
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar barbeiros."
        )

    return db.query(User).filter(User.role == RoleEnum.BARBEIRO, User.ativo.is_(True)).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF19: Gerenciar clientes - visualizar cliente específico
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar clientes."
        )

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # RF19: Gerenciar clientes - editar cliente
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem gerenciar clientes."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Only allow updating CLIENTE users through this endpoint
    if user.role != RoleEnum.CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint é apenas para gerenciamento de clientes"
        )

    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


# Note: Password changes should be handled through a separate endpoint for security
# Block/unblock is handled via the bloqueado field in the update endpoint above


@router.delete("/me")
def excluir_minha_conta(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.ativo = False
    current_user.email = f"excluido_{current_user.id}@anonimizado.local"
    current_user.nome = "Usuário excluído"
    # mantém o hashed_password intacto ou randomiza, mas NUNCA deixa null se outro campo depender dele
    db.commit()
    return {"mensagem": "Conta excluída com sucesso"}