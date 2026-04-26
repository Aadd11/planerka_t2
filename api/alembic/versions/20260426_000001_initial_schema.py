from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260426_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("registered", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("alliance", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="employee"),
        sa.Column("employee_category", sa.String(length=64), nullable=False, server_default="adult"),
        sa.Column("weekly_norm_hours", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_external_id", "users", ["external_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_alliance", "users", ["alliance"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_verification_tokens_id", "verification_tokens", ["id"])
    op.create_index("ix_verification_tokens_token", "verification_tokens", ["token"])

    op.create_table(
        "collection_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("alliance", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_collection_periods_id", "collection_periods", ["id"])
    op.create_index("ix_collection_periods_alliance", "collection_periods", ["alliance"])
    op.create_index("ix_collection_periods_is_open", "collection_periods", ["is_open"])
    op.create_index(
        "uq_collection_period_open_alliance",
        "collection_periods",
        ["alliance"],
        unique=True,
        postgresql_where=sa.text("is_open = true"),
    )

    op.create_table(
        "schedule_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("collection_periods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "period_id", "day", name="uq_schedule_user_period_day"),
    )
    op.create_index("ix_schedule_entries_id", "schedule_entries", ["id"])

    op.create_table(
        "schedule_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_id", sa.Integer(), sa.ForeignKey("collection_periods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employee_comment", sa.Text(), nullable=True),
        sa.Column("manager_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("user_id", "period_id", name="uq_submission_user_period"),
    )
    op.create_index("ix_schedule_submissions_id", "schedule_submissions", ["id"])

    op.create_table(
        "schedule_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("work_days", sa.Integer(), nullable=False),
        sa.Column("rest_days", sa.Integer(), nullable=False),
        sa.Column("shift_start", sa.String(length=5), nullable=False),
        sa.Column("shift_end", sa.String(length=5), nullable=False),
        sa.Column("has_break", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("break_start", sa.String(length=5), nullable=True),
        sa.Column("break_end", sa.String(length=5), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_schedule_templates_id", "schedule_templates", ["id"])


def downgrade() -> None:
    op.drop_index("ix_schedule_templates_id", table_name="schedule_templates")
    op.drop_table("schedule_templates")
    op.drop_index("ix_schedule_submissions_id", table_name="schedule_submissions")
    op.drop_table("schedule_submissions")
    op.drop_index("ix_schedule_entries_id", table_name="schedule_entries")
    op.drop_table("schedule_entries")
    op.drop_index("uq_collection_period_open_alliance", table_name="collection_periods")
    op.drop_index("ix_collection_periods_is_open", table_name="collection_periods")
    op.drop_index("ix_collection_periods_alliance", table_name="collection_periods")
    op.drop_index("ix_collection_periods_id", table_name="collection_periods")
    op.drop_table("collection_periods")
    op.drop_index("ix_verification_tokens_token", table_name="verification_tokens")
    op.drop_index("ix_verification_tokens_id", table_name="verification_tokens")
    op.drop_table("verification_tokens")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_alliance", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
