from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_active_user, get_password_hash, verify_password
from constants import UserRole
from db import get_db
from models import User, VerificationToken
from schedule_service import get_weekly_norm_hours
from schemas import LoginRequest, Token, UserCreate, UserMe, VerificationRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserMe,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация сотрудника",
    description="Создает нового пользователя со статусом `is_verified = false`.",
)
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


@router.post(
    "/login",
    response_model=Token,
    summary="Вход по email и паролю",
    description=(
        "Принимает либо JSON `{email, password}`, либо form-data "
        "с полями `username`/`email` и `password`."
    ),
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    email, password = await _extract_login_credentials(request)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Некорректный email или пароль")

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        is_verified=user.is_verified,
    )
    return Token(access_token=access_token)


async def _extract_login_credentials(request: Request) -> tuple[str, str]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = LoginRequest.model_validate(await request.json())
        return str(payload.email), payload.password

    form = await request.form()
    email = form.get("email") or form.get("username")
    password = form.get("password")
    if not email or not password:
        raise HTTPException(
            status_code=400,
            detail="Для входа передайте email/username и password",
        )
    return str(email), str(password)


@router.post(
    "/verify",
    response_model=UserMe,
    summary="Подтверждение аккаунта по токену",
)
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


@router.get(
    "/me",
    response_model=UserMe,
    summary="Профиль текущего пользователя",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
