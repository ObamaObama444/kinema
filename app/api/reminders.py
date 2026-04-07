import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.core.progress import resolve_timezone_name
from app.crud.onboarding import get_user_onboarding
from app.crud.reminder import delete_reminder, get_reminder_by_id, list_user_reminders
from app.crud.settings import get_or_create_user_settings
from app.models.reminder import ReminderRule
from app.models.user import User
from app.schemas.reminder import (
    ReminderRuleCreateRequest,
    ReminderRuleListResponse,
    ReminderRulePatchRequest,
    ReminderRuleResponse,
)

router = APIRouter(tags=["reminders"])


def _training_days_from_onboarding(db: Session, user_id: int) -> list[str]:
    onboarding = get_user_onboarding(db, user_id)
    if onboarding is None or not onboarding.training_days:
        return []
    try:
        parsed = json.loads(onboarding.training_days)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip().lower() for item in parsed if str(item).strip()]


def _reminder_status(rule: ReminderRule, current_user: User) -> str:
    if not current_user.telegram_user_id:
        return "needs_link"
    if not rule.enabled:
        return "disabled"
    return "active"


def _serialize_reminder(rule: ReminderRule, current_user: User) -> ReminderRuleResponse:
    days: list[str] = []
    if rule.days_json:
        try:
            parsed = json.loads(rule.days_json)
            if isinstance(parsed, list):
                days = [str(item).strip().lower() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            days = []
    return ReminderRuleResponse(
        id=rule.id,
        kind=rule.kind,
        title=rule.title,
        message=rule.message,
        time_local=rule.time_local,
        days=days,
        enabled=rule.enabled,
        timezone=rule.timezone,
        last_sent_at=rule.last_sent_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
        status=_reminder_status(rule, current_user),
    )


@router.get("/api/profile/reminders", response_model=ReminderRuleListResponse)
def get_profile_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderRuleListResponse:
    items = list_user_reminders(db, current_user.id)
    return ReminderRuleListResponse(items=[_serialize_reminder(item, current_user) for item in items])


@router.post("/api/profile/reminders", response_model=ReminderRuleResponse, status_code=status.HTTP_201_CREATED)
def create_profile_reminder(
    payload: ReminderRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderRuleResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    reminder_days = list(payload.days or [])
    if payload.kind == "workout" and not reminder_days:
        reminder_days = _training_days_from_onboarding(db, current_user.id)

    rule = ReminderRule(
        user_id=current_user.id,
        kind=payload.kind,
        title=payload.title,
        message=payload.message,
        time_local=payload.time_local,
        days_json=json.dumps(reminder_days, ensure_ascii=True),
        enabled=payload.enabled,
        timezone=resolve_timezone_name(payload.timezone or current_settings.timezone),
    )
    try:
        db.add(rule)
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить напоминание.",
        ) from exc
    return _serialize_reminder(rule, current_user)


@router.patch("/api/profile/reminders/{reminder_id}", response_model=ReminderRuleResponse)
def patch_profile_reminder(
    reminder_id: int,
    payload: ReminderRulePatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderRuleResponse:
    rule = get_reminder_by_id(db, current_user.id, reminder_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Напоминание не найдено.")

    if payload.title is not None:
        rule.title = payload.title
    if payload.message is not None:
        rule.message = payload.message
    if payload.time_local is not None:
        rule.time_local = payload.time_local
    if payload.days is not None:
        reminder_days = list(payload.days or [])
        if rule.kind == "workout" and not reminder_days:
            reminder_days = _training_days_from_onboarding(db, current_user.id)
        rule.days_json = json.dumps(reminder_days, ensure_ascii=True)
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.timezone is not None:
        rule.timezone = resolve_timezone_name(payload.timezone)

    try:
        db.add(rule)
        db.commit()
        db.refresh(rule)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить напоминание.",
        ) from exc
    return _serialize_reminder(rule, current_user)


@router.delete("/api/profile/reminders/{reminder_id}", response_model=dict[str, bool])
def delete_profile_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    removed = delete_reminder(db, current_user.id, reminder_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Напоминание не найдено.")
    return {"ok": True}
