from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class ProgramExercise(Base):
    __tablename__ = "program_exercises"

    id = mapped_column(Integer, primary_key=True)
    program_id = mapped_column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id = mapped_column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order = mapped_column(Integer, nullable=False)
    sets = mapped_column(Integer, nullable=False)
    reps = mapped_column(Integer, nullable=False)
    rest_sec = mapped_column(Integer, nullable=False)
    tempo = mapped_column(String(40), nullable=False)

    program = relationship("Program", back_populates="program_exercises")
    exercise = relationship("Exercise", back_populates="program_exercises")
