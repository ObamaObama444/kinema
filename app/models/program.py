from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class Program(Base):
    __tablename__ = "programs"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(180), nullable=False)
    description = mapped_column(Text, nullable=False)
    level = mapped_column(String(32), nullable=False)
    duration_weeks = mapped_column(Integer, nullable=False)
    owner_user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    program_exercises = relationship(
        "ProgramExercise",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramExercise.order",
    )
    workout_sessions = relationship(
        "WorkoutSession",
        back_populates="program",
        cascade="all, delete-orphan",
    )
    owner_user = relationship("User", foreign_keys=[owner_user_id])
