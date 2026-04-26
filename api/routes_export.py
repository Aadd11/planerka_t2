from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from auth import require_role
from constants import UserRole
from db import get_db
from models import CollectionPeriod, ScheduleEntry, User
from schedule_service import get_or_create_submission, normalize_schedule_day, validate_schedule

router = APIRouter(prefix="/export", tags=["export"])


def _resolve_period(db: Session, current_user: User, period_id: int | None) -> CollectionPeriod:
    if period_id is None:
        period = (
            db.query(CollectionPeriod)
            .filter(CollectionPeriod.is_open.is_(True), CollectionPeriod.alliance == current_user.alliance)
            .order_by(CollectionPeriod.created_at.desc())
            .first()
        )
    else:
        period = db.query(CollectionPeriod).filter(CollectionPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    if current_user.role != UserRole.ADMIN.value and period.alliance != current_user.alliance:
        raise HTTPException(status_code=403, detail="Нет доступа к этому периоду")
    return period


def _build_workbook(db: Session, period: CollectionPeriod) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "schedule"
    sheet.append(
        [
            "Группа",
            "ФИО",
            "Email",
            "Категория",
            "Статус отправки",
            "Период",
            "Дата",
            "Тип дня",
            "Интервалы",
            "Комментарий сотрудника",
            "Комментарий руководителя",
            "Комментарий к графику сотрудника",
            "Комментарий к графику руководителя",
            "Суммарные часы",
            "Предупреждения",
        ]
    )

    users = (
        db.query(User)
        .filter(User.alliance == period.alliance, User.role == UserRole.EMPLOYEE.value)
        .order_by(User.full_name.asc())
        .all()
    )
    for user in users:
        entries = (
            db.query(ScheduleEntry)
            .filter(ScheduleEntry.user_id == user.id, ScheduleEntry.period_id == period.id)
            .order_by(ScheduleEntry.day.asc())
            .all()
        )
        submission = get_or_create_submission(db, user.id, period.id)
        validation = validate_schedule(
            period=period,
            days={entry.day: normalize_schedule_day({"status": entry.status, "meta": entry.meta or {}}) for entry in entries},
            employee_category=user.employee_category,
        )
        warning_messages = "; ".join(issue.message for issue in validation.issues if issue.severity.value == "warning")

        if not entries:
            sheet.append(
                [
                    user.alliance,
                    user.full_name,
                    user.email,
                    user.employee_category,
                    submission.status,
                    f"{period.period_start} - {period.period_end}",
                    "",
                    "",
                    "",
                    "",
                    "",
                    submission.employee_comment or "",
                    submission.manager_comment or "",
                    validation.summary.total_hours,
                    warning_messages,
                ]
            )
            continue

        for entry in entries:
            normalized = normalize_schedule_day({"status": entry.status, "meta": entry.meta or {}})
            segments = ", ".join(f'{segment["start"]}-{segment["end"]}' for segment in normalized["segments"])
            sheet.append(
                [
                    user.alliance,
                    user.full_name,
                    user.email,
                    user.employee_category,
                    submission.status,
                    f"{period.period_start} - {period.period_end}",
                    entry.day.isoformat(),
                    normalized["dayType"],
                    segments,
                    normalized["employeeComment"] or "",
                    normalized["managerComment"] or "",
                    submission.employee_comment or "",
                    submission.manager_comment or "",
                    validation.summary.total_hours,
                    warning_messages,
                ]
            )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


@router.get("/schedule", summary="Экспорт расписаний в Excel")
def export_schedule(
    period_id: int | None = Query(default=None, alias="period_id"),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    period = _resolve_period(db, current_user, period_id)
    file_obj = _build_workbook(db, period)
    return StreamingResponse(
        file_obj,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="schedule_{period.alliance}_{period.period_start}_{period.period_end}.xlsx"'
            )
        },
    )
