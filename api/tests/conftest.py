from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import pytest


TEST_DB_PATH = Path("/tmp/t2_schedule_test.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from auth import create_access_token, get_password_hash  # noqa: E402
from constants import UserRole  # noqa: E402
from db import Base, SessionLocal, engine  # noqa: E402
from models import CollectionPeriod, ScheduleEntry, User  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def auth_headers():
    def _make(user: User) -> dict[str, str]:
        token = create_access_token(
            subject=str(user.id),
            role=user.role,
            is_verified=user.is_verified,
        )
        return {"Authorization": f"Bearer {token}"}

    return _make


def create_user(
    session,
    *,
    email: str,
    full_name: str,
    alliance: str,
    role: str = UserRole.EMPLOYEE.value,
    category: str = "adult",
    verified: bool = True,
) -> User:
    weekly_norm = {"adult": 40.0, "minor_not_student": 35.0, "minor_student": 17.5}[category]
    user = User(
        email=email,
        password_hash=get_password_hash("password123"),
        registered=True,
        is_verified=verified,
        full_name=full_name,
        alliance=alliance,
        role=role,
        employee_category=category,
        weekly_norm_hours=weekly_norm,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_period(session, *, alliance: str = "Retail East") -> CollectionPeriod:
    period = CollectionPeriod(
        name="May 2026",
        alliance=alliance,
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 14),
        deadline=datetime(2026, 4, 30, 18, 0, 0),
        is_open=True,
    )
    session.add(period)
    session.commit()
    session.refresh(period)
    return period


def create_entry(session, *, user_id: int, period_id: int, day: str, status: str, meta: dict):
    entry = ScheduleEntry(
        user_id=user_id,
        period_id=period_id,
        day=date.fromisoformat(day),
        status=status,
        meta=meta,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
