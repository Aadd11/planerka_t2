from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_verified_user, require_role
from constants import DayType, SubmissionStatus, UserRole
from db import get_db
from models import CollectionPeriod, ScheduleEntry, User
from routes_periods import period_to_schema
from schedule_service import (
    build_schedule_map,
    ensure_group_access,
    get_or_create_submission,
    get_period_for_user,
    get_submission,
    normalize_schedule_day,
    serialize_entry,
    submission_to_schema,
    validate_schedule,
)
from schemas import (
    ScheduleBulkUpdate,
    ScheduleBundleOut,
    ScheduleDayPayload,
    ScheduleValidateRequest,
    ScheduleValidationResponse,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _load_entries(db: Session, user_id: int, period_id: int) -> list[ScheduleEntry]:
    return (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.user_id == user_id, ScheduleEntry.period_id == period_id)
        .order_by(ScheduleEntry.day.asc())
        .all()
    )


def _bundle_for_user(db: Session, user: User, period_id: int) -> ScheduleBundleOut:
    period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")

    submission = get_or_create_submission(db, user.id, period.id)
    db.flush()
    entries = _load_entries(db, user.id, period.id)
    schedule_map = build_schedule_map(entries)
    validation = validate_schedule(
        period=period,
        days=schedule_map,
        employee_category=user.employee_category,
    )
    return ScheduleBundleOut(
        user=user,
        period=period_to_schema(period),
        submission=submission_to_schema(submission),
        entries=schedule_map,
        validation=validation,
    )


def _persist_schedule(
    *,
    db: Session,
    user: User,
    period_id: int,
    payload: ScheduleBulkUpdate,
) -> ScheduleBundleOut:
    period = get_period_for_user(db, user, period_id=period_id)
    existing_entries = {
        entry.day: entry
        for entry in _load_entries(db, user.id, period.id)
    }
    submission = get_or_create_submission(db, user.id, period.id)
    existing_submission = get_submission(db, user.id, period.id)

    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == user.id,
        ScheduleEntry.period_id == period.id,
    ).delete()

    for schedule_day, day_payload in sorted(payload.days.items(), key=lambda item: item[0]):
        existing_manager_comment = None
        if schedule_day in existing_entries:
            existing_manager_comment = (existing_entries[schedule_day].meta or {}).get("managerComment")

        normalized = normalize_schedule_day(day_payload, existing_manager_comment=existing_manager_comment)
        day_type = DayType(normalized["dayType"])
        has_data = bool(normalized["segments"] or normalized["employeeComment"] or normalized["managerComment"])
        if day_type == DayType.UNAVAILABLE and not has_data:
            continue

        entry = ScheduleEntry(
            user_id=user.id,
            period_id=period.id,
            day=schedule_day,
            status=normalized["status"],
            meta=normalized["meta"],
        )
        db.add(entry)

    submission.status = SubmissionStatus.DRAFT.value
    submission.employee_comment = payload.employee_comment
    if existing_submission and existing_submission.manager_comment:
        submission.manager_comment = existing_submission.manager_comment
    submission.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _bundle_for_user(db, user, period.id)


@router.get(
    "/me",
    response_model=ScheduleBundleOut,
    summary="Получить свой график",
    description="Возвращает текущий график сотрудника, submission status и результат backend-валидации.",
)
def get_my_schedule(
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(db, current_user, period_id=period_id, require_open=period_id is None)
    db.flush()
    return _bundle_for_user(db, current_user, period.id)


@router.put(
    "/me",
    response_model=ScheduleBundleOut,
    summary="Сохранить график как черновик",
)
def update_my_schedule(
    payload: ScheduleBulkUpdate,
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(db, current_user, period_id=period_id, require_open=period_id is None)
    return _persist_schedule(db=db, user=current_user, period_id=period.id, payload=payload)


@router.post(
    "/me/submit",
    response_model=ScheduleBundleOut,
    summary="Отправить график",
    description="Перед отправкой выполняет backend-валидацию. Ошибки блокируют submit.",
)
def submit_my_schedule(
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(db, current_user, period_id=period_id, require_open=period_id is None)
    bundle = _bundle_for_user(db, current_user, period.id)
    if not bundle.validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "График не отправлен: есть ошибки валидации.",
                "validation": bundle.validation.model_dump(by_alias=True),
            },
        )

    submission = get_or_create_submission(db, current_user.id, period.id)
    submission.status = SubmissionStatus.SUBMITTED.value
    submission.submitted_at = datetime.now(timezone.utc)
    db.commit()
    return _bundle_for_user(db, current_user, period.id)


@router.post(
    "/validate",
    response_model=ScheduleValidationResponse,
    summary="Проверить график",
    description="Проверяет интервалы, недельные нормы, запреты на ночную работу и минимальное число выходных.",
)
def validate_schedule_endpoint(
    payload: ScheduleValidateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    period = get_period_for_user(
        db,
        current_user,
        period_id=payload.period_id,
        require_open=payload.period_id is None,
    )
    return validate_schedule(
        period=period,
        days=payload.days,
        employee_category=(payload.employee_category.value if payload.employee_category else current_user.employee_category),
    )


@router.get(
    "/by-user/{user_id}",
    response_model=ScheduleBundleOut,
    summary="Получить график сотрудника по id",
    description="Доступно руководителю своей группы и admin.",
)
def get_schedule_for_user(
    user_id: int,
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    ensure_group_access(current_user, target_user)
    period = get_period_for_user(
        db,
        current_user,
        period_id=period_id,
        alliance=target_user.alliance,
        require_open=period_id is None,
    )
    return _bundle_for_user(db, target_user, period.id)
