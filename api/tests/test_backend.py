from __future__ import annotations

import asyncio
from datetime import date

import pytest
from fastapi import BackgroundTasks, HTTPException

from app import app
from auth import verify_password
from config import Settings
from constants import UserRole
from models import ScheduleEntry, User, VerificationToken
from routes_admin import get_users
from routes_auth import hash_verification_token, login, register_user
from routes_export import export_schedule
from routes_manager import create_manager_comment
from routes_schedule import get_my_schedule, get_schedule_for_user, update_my_schedule
from schedule_service import validate_schedule
from schemas import ManagerCommentCreate, ScheduleBulkUpdate, ScheduleValidateRequest, UserCreate

from conftest import create_entry, create_period, create_user


def test_register_and_login(db_session):
    payload = UserCreate(
        full_name="Ivan Ivanov",
        email="ivan@example.com",
        password="password123",
        alliance="Retail East",
        employeeCategory="adult",
    )
    user = register_user(payload, db_session)
    assert user.email == "ivan@example.com"
    assert verify_password("password123", user.password_hash)

    user.is_verified = True
    db_session.commit()

    class JsonLoginRequest:
        headers = {"content-type": "application/json"}

        async def json(self):
            return {"email": "ivan@example.com", "password": "password123"}

        async def form(self):
            return {}

    token = asyncio.run(login(JsonLoginRequest(), db_session))
    assert token.access_token


def test_register_stores_hashed_verification_token(db_session):
    payload = UserCreate(
        full_name="Ivan Ivanov",
        email="ivan.hash@example.com",
        password="password123",
        alliance="Retail East",
        employeeCategory="adult",
    )
    user = register_user(payload, db_session)
    token_row = db_session.query(VerificationToken).filter(VerificationToken.user_id == user.id).first()
    assert token_row is not None
    assert len(token_row.token) == 64
    assert all(char in "0123456789abcdef" for char in token_row.token)


def test_settings_require_strong_jwt_secret_in_production():
    settings = Settings(
        DATABASE_URL="sqlite:////tmp/t2_security_test.db",
        JWT_SECRET_KEY="CHANGE_ME_SECRET",
        APP_ENV="production",
        CORS_ORIGINS="http://localhost:8000",
    )
    with pytest.raises(ValueError):
        settings.validate_security()


