from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_verified_user, require_role
from constants import UserRole
from db import get_db
from models import User
from schedule_service import get_weekly_norm_hours
from schemas import AdminAllianceUpdate, AdminRoleUpdate, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: User = Depends(require_role(UserRole.ADMIN))) -> User:
    return current_user


@router.get("/users", response_model=list[UserOut], summary="Список пользователей")
def get_users(
    verified: bool | None = None,
    alliance: str | None = None,
    role: str | None = None,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in {UserRole.ADMIN.value, UserRole.MANAGER.value}:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    query = db.query(User)
    if current_user.role == UserRole.MANAGER.value:
        query = query.filter(User.alliance == current_user.alliance)
    elif alliance:
        query = query.filter(User.alliance == alliance)

    if verified is not None:
        query = query.filter(User.is_verified.is_(verified))
    if role:
        query = query.filter(User.role == role)

    return query.order_by(User.full_name.asc()).all()


@router.put("/users/{user_id}/verify", response_model=UserOut, summary="Подтвердить пользователя")
def verify_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/role", response_model=UserOut, summary="Изменить роль пользователя")
def change_role(
    user_id: int,
    payload: AdminRoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.role = payload.role.value
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/alliance", response_model=UserOut, summary="Изменить группу пользователя")
def change_alliance(
    user_id: int,
    payload: AdminAllianceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.alliance = payload.alliance
    if user.role == UserRole.EMPLOYEE.value:
        user.weekly_norm_hours = get_weekly_norm_hours(user.employee_category)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(user)
    db.commit()
