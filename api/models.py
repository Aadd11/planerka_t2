import enum
from datetime import datetime, date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(32), unique=True, index=True, nullable=True)  # e.g. "6505365461"
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)

    registered = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    full_name = Column(Text, nullable=True)
    alliance = Column(Text, nullable=True)
    category = Column(String(64), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    schedules = relationship("ScheduleEntry", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship(
        "VerificationToken", back_populates="user", cascade="all, delete-orphan"
    )
    templates = relationship("ScheduleTemplate", back_populates="user", cascade="all, delete-orphan")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="verification_tokens")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_id = Column(Integer, ForeignKey("collection_periods.id", ondelete="CASCADE"), nullable=False)  # новое поле
    day = Column(Date, nullable=False)
    status = Column(String(128), nullable=False)
    meta = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="schedules")
    period = relationship("CollectionPeriod")

    __table_args__ = (UniqueConstraint("user_id", "period_id", "day", name="uq_schedule_user_period_day"),)


class ScheduleTemplate(Base):
    __tablename__ = "schedule_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)  # "5/2, 09:00-18:15"
    work_days = Column(Integer, nullable=False)  # 5
    rest_days = Column(Integer, nullable=False)  # 2
    shift_start = Column(String(5), nullable=False)  # "09:00"
    shift_end = Column(String(5), nullable=False)  # "18:15"
    has_break = Column(Boolean, default=False, nullable=False)
    break_start = Column(String(5), nullable=True)  # "14:30"
    break_end = Column(String(5), nullable=True)  # "17:00"

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="templates")


class CollectionPeriod(Base):
    __tablename__ = "collection_periods"

    id = Column(Integer, primary_key=True, index=True)
    alliance = Column(Text, nullable=False, index=True)  # привязка к альянсу
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    is_open = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

