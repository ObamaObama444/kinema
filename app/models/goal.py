from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    goal_type = mapped_column(String(64), nullable=False)
    target_value = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship(
        "User",
        backref=backref("goal", uselist=False),
        uselist=False,
    )
