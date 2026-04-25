from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_verified_user, require_role
from db import get_db
from models import CollectionPeriod, ScheduleEntry, User, UserRole
from schemas import ScheduleBulkUpdate, ScheduleDayPayload, ScheduleForUser

router = APIRouter(prefix="/schedules", tags=["schedules"])

def get_current_period(db: Session = Depends(get_db)) -> Optional[CollectionPeriod]:
    return db.query(CollectionPeriod).filter(CollectionPeriod.is_open == True).first()

@router.get("/me", response_model=Dict[date, ScheduleDayPayload])
def get_my_schedule(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db)
    if not current_period:
        return {}  # нет активного периода → пустой график

    entries: List[ScheduleEntry] = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == current_user.id,
            ScheduleEntry.period_id == current_period.id
        )
        .all()
    )
    return {e.day: ScheduleDayPayload(status=e.status, meta=e.meta) for e in entries}

@router.put("/me", response_model=Dict[date, ScheduleDayPayload])
def update_my_schedule(
    payload: ScheduleBulkUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
):
    current_period = get_current_period(db)
    if not current_period:
        raise HTTPException(status_code=400, detail="Нет активного периода сбора")

    # Проверяем, что все даты входят в период
    for d in payload.days.keys():
        if d < current_period.period_start or d > current_period.period_end:
            raise HTTPException(
                status_code=400,
                detail=f"Дата {d} выходит за границы текущего периода"
            )

    # Удаляем все существующие записи пользователя за этот период
    db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id
    ).delete()

    # Добавляем новые записи для дней, которые не empty
    for d, day_payload in payload.days.items():
        # Здесь мы добавляем только те дни, которые есть в payload (они все не empty по логике клиента)
        # На клиенте в payload попадают только не empty дни
        entry = ScheduleEntry(
            user_id=current_user.id,
            period_id=current_period.id,
            day=d,
            status=day_payload.status,
            meta=day_payload.meta,
        )
        db.add(entry)
    db.commit()

    # Возвращаем обновлённые записи
    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.user_id == current_user.id,
        ScheduleEntry.period_id == current_period.id
    ).all()
    return {e.day: ScheduleDayPayload(status=e.status, meta=e.meta) for e in entries}

@router.get("/by-user/{user_id}", response_model=ScheduleForUser)
def get_schedule_for_user(
    user_id: int,
    _: User = Depends(require_role(UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    current_period = get_current_period(db)
    if not current_period:
        # Нет активного периода – возвращаем пустой график
        return ScheduleForUser(user=user, entries={}, vacation_work=None)

    entries: List[ScheduleEntry] = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.user_id == user.id,
            ScheduleEntry.period_id == current_period.id
        )
        .all()
    )
    schedule_map = {e.day: ScheduleDayPayload(status=e.status, meta=e.meta) for e in entries}

    return ScheduleForUser(
        user=user,
        entries=schedule_map,
        vacation_work=None,
    )