def test_employee_sees_only_own_schedule(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    other = create_user(
        db_session,
        email="other@example.com",
        full_name="Other",
        alliance="Retail East",
    )
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    period = create_period(db_session)
    create_entry(
        db_session,
        user_id=employee.id,
        period_id=period.id,
        day="2026-05-01",
        status="work",
        meta={"dayType": "work", "segments": [{"start": "09:00", "end": "18:00"}]},
    )
    create_entry(
        db_session,
        user_id=other.id,
        period_id=period.id,
        day="2026-05-01",
        status="work",
        meta={"dayType": "work", "segments": [{"start": "10:00", "end": "19:00"}]},
    )

    own = get_my_schedule(None, employee, db_session)
    assert date(2026, 5, 1) in own.entries

    with pytest.raises(HTTPException) as exc:
        get_schedule_for_user(other.id, None, employee, db_session)
    assert exc.value.status_code == 403

    manager_view = get_schedule_for_user(other.id, None, manager, db_session)
    assert manager_view.user.email == "other@example.com"


def test_manager_sees_only_his_group(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    same_group = create_user(
        db_session,
        email="employee1@example.com",
        full_name="Same Group",
        alliance="Retail East",
    )
    other_group = create_user(
        db_session,
        email="employee2@example.com",
        full_name="Other Group",
        alliance="Retail West",
    )

    users = get_users(None, None, None, manager, db_session)
    emails = {item.email for item in users}
    assert same_group.email in emails
    assert other_group.email not in emails


def test_manager_cannot_edit_employee_schedule_directly():
    matching_routes = [
        route
        for route in app.routes
        if getattr(route, "path", "") == "/schedules/by-user/{user_id}"
    ]
    assert matching_routes
    assert matching_routes[0].methods == {"GET"}


def test_manager_can_add_comment(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)

    result = create_manager_comment(
        ManagerCommentCreate(userId=employee.id, periodId=period.id, date="2026-05-04", comment="Cover lunch peak"),
        manager,
        db_session,
    )
    assert result.day_comments[date(2026, 5, 4)] == "Cover lunch peak"


def test_employee_cannot_edit_manager_comment(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)
    create_manager_comment(
        ManagerCommentCreate(userId=employee.id, periodId=period.id, date="2026-05-05", comment="Manager note"),
        manager,
        db_session,
    )

    updated = update_my_schedule(
        ScheduleBulkUpdate(
            days={
                "2026-05-05": {
                    "dayType": "work",
                    "segments": [{"start": "09:00", "end": "13:00"}],
                    "managerComment": "Employee override",
                }
            }
        ),
        None,
        employee,
        db_session,
    )
    assert updated.entries[date(2026, 5, 5)].manager_comment == "Manager note"


def test_validate_schedule(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)

    validation = validate_schedule(
        period=period,
        days=ScheduleValidateRequest(
            days={
                "2026-05-01": {
                    "dayType": "work",
                    "segments": [
                        {"start": "09:00", "end": "12:00"},
                        {"start": "11:00", "end": "13:00"},
                    ],
                }
            }
        ).days,
        employee_category=employee.employee_category,
    )
    issue_codes = {issue.code for issue in validation.issues}
    assert "SEGMENTS_OVERLAP" in issue_codes


def test_adult_weekly_norm_warning(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
        category="adult",
    )
    period = create_period(db_session)
    days = {
        f"2026-05-{index:02d}": {
            "dayType": "work",
            "segments": [{"start": "09:00", "end": "18:00"}],
        }
        for index in range(4, 9)
    }
    validation = validate_schedule(period=period, days=ScheduleValidateRequest(days=days).days, employee_category=employee.employee_category)
    warning_codes = {issue.code for issue in validation.issues if issue.severity.value == "warning"}
    assert "WEEKLY_NORM_EXCEEDED" in warning_codes


def test_minor_weekly_norm_error(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
        category="minor_student",
    )
    period = create_period(db_session)
    days = {
        "2026-05-04": {"dayType": "work", "segments": [{"start": "09:00", "end": "14:00"}]},
        "2026-05-05": {"dayType": "work", "segments": [{"start": "09:00", "end": "14:00"}]},
        "2026-05-06": {"dayType": "work", "segments": [{"start": "09:00", "end": "14:00"}]},
        "2026-05-07": {"dayType": "work", "segments": [{"start": "09:00", "end": "14:00"}]},
    }
    validation = validate_schedule(period=period, days=ScheduleValidateRequest(days=days).days, employee_category=employee.employee_category)
    error_codes = {issue.code for issue in validation.issues if issue.severity.value == "error"}
    assert "WEEKLY_NORM_EXCEEDED" in error_codes


def test_minor_night_work_error(db_session):
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
        category="minor_not_student",
    )
    period = create_period(db_session)
    validation = validate_schedule(
        period=period,
        days=ScheduleValidateRequest(
            days={"2026-05-01": {"dayType": "work", "segments": [{"start": "21:00", "end": "23:00"}]}}
        ).days,
        employee_category=employee.employee_category,
    )
    error_codes = {issue.code for issue in validation.issues if issue.severity.value == "error"}
    assert "MINOR_NIGHT_WORK_FORBIDDEN" in error_codes


def test_export_works(db_session):
    manager = create_user(
        db_session,
        email="manager@example.com",
        full_name="Manager",
        alliance="Retail East",
        role=UserRole.MANAGER.value,
    )
    employee = create_user(
        db_session,
        email="employee@example.com",
        full_name="Employee",
        alliance="Retail East",
    )
    period = create_period(db_session)
    create_entry(
        db_session,
        user_id=employee.id,
        period_id=period.id,
        day="2026-05-02",
        status="work",
        meta={"dayType": "work", "segments": [{"start": "09:00", "end": "18:00"}]},
    )

    response = export_schedule(BackgroundTasks(), period.id, manager, db_session)
    assert str(response.path).endswith(".xlsx")
