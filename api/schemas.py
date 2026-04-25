from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from constants import DayType, EmployeeCategory, IssueSeverity, SubmissionStatus, UserRole


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class Token(ApiModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(ApiModel):
    sub: str
    role: str
    is_verified: bool
    exp: int


class UserBase(ApiModel):
    external_id: str | None = None
    full_name: str
    alliance: str
    employee_category: EmployeeCategory = Field(default=EmployeeCategory.ADULT, alias="employeeCategory")
    role: UserRole = UserRole.EMPLOYEE


class UserCreate(UserBase):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password too long, must be <= 72 bytes")
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class UserOut(UserBase):
    id: int
    email: EmailStr
    registered: bool
    is_verified: bool = Field(alias="isVerified")
    weekly_norm_hours: float | None = Field(default=None, alias="weeklyNormHours")


class UserMe(UserOut):
    pass


class VerificationRequest(ApiModel):
    token: str


class AdminRoleUpdate(ApiModel):
    role: UserRole


class AdminAllianceUpdate(ApiModel):
    alliance: str


class TimeSegment(ApiModel):
    start: str
    end: str


class ScheduleDayPayload(ApiModel):
    status: str | None = None
    day_type: DayType | None = Field(default=None, alias="dayType")
    segments: list[TimeSegment] = Field(default_factory=list)
    employee_comment: str | None = Field(default=None, alias="employeeComment")
    manager_comment: str | None = Field(default=None, alias="managerComment")
    meta: dict[str, Any] | None = None


class ScheduleBulkUpdate(ApiModel):
    days: dict[dt.date, ScheduleDayPayload]
    employee_comment: str | None = Field(default=None, alias="employeeComment")


class ValidationIssue(ApiModel):
    severity: IssueSeverity
    code: str
    date: dt.date | None
    message: str


class ValidationSummary(ApiModel):
    total_hours: float = Field(alias="totalHours")
    weekly_hours: dict[str, float] = Field(alias="weeklyHours")
    days_off_count: dict[str, int] = Field(alias="daysOffCount")


class ScheduleValidationResponse(ApiModel):
    is_valid: bool = Field(alias="isValid")
    summary: ValidationSummary
    issues: list[ValidationIssue]


class ScheduleValidateRequest(ApiModel):
    period_id: int | None = Field(default=None, alias="periodId")
    days: dict[dt.date, ScheduleDayPayload]
    employee_category: EmployeeCategory | None = Field(default=None, alias="employeeCategory")


class SubmissionOut(ApiModel):
    id: int
    status: SubmissionStatus
    submitted_at: dt.datetime | None = Field(alias="submittedAt")
    employee_comment: str | None = Field(alias="employeeComment")
    manager_comment: str | None = Field(alias="managerComment")
    period_id: int = Field(alias="periodId")
    user_id: int = Field(alias="userId")


class CollectionPeriodOut(ApiModel):
    id: int
    name: str
    alliance: str
    period_start: dt.date = Field(alias="periodStart")
    period_end: dt.date = Field(alias="periodEnd")
    deadline: dt.datetime
    is_open: bool = Field(alias="isOpen")
    holidays: dict[str, str] = Field(default_factory=dict)
    created_at: dt.datetime = Field(alias="createdAt")
    updated_at: dt.datetime = Field(alias="updatedAt")


class CollectionPeriodCreate(ApiModel):
    name: str
    alliance: str | None = None
    period_start: dt.date = Field(alias="periodStart")
    period_end: dt.date = Field(alias="periodEnd")
    deadline: dt.datetime

    @model_validator(mode="after")
    def validate_dates(self) -> "CollectionPeriodCreate":
        if self.period_end < self.period_start:
            raise ValueError("periodEnd must be greater than or equal to periodStart")
        return self


class ScheduleTemplateCreate(ApiModel):
    name: str
    work_days: int = Field(alias="workDays", ge=1, le=7)
    rest_days: int = Field(alias="restDays", ge=0, le=7)
    shift_start: str = Field(alias="shiftStart")
    shift_end: str = Field(alias="shiftEnd")
    has_break: bool = Field(default=False, alias="hasBreak")
    break_start: str | None = Field(default=None, alias="breakStart")
    break_end: str | None = Field(default=None, alias="breakEnd")


class ScheduleTemplateOut(ApiModel):
    id: int
    user_id: int = Field(alias="userId")
    name: str
    work_days: int = Field(alias="workDays")
    rest_days: int = Field(alias="restDays")
    shift_start: str = Field(alias="shiftStart")
    shift_end: str = Field(alias="shiftEnd")
    has_break: bool = Field(alias="hasBreak")
    break_start: str | None = Field(alias="breakStart")
    break_end: str | None = Field(alias="breakEnd")
    created_at: dt.datetime = Field(alias="createdAt")
    updated_at: dt.datetime = Field(alias="updatedAt")


class ScheduleBundleOut(ApiModel):
    user: UserOut
    period: CollectionPeriodOut
    submission: SubmissionOut
    entries: dict[dt.date, ScheduleDayPayload]
    validation: ScheduleValidationResponse


class ManagerCommentCreate(ApiModel):
    user_id: int = Field(alias="userId")
    period_id: int = Field(alias="periodId")
    date: dt.date | None = None
    comment: str


class ManagerCommentsOut(ApiModel):
    user_id: int = Field(alias="userId")
    period_id: int = Field(alias="periodId")
    schedule_comment: str | None = Field(alias="scheduleComment")
    day_comments: dict[dt.date, str] = Field(alias="dayComments")


class ManagerEmployeeSchedule(ApiModel):
    user: UserOut
    submission: SubmissionOut
    entries: dict[dt.date, ScheduleDayPayload]
    validation: ScheduleValidationResponse


class ManagerSchedulesOut(ApiModel):
    period: CollectionPeriodOut
    items: list[ManagerEmployeeSchedule]


class CoverageBucket(ApiModel):
    hour: str
    count: int
    users: list[str]


class CoverageResponse(ApiModel):
    day: dt.date
    period_id: int = Field(alias="periodId")
    buckets: list[CoverageBucket]
