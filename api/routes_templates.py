from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import get_current_verified_user
from db import get_db
from models import ScheduleTemplate, User
from schemas import ScheduleTemplateCreate, ScheduleTemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=List[ScheduleTemplateOut])
def get_my_templates(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    templates = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.user_id == current_user.id
    ).order_by(ScheduleTemplate.created_at.desc()).all()
    return templates


@router.post("", response_model=ScheduleTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: ScheduleTemplateCreate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    template = ScheduleTemplate(
        user_id=current_user.id,
        name=payload.name,
        work_days=payload.work_days,
        rest_days=payload.rest_days,
        shift_start=payload.shift_start,
        shift_end=payload.shift_end,
        has_break=payload.has_break,
        break_start=payload.break_start,
        break_end=payload.break_end
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    template = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.id == template_id,
        ScheduleTemplate.user_id == current_user.id
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    db.delete(template)
    db.commit()
    return None
