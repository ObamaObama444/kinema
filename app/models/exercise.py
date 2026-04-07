from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(180), nullable=False)
    description = mapped_column(Text, nullable=False)
    equipment = mapped_column(String(180), nullable=True)
    primary_muscles = mapped_column(String(180), nullable=True)
    difficulty = mapped_column(String(32), nullable=False)

    program_exercises = relationship(
        "ProgramExercise",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    workout_set_logs = relationship(
        "WorkoutSetLog",
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
