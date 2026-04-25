from datetime import date, datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: UserRole
    is_verified: bool
    exp: int


class UserBase(BaseModel):
    external_id: Optional[str] = Field(None, description="External numeric/string identifier")
    full_name: Optional[str] = None
    alliance: Optional[str] = None
    category: Optional[str] = None
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    email: EmailStr
    password: str

    @validator('password')
    def check_password_length(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password too long, must be <= 72 bytes')
        return v


class UserOut(UserBase):
    id: int
    email: Optional[EmailStr] = None
    registered: bool
    is_verified: bool

    class Config:
        from_attributes = True


class UserMe(UserOut):
    pass


class VerificationRequest(BaseModel):
    token: str


class ScheduleDayPayload(BaseModel):
    status: str
    meta: Optional[dict] = None


class ScheduleBulkUpdate(BaseModel):
    # Map of "YYYY-MM-DD" -> complex payload for a day
    days: Dict[date, ScheduleDayPayload]


class ScheduleForUser(BaseModel):
    user: UserOut
    entries: Dict[date, ScheduleDayPayload]
    vacation_work: Optional[dict] = None


class CollectionPeriodOut(BaseModel):
    id: int
    alliance: str
    period_start: date
    period_end: date
    deadline: datetime
    is_open: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionPeriodCreate(BaseModel):
    period_start: date
    period_end: date
    deadline: datetime


class ScheduleTemplateCreate(BaseModel):
    name: str
    work_days: int = Field(..., ge=1, le=7)
    rest_days: int = Field(..., ge=0, le=7)
    shift_start: str
    shift_end: str
    has_break: bool = False
    break_start: Optional[str] = None
    break_end: Optional[str] = None


class ScheduleTemplateOut(BaseModel):
    id: int
    user_id: int
    name: str
    work_days: int
    rest_days: int
    shift_start: str
    shift_end: str
    has_break: bool
    break_start: Optional[str]
    break_end: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

