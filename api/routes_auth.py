from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash, verify_password, get_current_active_user
from config import settings
from db import get_db
from models import User, VerificationToken, UserRole
from schemas import Token, UserCreate, UserMe, VerificationRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserMe, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter(
            (User.email == payload.email)
            | (User.external_id == payload.external_id if payload.external_id else False)
        )
        .first()
    )
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
        category=payload.category,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create verification token (you'll send it via email / message in real system)
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    token = VerificationToken(user_id=user.id, token=token_str, expires_at=expires_at)
    db.add(token)
    db.commit()

    # In a real system you would send `token_str` via email or another channel
    # Here we just expose it in the response header for convenience

    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="Некорректный Email или пароль")

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Некорректный Email или пароль")

    access_token = create_access_token(
        subject=str(user.id), role=user.role, is_verified=user.is_verified
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

    now = datetime.now(timezone.utc)
    if token.expires_at < now:
        raise HTTPException(status_code=400, detail="Токен верификации истек")

    user = token.user
    user.is_verified = True
    token.consumed = True
    db.commit()
    db.refresh(user)

    return user


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_active_user)):
    # We wire this properly from main app where dependency injection is available
    return current_user

