from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.weight_entry import WeightEntry


def list_weight_entries(db: Session, user_id: int) -> list[WeightEntry]:
    stmt = (
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .order_by(WeightEntry.created_at.asc(), WeightEntry.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_weight_entry_for_day(db: Session, user_id: int, local_date: date) -> WeightEntry | None:
    stmt = select(WeightEntry).where(
        WeightEntry.user_id == user_id,
        WeightEntry.recorded_on_local_date == local_date,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_weight_entry(db: Session, user_id: int) -> WeightEntry | None:
    stmt = (
        select(WeightEntry)
        .where(WeightEntry.user_id == user_id)
        .order_by(WeightEntry.created_at.desc(), WeightEntry.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()
