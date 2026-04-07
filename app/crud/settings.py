from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user_settings import UserSettings


def get_user_settings(db: Session, user_id: int) -> UserSettings | None:
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_or_create_user_settings(db: Session, user_id: int) -> UserSettings:
    current = get_user_settings(db, user_id)
    if current is not None:
        return current
    current = UserSettings(user_id=user_id, timezone=settings.default_timezone)
    db.add(current)
    db.flush()
    return current
