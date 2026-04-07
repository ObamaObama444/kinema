from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = mapped_column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at = mapped_column(DateTime(timezone=True), nullable=True)
    status = mapped_column(String(32), nullable=False)

    user = relationship(
        "User",
        backref=backref("workout_sessions", order_by="WorkoutSession.id.desc()"),
    )
    program = relationship("Program", back_populates="workout_sessions")
    set_logs = relationship(
        "WorkoutSetLog",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkoutSetLog.set_number",
    )


class WorkoutSetLog(Base):
    __tablename__ = "workout_set_logs"

    id = mapped_column(Integer, primary_key=True)
    session_id = mapped_column(
        Integer,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = mapped_column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_number = mapped_column(Integer, nullable=False)
    reps_planned = mapped_column(Integer, nullable=False)
    reps_done = mapped_column(Integer, nullable=True)
    form_score_mock = mapped_column(Integer, nullable=True)  # MOCK
    notes_mock = mapped_column(Text, nullable=True)  # MOCK

    session = relationship("WorkoutSession", back_populates="set_logs")
    exercise = relationship("Exercise", back_populates="workout_set_logs")
