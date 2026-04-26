from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from db import engine


def _has_existing_schema() -> bool:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    app_tables = {
        "users",
        "verification_tokens",
        "collection_periods",
        "schedule_entries",
        "schedule_submissions",
        "schedule_templates",
    }
    return bool(existing_tables & app_tables)


def _has_alembic_version() -> bool:
    inspector = inspect(engine)
    return "alembic_version" in set(inspector.get_table_names())


def main() -> None:
    config = Config("alembic.ini")
    if _has_existing_schema() and not _has_alembic_version():
        command.stamp(config, "head")
        return
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
