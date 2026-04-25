from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from constants import (
    CATEGORY_NORMS,
    DAY_TYPE_TO_STATUS,
    DEMO_HOLIDAYS,
    DayType,
    EmployeeCategory,
    IssueSeverity,
    LEGACY_STATUS_TO_DAY_TYPE,
    SubmissionStatus,
)
from models import CollectionPeriod, ScheduleEntry, ScheduleSubmission, User
from schemas import (
    ScheduleDayPayload,
    ScheduleValidationResponse,
    SubmissionOut,
    TimeSegment,
    ValidationIssue,
    ValidationSummary,
)


def resolve_employee_category(value: str | None) -> EmployeeCategory:
    try:
        return EmployeeCategory(value or EmployeeCategory.ADULT.value)
    except ValueError:
        return EmployeeCategory.ADULT


def get_weekly_norm_hours(category: str | None) -> float:
    return CATEGORY_NORMS[resolve_employee_category(category)].weekly_hours


def parse_time_to_minutes(value: str) -> int:
    hour_str, minute_str = value.split(":")
    hour = int(hour_str)
    minute = int(minute_str)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Invalid time")
    return hour * 60 + minute


def minutes_to_hours(value: int) -> float:
    return round(value / 60.0, 2)


def format_hours(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def iso_week_key(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def build_period_holidays(period: CollectionPeriod) -> dict[str, str]:
    return {
        holiday_date: holiday_name
        for holiday_date, holiday_name in DEMO_HOLIDAYS.items()
        if period.period_start <= date.fromisoformat(holiday_date) <= period.period_end
    }


def get_period_for_user(
    db: Session,
    actor: User,
    period_id: int | None = None,
    alliance: str | None = None,
    require_open: bool = False,
) -> CollectionPeriod:
    target_alliance = alliance or actor.alliance
    if not target_alliance:
        raise HTTPException(status_code=400, detail="Для пользователя не настроена группа")

    query = db.query(CollectionPeriod).filter(CollectionPeriod.alliance == target_alliance)
    if period_id is not None:
        query = query.filter(CollectionPeriod.id == period_id)
    elif require_open:
        query = query.filter(CollectionPeriod.is_open.is_(True)).order_by(CollectionPeriod.created_at.desc())
    else:
        query = query.order_by(CollectionPeriod.is_open.desc(), CollectionPeriod.created_at.desc())

    period = query.first()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    if require_open and not period.is_open:
        raise HTTPException(status_code=400, detail="Активный период сбора не найден")
    return period


def ensure_group_access(actor: User, target_user: User) -> None:
    if actor.role == "admin":
        return
    if actor.role == "manager" and actor.alliance == target_user.alliance:
        return
    if actor.id == target_user.id:
        return
    raise HTTPException(status_code=403, detail="Вы не можете открыть график сотрудника из другой группы.")


def get_submission(db: Session, user_id: int, period_id: int) -> ScheduleSubmission | None:
    return (
        db.query(ScheduleSubmission)
        .filter(ScheduleSubmission.user_id == user_id, ScheduleSubmission.period_id == period_id)
        .first()
    )


def get_or_create_submission(db: Session, user_id: int, period_id: int) -> ScheduleSubmission:
    submission = get_submission(db, user_id, period_id)
    if submission:
        return submission

    submission = ScheduleSubmission(
        user_id=user_id,
        period_id=period_id,
        status=SubmissionStatus.DRAFT.value,
    )
    db.add(submission)
    db.flush()
    return submission


def _segments_from_legacy(status: str, meta: dict | None) -> list[dict[str, str]]:
    meta = meta or {}
    if status == "shift":
        if meta.get("shiftStart") and meta.get("shiftEnd"):
            return [{"start": meta["shiftStart"], "end": meta["shiftEnd"]}]
        return []
    if status == "split":
        raw_segments = [
            (meta.get("splitStart1"), meta.get("splitEnd1")),
            (meta.get("splitStart2"), meta.get("splitEnd2")),
        ]
        return [
            {"start": start, "end": end}
            for start, end in raw_segments
            if start and end
        ]
    return []


def normalize_schedule_day(
    payload: ScheduleDayPayload | dict | None,
    existing_manager_comment: str | None = None,
    allow_manager_comment_input: bool = False,
) -> dict:
    if payload is None:
        return {
            "status": DayType.UNAVAILABLE.value,
            "dayType": DayType.UNAVAILABLE.value,
            "segments": [],
            "employeeComment": None,
            "managerComment": existing_manager_comment,
        }

    if isinstance(payload, dict):
        payload = ScheduleDayPayload.model_validate(payload)

    raw_meta = payload.meta or {}
    day_type_value = payload.day_type.value if payload.day_type else raw_meta.get("dayType")
    if not day_type_value and payload.status:
        day_type_value = LEGACY_STATUS_TO_DAY_TYPE.get(payload.status, DayType.UNAVAILABLE).value
    if not day_type_value:
        day_type_value = DayType.UNAVAILABLE.value

    if payload.segments:
        segments = [segment.model_dump(by_alias=True) for segment in payload.segments]
    elif raw_meta.get("segments"):
        segments = raw_meta["segments"]
    else:
        segments = _segments_from_legacy(payload.status or "", raw_meta)

    employee_comment = payload.employee_comment
    if employee_comment is None:
        employee_comment = raw_meta.get("employeeComment")

    manager_comment = existing_manager_comment
    if manager_comment is None:
        manager_comment = raw_meta.get("managerComment")
    if allow_manager_comment_input and payload.manager_comment and not existing_manager_comment:
        manager_comment = payload.manager_comment

    normalized = {
        "status": DAY_TYPE_TO_STATUS[DayType(day_type_value)],
        "dayType": day_type_value,
        "segments": segments,
        "employeeComment": employee_comment,
        "managerComment": manager_comment,
    }
    normalized["meta"] = {
        "dayType": normalized["dayType"],
        "segments": normalized["segments"],
        "employeeComment": normalized["employeeComment"],
        "managerComment": normalized["managerComment"],
    }
    return normalized


def serialize_entry(entry: ScheduleEntry) -> ScheduleDayPayload:
    normalized = normalize_schedule_day(
        {"status": entry.status, "meta": entry.meta or {}},
        existing_manager_comment=(entry.meta or {}).get("managerComment"),
    )
    return ScheduleDayPayload.model_validate(normalized)


def build_schedule_map(entries: Iterable[ScheduleEntry]) -> dict[date, ScheduleDayPayload]:
    return {entry.day: serialize_entry(entry) for entry in entries}


def submission_to_schema(submission: ScheduleSubmission) -> SubmissionOut:
    return SubmissionOut.model_validate(submission)


def validate_schedule(
    *,
    period: CollectionPeriod,
    days: dict[date, ScheduleDayPayload | dict],
    employee_category: str | None,
) -> ScheduleValidationResponse:
    category = resolve_employee_category(employee_category)
    norm = CATEGORY_NORMS[category]
    issues: list[ValidationIssue] = []
    weekly_minutes: dict[str, int] = defaultdict(int)
    days_off_count: dict[str, int] = defaultdict(int)
    total_minutes = 0
    non_empty_days = 0

    for current_day, raw_payload in sorted(days.items(), key=lambda item: item[0]):
        normalized = normalize_schedule_day(raw_payload)
        day_type = DayType(normalized["dayType"])
        if current_day < period.period_start or current_day > period.period_end:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="DATE_OUT_OF_PERIOD",
                    date=current_day,
                    message="Дата должна попадать в активный период.",
                )
            )
            continue

        week_key = iso_week_key(current_day)

        if day_type != DayType.UNAVAILABLE:
            non_empty_days += 1

        if day_type != DayType.WORK:
            if day_type in {DayType.DAY_OFF, DayType.VACATION, DayType.HOLIDAY, DayType.UNAVAILABLE}:
                days_off_count[week_key] += 1
            if normalized["segments"]:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="SEGMENTS_FOR_NON_WORK_DAY",
                        date=current_day,
                        message="Интервалы можно указывать только для рабочего дня.",
                    )
                )
            continue

        if not normalized["segments"]:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="WORK_DAY_WITHOUT_SEGMENTS",
                    date=current_day,
                    message="Для рабочего дня нужно добавить хотя бы один интервал.",
                )
            )
            continue

        segment_ranges: list[tuple[int, int]] = []
        for segment in normalized["segments"]:
            try:
                start = parse_time_to_minutes(segment["start"])
                end = parse_time_to_minutes(segment["end"])
            except ValueError:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="INVALID_TIME_FORMAT",
                        date=current_day,
                        message="Используйте время в формате HH:MM.",
                    )
                )
                continue

            if start >= end:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="INVALID_TIME_RANGE",
                        date=current_day,
                        message="Время начала должно быть меньше времени окончания.",
                    )
                )
                continue

            segment_ranges.append((start, end))

        segment_ranges.sort(key=lambda item: item[0])
        day_minutes = 0
        for index, (start, end) in enumerate(segment_ranges):
            if index > 0 and start < segment_ranges[index - 1][1]:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="SEGMENTS_OVERLAP",
                        date=current_day,
                        message="Рабочие интервалы не должны пересекаться.",
                    )
                )
            if norm.night_work_forbidden and (start < 360 or end > 1320):
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="MINOR_NIGHT_WORK_FORBIDDEN",
                        date=current_day,
                        message="Сотрудникам 16–18 лет запрещена работа ночью с 22:00 до 06:00.",
                    )
                )
            day_minutes += end - start

        day_hours = minutes_to_hours(day_minutes)
        total_minutes += day_minutes
        weekly_minutes[week_key] += day_minutes

        if norm.daily_hours is not None and day_hours > norm.daily_hours:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="DAILY_NORM_EXCEEDED",
                    date=current_day,
                    message=(
                        f"Превышена дневная норма: {format_hours(day_hours)} ч "
                        f"из {format_hours(norm.daily_hours)} ч."
                    ),
                )
            )

    if non_empty_days == 0:
        issues.append(
            ValidationIssue(
                severity=IssueSeverity.ERROR,
                code="EMPTY_SCHEDULE",
                date=None,
                message="Добавьте хотя бы один рабочий день или отметьте выходные.",
            )
        )

    for week_key, minutes in sorted(weekly_minutes.items()):
        hours = minutes_to_hours(minutes)
        if hours > norm.weekly_hours:
            severity = IssueSeverity.WARNING if category == EmployeeCategory.ADULT else IssueSeverity.ERROR
            issues.append(
                ValidationIssue(
                    severity=severity,
                    code="WEEKLY_NORM_EXCEEDED",
                    date=None,
                    message=(
                        f"Превышена недельная норма: {format_hours(hours)} ч "
                        f"из {format_hours(norm.weekly_hours)} ч."
                    ),
                )
            )

    if norm.overtime_forbidden:
        for week_key, minutes in sorted(weekly_minutes.items()):
            if minutes_to_hours(minutes) > norm.weekly_hours:
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code="OVERTIME_FORBIDDEN",
                        date=None,
                        message="Для этой категории сотрудников сверхурочная работа запрещена.",
                    )
                )
                break

    for current_day in _iter_period_days(period):
        week_key = iso_week_key(current_day)
        if week_key not in days_off_count and week_key not in weekly_minutes:
            days_off_count[week_key] += 1

    all_week_keys = set(weekly_minutes) | set(days_off_count)
    for week_key in sorted(all_week_keys):
        if days_off_count[week_key] < norm.min_days_off:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code="MIN_DAYS_OFF_REQUIRED",
                    date=None,
                    message="В каждой неделе должно быть минимум 2 выходных дня.",
                )
            )

    summary = ValidationSummary(
        totalHours=minutes_to_hours(total_minutes),
        weeklyHours={week: minutes_to_hours(value) for week, value in sorted(weekly_minutes.items())},
        daysOffCount=dict(sorted(days_off_count.items())),
    )

    issues.sort(key=lambda issue: (issue.severity != IssueSeverity.ERROR, issue.date or date.max, issue.code))
    return ScheduleValidationResponse(
        isValid=not any(issue.severity == IssueSeverity.ERROR for issue in issues),
        summary=summary,
        issues=issues,
    )


def _iter_period_days(period: CollectionPeriod):
    current_day = period.period_start
    while current_day <= period.period_end:
        yield current_day
        current_day += timedelta(days=1)
