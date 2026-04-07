from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class DailyRecordGoal(Base):
    __tablename__ = "daily_record_goals"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_daily_record_goals_user_date"),
    )

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    local_date = mapped_column(Date, nullable=False, index=True)
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    steps_goal = mapped_column(Integer, nullable=True)
    water_goal_glasses = mapped_column(Integer, nullable=True)
    water_consumed_glasses = mapped_column(Integer, nullable=False, server_default="0")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", backref="daily_record_goals")
