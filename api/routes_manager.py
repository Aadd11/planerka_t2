from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import require_role
from constants import DayType, UserRole
from db import get_db
from models import ScheduleEntry, User
from routes_periods import period_to_schema
from schedule_service import (
    ensure_group_access,
    get_or_create_submission,
    get_period_for_user,
    normalize_schedule_day,
    submission_to_schema,
    validate_schedule,
)
from schemas import (
    CoverageBucket,
    CoverageResponse,
    ManagerCommentCreate,
    ManagerCommentsOut,
    ManagerEmployeeSchedule,
    ManagerSchedulesOut,
    ScheduleDayPayload,
)

router = APIRouter(prefix="/manager", tags=["manager"])


def _manager_users(db: Session, manager: User) -> list[User]:
    return (
        db.query(User)
        .filter(
            User.alliance == manager.alliance,
            User.role == UserRole.EMPLOYEE.value,
            User.is_verified.is_(True),
        )
        .order_by(User.full_name.asc())
        .all()
    )


@router.get(
    "/schedules",
    response_model=ManagerSchedulesOut,
    summary="Матрица графиков по группе",
)
def get_manager_schedules(
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(db, current_user, period_id=period_id, require_open=period_id is None)
    users = _manager_users(db, current_user) if current_user.role != UserRole.ADMIN.value else (
        db.query(User)
        .filter(User.role == UserRole.EMPLOYEE.value, User.is_verified.is_(True))
        .order_by(User.alliance.asc(), User.full_name.asc())
        .all()
    )

    items: list[ManagerEmployeeSchedule] = []
    for user in users:
        if current_user.role == UserRole.ADMIN.value and user.alliance != period.alliance:
            continue
        entries = (
            db.query(ScheduleEntry)
            .filter(ScheduleEntry.user_id == user.id, ScheduleEntry.period_id == period.id)
            .order_by(ScheduleEntry.day.asc())
            .all()
        )
        entry_map = {entry.day: ScheduleDayPayload.model_validate(normalize_schedule_day({"status": entry.status, "meta": entry.meta or {}})) for entry in entries}
        submission = get_or_create_submission(db, user.id, period.id)
        items.append(
            ManagerEmployeeSchedule(
                user=user,
                submission=submission_to_schema(submission),
                entries=entry_map,
                validation=validate_schedule(
                    period=period,
                    days=entry_map,
                    employee_category=user.employee_category,
                ),
            )
        )
    return ManagerSchedulesOut(period=period_to_schema(period), items=items)


@router.get(
    "/comments",
    response_model=ManagerCommentsOut,
    summary="Получить комментарии руководителя",
)
def get_manager_comments(
    user_id: int,
    period_id: int,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    ensure_group_access(current_user, user)
    period = get_period_for_user(db, current_user, period_id=period_id, alliance=user.alliance)
    submission = get_or_create_submission(db, user.id, period.id)
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.user_id == user.id, ScheduleEntry.period_id == period.id)
        .all()
    )
    day_comments = {
        entry.day: (entry.meta or {}).get("managerComment")
        for entry in entries
        if (entry.meta or {}).get("managerComment")
    }
    return ManagerCommentsOut(
        userId=user.id,
        periodId=period.id,
        scheduleComment=submission.manager_comment,
        dayComments=day_comments,
    )


@router.post(
    "/comments",
    response_model=ManagerCommentsOut,
    status_code=status.HTTP_201_CREATED,
    summary="Оставить комментарий руководителя",
)
def create_manager_comment(
    payload: ManagerCommentCreate,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    ensure_group_access(current_user, user)
    period = get_period_for_user(db, current_user, period_id=payload.period_id, alliance=user.alliance)
    submission = get_or_create_submission(db, user.id, period.id)

    if payload.date is None:
        submission.manager_comment = payload.comment
    else:
        if payload.date < period.period_start or payload.date > period.period_end:
            raise HTTPException(status_code=400, detail="Комментарий можно оставить только в пределах периода")
        entry = (
            db.query(ScheduleEntry)
            .filter(
                ScheduleEntry.user_id == user.id,
                ScheduleEntry.period_id == period.id,
                ScheduleEntry.day == payload.date,
            )
            .first()
        )
        if not entry:
            normalized = normalize_schedule_day(
                {"dayType": DayType.UNAVAILABLE.value, "segments": []},
                payload.comment,
                allow_manager_comment_input=True,
            )
            entry = ScheduleEntry(
                user_id=user.id,
                period_id=period.id,
                day=payload.date,
                status=normalized["status"],
                meta=normalized["meta"],
            )
            db.add(entry)
        else:
            normalized = normalize_schedule_day(
                {"status": entry.status, "meta": entry.meta or {}},
                payload.comment,
                allow_manager_comment_input=True,
            )
            entry.status = normalized["status"]
            entry.meta = normalized["meta"]
    db.commit()
    return get_manager_comments(payload.user_id, period.id, current_user, db)


@router.get(
    "/coverage",
    response_model=CoverageResponse,
    summary="Coverage по выбранному дню",
)
def get_manager_coverage(
    day: date,
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(db, current_user, period_id=period_id, require_open=period_id is None)
    if day < period.period_start or day > period.period_end:
        raise HTTPException(status_code=400, detail="Дата должна попадать в активный период")

    coverage: dict[int, list[str]] = defaultdict(list)
    users = _manager_users(db, current_user) if current_user.role != UserRole.ADMIN.value else (
        db.query(User)
        .filter(User.role == UserRole.EMPLOYEE.value, User.is_verified.is_(True), User.alliance == period.alliance)
        .order_by(User.full_name.asc())
        .all()
    )
    for user in users:
        entry = (
            db.query(ScheduleEntry)
            .filter(
                ScheduleEntry.user_id == user.id,
                ScheduleEntry.period_id == period.id,
                ScheduleEntry.day == day,
            )
            .first()
        )
        if not entry:
            continue
        normalized = normalize_schedule_day({"status": entry.status, "meta": entry.meta or {}})
        if normalized["dayType"] != DayType.WORK.value:
            continue
        for segment in normalized["segments"]:
            start_hour = int(segment["start"].split(":")[0])
            end_hour = int(segment["end"].split(":")[0])
            for hour in range(start_hour, end_hour + 1):
                if hour > 23:
                    continue
                coverage[hour].append(user.full_name)

    buckets = [
        CoverageBucket(hour=f"{hour:02d}:00", count=len(coverage.get(hour, [])), users=sorted(coverage.get(hour, [])))
        for hour in range(24)
    ]
    return CoverageResponse(day=day, periodId=period.id, buckets=buckets)
