from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class EmployeeCategory(str, Enum):
    ADULT = "adult"
    MINOR_STUDENT = "minor_student"
    MINOR_NOT_STUDENT = "minor_not_student"


class DayType(str, Enum):
    WORK = "work"
    DAY_OFF = "day_off"
    VACATION = "vacation"
    HOLIDAY = "holiday"
    UNAVAILABLE = "unavailable"


class SubmissionStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


LEGACY_STATUS_TO_DAY_TYPE = {
    "shift": DayType.WORK,
    "split": DayType.WORK,
    "dayoff": DayType.DAY_OFF,
    "vacation": DayType.VACATION,
    "holiday": DayType.HOLIDAY,
    "unavailable": DayType.UNAVAILABLE,
    "work": DayType.WORK,
    "day_off": DayType.DAY_OFF,
}

DAY_TYPE_TO_STATUS = {
    DayType.WORK: "work",
    DayType.DAY_OFF: "day_off",
    DayType.VACATION: "vacation",
    DayType.HOLIDAY: "holiday",
    DayType.UNAVAILABLE: "unavailable",
}


@dataclass(frozen=True)
class CategoryNorm:
    weekly_hours: float
    daily_hours: float | None
    min_days_off: int
    night_work_forbidden: bool
    overtime_forbidden: bool


CATEGORY_NORMS = {
    EmployeeCategory.ADULT: CategoryNorm(
        weekly_hours=40.0,
        daily_hours=None,
        min_days_off=2,
        night_work_forbidden=False,
        overtime_forbidden=False,
    ),
    EmployeeCategory.MINOR_NOT_STUDENT: CategoryNorm(
        weekly_hours=35.0,
        daily_hours=7.0,
        min_days_off=2,
        night_work_forbidden=True,
        overtime_forbidden=True,
    ),
    EmployeeCategory.MINOR_STUDENT: CategoryNorm(
        weekly_hours=17.5,
        daily_hours=4.0,
        min_days_off=2,
        night_work_forbidden=True,
        overtime_forbidden=True,
    ),
}


DEMO_HOLIDAYS = {
    "2026-05-01": "Праздник весны и труда",
    "2026-05-09": "День Победы",
    "2026-06-12": "День России",
}
