from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship, mapped_column

from app.core.database import Base


class WorkoutCheckin(Base):
    __tablename__ = "workout_checkins"
    __table_args__ = (
        UniqueConstraint("user_id", "local_date", name="uq_workout_checkins_user_day"),
    )

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    local_date = mapped_column(Date, nullable=False)
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", backref="workout_checkins")
