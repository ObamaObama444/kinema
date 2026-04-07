from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification import Notification


def list_notifications(db: Session, user_id: int, limit: int = 30) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def list_all_notifications(db: Session, user_id: int) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def count_unread_notifications(db: Session, user_id: int) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    return int(db.execute(stmt).scalar_one())


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    action_type: str | None = None,
    action_label: str | None = None,
    action_payload: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title.strip(),
        message=message.strip(),
        action_type=action_type.strip() if isinstance(action_type, str) and action_type.strip() else None,
        action_label=action_label.strip() if isinstance(action_label, str) and action_label.strip() else None,
        action_payload=action_payload.strip() if isinstance(action_payload, str) and action_payload.strip() else None,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_notification_safe(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    action_type: str | None = None,
    action_label: str | None = None,
    action_payload: str | None = None,
) -> bool:
    try:
        create_notification(
            db,
            user_id=user_id,
            title=title,
            message=message,
            action_type=action_type,
            action_label=action_label,
            action_payload=action_payload,
        )
        return True
    except SQLAlchemyError:
        db.rollback()
        return False


def get_notification_by_id(db: Session, user_id: int, notification_id: int) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def mark_all_notifications_as_read(db: Session, user_id: int) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)


def mark_notification_as_read(db: Session, user_id: int, notification_id: int) -> bool:
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return bool(result.rowcount)


def delete_all_notifications(db: Session, user_id: int) -> int:
    stmt = delete(Notification).where(Notification.user_id == user_id)
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)
