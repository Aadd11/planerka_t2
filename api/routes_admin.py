from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db import get_db
from models import User, UserRole
from schemas import UserOut
from auth import get_current_active_user

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return current_user

@router.get("/users", response_model=List[UserOut])
def get_users(
    verified: Optional[bool] = None,
    alliance: Optional[str] = None,
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.role == UserRole.MANAGER:
        if not alliance:
            alliance = current_user.alliance
        query = query.filter(User.alliance == alliance)
    else:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    if verified is not None:
        query = query.filter(User.is_verified == verified)
    if alliance:
        query = query.filter(User.alliance == alliance)
    if role:
        query = query.filter(User.role == role)

    return query.all()

@router.put("/users/{user_id}/verify", response_model=UserOut)
def verify_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()

@router.put("/users/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = new_role
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}/alliance", response_model=UserOut)
def change_alliance(
    user_id: int,
    new_alliance: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.alliance = new_alliance
    db.commit()
    db.refresh(user)
    return user