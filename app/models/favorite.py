from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship, mapped_column

from app.core.database import Base


class FavoriteItem(Base):
    __tablename__ = "favorite_items"
    __table_args__ = (
        UniqueConstraint("user_id", "item_type", "item_id", name="uq_favorite_items_user_item"),
    )

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type = mapped_column(String(32), nullable=False)
    item_id = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", backref="favorite_items")
