from __future__ import annotations

from datetime import date, datetime, timezone

from auth import get_password_hash
from db import Base, SessionLocal, engine
from models import CollectionPeriod, ScheduleEntry, ScheduleSubmission, User


Base.metadata.create_all(bind=engine)


def upsert_user(session, **kwargs):
    user = session.query(User).filter(User.email == kwargs["email"]).first()
    if not user:
        user = User(**kwargs)
        session.add(user)
    else:
        for key, value in kwargs.items():
            setattr(user, key, value)
    session.flush()
    return user


def upsert_period(session, **kwargs):
    period = (
        session.query(CollectionPeriod)
        .filter(
            CollectionPeriod.name == kwargs["name"],
            CollectionPeriod.alliance == kwargs["alliance"],
        )
        .first()
    )
    if not period:
        period = CollectionPeriod(**kwargs)
        session.add(period)
    else:
        for key, value in kwargs.items():
            setattr(period, key, value)
    session.flush()
    return period


def replace_schedule(session, *, user: User, period: CollectionPeriod, entries: dict[str, dict], submission_status: str, employee_comment: str = "", manager_comment: str = ""):
    session.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == user.id,
        ScheduleEntry.period_id == period.id,
    ).delete()
    session.query(ScheduleSubmission).filter(
        ScheduleSubmission.user_id == user.id,
        ScheduleSubmission.period_id == period.id,
    ).delete()

    for day, payload in entries.items():
        session.add(
            ScheduleEntry(
                user_id=user.id,
                period_id=period.id,
                day=date.fromisoformat(day),
                status=payload["dayType"],
                meta=payload,
            )
        )
    session.add(
        ScheduleSubmission(
            user_id=user.id,
            period_id=period.id,
            status=submission_status,
            submitted_at=datetime.now(timezone.utc) if submission_status == "submitted" else None,
            employee_comment=employee_comment,
            manager_comment=manager_comment,
        )
    )


def main():
    session = SessionLocal()
    try:
        admin = upsert_user(
            session,
            email="admin@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=True,
            full_name="T2 Admin",
            alliance="Retail East",
            role="admin",
            employee_category="adult",
            weekly_norm_hours=40.0,
        )
        manager = upsert_user(
            session,
            email="manager@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=True,
            full_name="Elena Manager",
            alliance="Retail East",
            role="manager",
            employee_category="adult",
            weekly_norm_hours=40.0,
        )
        employee_ok = upsert_user(
            session,
            email="employee1@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=True,
            full_name="Anna Schedule",
            alliance="Retail East",
            role="employee",
            employee_category="adult",
            weekly_norm_hours=40.0,
        )
        employee_issue = upsert_user(
            session,
            email="employee2@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=True,
            full_name="Maksim Overtime",
            alliance="Retail East",
            role="employee",
            employee_category="minor_not_student",
            weekly_norm_hours=35.0,
        )
        waiting = upsert_user(
            session,
            email="newbie@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=False,
            full_name="Pending User",
            alliance="Retail East",
            role="employee",
            employee_category="adult",
            weekly_norm_hours=40.0,
        )
        foreign_employee = upsert_user(
            session,
            email="west.employee@t2.demo",
            password_hash=get_password_hash("password123"),
            registered=True,
            is_verified=True,
            full_name="Nikita West",
            alliance="Retail West",
            role="employee",
            employee_category="adult",
            weekly_norm_hours=40.0,
        )

        east_period = upsert_period(
            session,
            name="Май 2026",
            alliance="Retail East",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 14),
            deadline=datetime(2026, 4, 30, 18, 0, 0, tzinfo=timezone.utc),
            is_open=True,
        )
        west_period = upsert_period(
            session,
            name="Май 2026",
            alliance="Retail West",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 14),
            deadline=datetime(2026, 4, 30, 18, 0, 0, tzinfo=timezone.utc),
            is_open=True,
        )

        replace_schedule(
            session,
            user=employee_ok,
            period=east_period,
            submission_status="submitted",
            employee_comment="Предпочитаю смены в первой половине дня.",
            manager_comment="Принято, покрытие по утрам подходит.",
            entries={
                "2026-05-04": {"dayType": "work", "segments": [{"start": "09:00", "end": "13:00"}, {"start": "14:00", "end": "18:00"}], "employeeComment": "Готова закрывать пик до обеда.", "managerComment": "Ок"},
                "2026-05-05": {"dayType": "work", "segments": [{"start": "10:00", "end": "19:00"}], "employeeComment": "", "managerComment": ""},
                "2026-05-06": {"dayType": "day_off", "segments": [], "employeeComment": "", "managerComment": ""},
                "2026-05-07": {"dayType": "holiday", "segments": [], "employeeComment": "", "managerComment": ""},
                "2026-05-08": {"dayType": "vacation", "segments": [], "employeeComment": "Часть отпуска", "managerComment": ""},
            },
        )
        replace_schedule(
            session,
            user=employee_issue,
            period=east_period,
            submission_status="draft",
            employee_comment="Нужна проверка по нормам.",
            entries={
                "2026-05-04": {"dayType": "work", "segments": [{"start": "09:00", "end": "17:00"}], "employeeComment": "", "managerComment": ""},
                "2026-05-05": {"dayType": "work", "segments": [{"start": "09:00", "end": "17:00"}], "employeeComment": "", "managerComment": ""},
                "2026-05-06": {"dayType": "work", "segments": [{"start": "09:00", "end": "17:00"}], "employeeComment": "", "managerComment": ""},
                "2026-05-07": {"dayType": "work", "segments": [{"start": "21:00", "end": "23:30"}], "employeeComment": "Понимаю, что тут будет ошибка.", "managerComment": ""},
            },
        )
        replace_schedule(
            session,
            user=foreign_employee,
            period=west_period,
            submission_status="submitted",
            entries={
                "2026-05-05": {"dayType": "work", "segments": [{"start": "11:00", "end": "20:00"}], "employeeComment": "", "managerComment": ""},
                "2026-05-06": {"dayType": "day_off", "segments": [], "employeeComment": "", "managerComment": ""},
            },
        )

        session.commit()
        print("Seed complete.")
        print("Admin: admin@t2.demo / password123")
        print("Manager: manager@t2.demo / password123")
        print("Employee: employee1@t2.demo / password123")
        print("Employee with issues: employee2@t2.demo / password123")
        print("Pending verification: newbie@t2.demo / password123")
    finally:
        session.close()


if __name__ == "__main__":
    main()
