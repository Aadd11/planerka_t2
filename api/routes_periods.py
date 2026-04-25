from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_active_user, require_role
from constants import SubmissionStatus, UserRole
from db import get_db
from models import CollectionPeriod, ScheduleSubmission, User
from schedule_service import build_period_holidays, get_period_for_user
from schemas import CollectionPeriodCreate, CollectionPeriodOut

router = APIRouter(prefix="/periods", tags=["periods"])


def period_to_schema(period: CollectionPeriod) -> CollectionPeriodOut:
    data = CollectionPeriodOut.model_validate(period)
    data.holidays = build_period_holidays(period)
    return data


@router.get("/current", response_model=CollectionPeriodOut | None)
def get_current_period(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not current_user.alliance:
        return None

    period = (
        db.query(CollectionPeriod)
        .filter(
            CollectionPeriod.is_open.is_(True),
            CollectionPeriod.alliance == current_user.alliance,
        )
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )
    if not period:
        return None
    return period_to_schema(period)


@router.post("", response_model=CollectionPeriodOut, status_code=status.HTTP_201_CREATED)
def create_period(
    payload: CollectionPeriodCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    alliance = payload.alliance or current_user.alliance
    if current_user.role == UserRole.MANAGER.value and alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Руководитель может создавать периоды только для своей группы")

    db.query(CollectionPeriod).filter(
        CollectionPeriod.is_open.is_(True),
        CollectionPeriod.alliance == alliance,
    ).update({"is_open": False, "updated_at": datetime.now(timezone.utc)})

    period = CollectionPeriod(
        name=payload.name,
        alliance=alliance,
        period_start=payload.period_start,
        period_end=payload.period_end,
        deadline=payload.deadline,
        is_open=True,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period_to_schema(period)


@router.post("/{period_id}/close", response_model=CollectionPeriodOut)
def close_period(
    period_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    if current_user.role == UserRole.MANAGER.value and period.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Нет доступа к этому периоду")

    period.is_open = False
    period.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(period)
    return period_to_schema(period)


@router.get("/current/stats")
def get_current_period_stats(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    period = (
        db.query(CollectionPeriod)
        .filter(
            CollectionPeriod.is_open.is_(True),
            CollectionPeriod.alliance == current_user.alliance,
        )
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )
    if not period:
        return {"totalEmployees": 0, "submittedCount": 0, "pendingCount": 0}

    employees = (
        db.query(User)
        .filter(
            User.alliance == current_user.alliance,
            User.role == UserRole.EMPLOYEE.value,
            User.is_verified.is_(True),
        )
        .all()
    )
    submitted_count = (
        db.query(ScheduleSubmission)
        .join(User, User.id == ScheduleSubmission.user_id)
        .filter(
            ScheduleSubmission.period_id == period.id,
            ScheduleSubmission.status == SubmissionStatus.SUBMITTED.value,
            User.alliance == current_user.alliance,
        )
        .count()
    )
    total = len(employees)
    return {
        "totalEmployees": total,
        "submittedCount": submitted_count,
        "pendingCount": max(total - submitted_count, 0),
    }


@router.get("/current/submissions")
def get_current_period_submissions(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    period = (
        db.query(CollectionPeriod)
        .filter(
            CollectionPeriod.is_open.is_(True),
            CollectionPeriod.alliance == current_user.alliance,
        )
        .order_by(CollectionPeriod.created_at.desc())
        .first()
    )
    if not period:
        return {"submitted": [], "pending": []}

    employees = (
        db.query(User)
        .filter(
            User.alliance == current_user.alliance,
            User.role == UserRole.EMPLOYEE.value,
            User.is_verified.is_(True),
        )
        .order_by(User.full_name.asc())
        .all()
    )
    submission_map = {
        submission.user_id: submission
        for submission in db.query(ScheduleSubmission).filter(ScheduleSubmission.period_id == period.id).all()
    }

    submitted = []
    pending = []
    for employee in employees:
        item = {
            "id": employee.id,
            "fullName": employee.full_name,
            "email": employee.email,
            "group": employee.alliance,
            "status": submission_map.get(employee.id).status if submission_map.get(employee.id) else "draft",
        }
        if item["status"] == SubmissionStatus.SUBMITTED.value:
            submitted.append(item)
        else:
            pending.append(item)
    return {"submitted": submitted, "pending": pending}


@router.get("/history", response_model=list[CollectionPeriodOut])
def get_periods_history(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.ADMIN.value:
        periods = db.query(CollectionPeriod).order_by(CollectionPeriod.created_at.desc()).all()
    else:
        periods = (
            db.query(CollectionPeriod)
            .filter(CollectionPeriod.alliance == current_user.alliance)
            .order_by(CollectionPeriod.created_at.desc())
            .all()
        )
    return [period_to_schema(period) for period in periods]
