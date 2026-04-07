from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.favorite import FavoriteItem


def list_favorites_by_type(db: Session, user_id: int, item_type: str) -> list[FavoriteItem]:
    stmt = (
        select(FavoriteItem)
        .where(FavoriteItem.user_id == user_id, FavoriteItem.item_type == item_type)
        .order_by(FavoriteItem.created_at.desc(), FavoriteItem.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def get_favorite(db: Session, user_id: int, item_type: str, item_id: int) -> FavoriteItem | None:
    stmt = select(FavoriteItem).where(
        FavoriteItem.user_id == user_id,
        FavoriteItem.item_type == item_type,
        FavoriteItem.item_id == item_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def add_favorite(db: Session, user_id: int, item_type: str, item_id: int) -> FavoriteItem:
    existing = get_favorite(db, user_id=user_id, item_type=item_type, item_id=item_id)
    if existing is not None:
        return existing

    favorite = FavoriteItem(user_id=user_id, item_type=item_type, item_id=item_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def remove_favorite(db: Session, user_id: int, item_type: str, item_id: int) -> bool:
    stmt = delete(FavoriteItem).where(
        FavoriteItem.user_id == user_id,
        FavoriteItem.item_type == item_type,
        FavoriteItem.item_id == item_id,
    )
    result = db.execute(stmt)
    db.commit()
    return bool(result.rowcount)
