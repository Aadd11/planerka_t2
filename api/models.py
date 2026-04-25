from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import JSON as SAJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db import Base


json_type = SAJSON().with_variant(JSONB, "postgresql")


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(32), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    registered = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    full_name = Column(Text, nullable=False)
    alliance = Column(Text, nullable=False, index=True)
    role = Column(String(32), default="employee", nullable=False, index=True)
    employee_category = Column(String(64), default="adult", nullable=False)
    weekly_norm_hours = Column(Float, nullable=True)

    schedules = relationship("ScheduleEntry", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship(
        "VerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    templates = relationship("ScheduleTemplate", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship(
        "ScheduleSubmission",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="verification_tokens")


class CollectionPeriod(TimestampMixin, Base):
    __tablename__ = "collection_periods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    alliance = Column(Text, nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    is_open = Column(Boolean, default=True, nullable=False, index=True)

    schedules = relationship("ScheduleEntry", back_populates="period", cascade="all, delete-orphan")
    submissions = relationship(
        "ScheduleSubmission",
        back_populates="period",
        cascade="all, delete-orphan",
    )


class ScheduleEntry(TimestampMixin, Base):
    __tablename__ = "schedule_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_id = Column(Integer, ForeignKey("collection_periods.id", ondelete="CASCADE"), nullable=False)
    day = Column(Date, nullable=False)
    status = Column(String(128), nullable=False)
    meta = Column(json_type, nullable=False, default=dict)

    user = relationship("User", back_populates="schedules")
    period = relationship("CollectionPeriod", back_populates="schedules")

    __table_args__ = (
        UniqueConstraint("user_id", "period_id", "day", name="uq_schedule_user_period_day"),
    )


class ScheduleSubmission(TimestampMixin, Base):
    __tablename__ = "schedule_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_id = Column(Integer, ForeignKey("collection_periods.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    employee_comment = Column(Text, nullable=True)
    manager_comment = Column(Text, nullable=True)

    user = relationship("User", back_populates="submissions")
    period = relationship("CollectionPeriod", back_populates="submissions")

    __table_args__ = (
        UniqueConstraint("user_id", "period_id", name="uq_submission_user_period"),
    )


class ScheduleTemplate(TimestampMixin, Base):
    __tablename__ = "schedule_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    work_days = Column(Integer, nullable=False)
    rest_days = Column(Integer, nullable=False)
    shift_start = Column(String(5), nullable=False)
    shift_end = Column(String(5), nullable=False)
    has_break = Column(Boolean, default=False, nullable=False)
    break_start = Column(String(5), nullable=True)
    break_end = Column(String(5), nullable=True)

    user = relationship("User", back_populates="templates")
