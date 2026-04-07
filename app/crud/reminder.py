from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.reminder import ReminderRule


def list_user_reminders(db: Session, user_id: int) -> list[ReminderRule]:
    stmt = (
        select(ReminderRule)
        .where(ReminderRule.user_id == user_id)
        .order_by(ReminderRule.created_at.desc(), ReminderRule.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_reminder_by_id(db: Session, user_id: int, reminder_id: int) -> ReminderRule | None:
    stmt = select(ReminderRule).where(
        ReminderRule.user_id == user_id,
        ReminderRule.id == reminder_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def delete_reminder(db: Session, user_id: int, reminder_id: int) -> bool:
    stmt = delete(ReminderRule).where(
        ReminderRule.user_id == user_id,
        ReminderRule.id == reminder_id,
    )
    result = db.execute(stmt)
    db.commit()
    return bool(result.rowcount)
