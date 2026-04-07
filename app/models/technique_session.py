from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class TechniqueSession(Base):
    __tablename__ = "technique_sessions"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = mapped_column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = mapped_column(String(32), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at = mapped_column(DateTime(timezone=True), nullable=True)
    reps_count = mapped_column(Integer, nullable=False, default=0)
    avg_score = mapped_column(Float, nullable=True)
    log_path = mapped_column(Text, nullable=True)

    user = relationship(
        "User",
        backref=backref("technique_sessions", order_by="TechniqueSession.id.desc()"),
    )
    exercise = relationship(
        "Exercise",
        backref=backref("technique_sessions", order_by="TechniqueSession.id.desc()"),
    )
