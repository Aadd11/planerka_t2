from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_active_user, get_password_hash, verify_password
from constants import UserRole
from db import get_db
from models import User, VerificationToken
from schedule_service import get_weekly_norm_hours
from schemas import Token, UserCreate, UserMe, VerificationRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserMe, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    user = User(
        email=payload.email,
        external_id=payload.external_id,
        password_hash=get_password_hash(payload.password),
        registered=True,
        is_verified=False,
        full_name=payload.full_name,
        alliance=payload.alliance,
        employee_category=payload.employee_category.value,
        weekly_norm_hours=get_weekly_norm_hours(payload.employee_category.value),
        role=UserRole.EMPLOYEE.value,
    )
    db.add(user)
    db.flush()

    verification_token = VerificationToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification_token)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Некорректный email или пароль")

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        is_verified=user.is_verified,
    )
    return Token(access_token=access_token)


@router.post("/verify", response_model=UserMe)
def verify_account(payload: VerificationRequest, db: Session = Depends(get_db)):
    token = (
        db.query(VerificationToken)
        .filter(VerificationToken.token == payload.token, VerificationToken.consumed.is_(False))
        .first()
    )
    if not token:
        raise HTTPException(status_code=400, detail="Неверный токен верификации")

    if token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Токен верификации истек")

    user = token.user
    user.is_verified = True
    token.consumed = True
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
