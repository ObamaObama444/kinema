from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    height_cm = mapped_column(Integer, nullable=True)
    weight_kg = mapped_column(Integer, nullable=True)
    age = mapped_column(Integer, nullable=True)
    level = mapped_column(String(32), nullable=True)
    active_program_id = mapped_column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workouts_per_week = mapped_column(Integer, nullable=True)

    user = relationship(
        "User",
        backref=backref("profile", uselist=False),
        uselist=False,
    )
    active_program = relationship(
        "Program",
        foreign_keys=[active_program_id],
        backref=backref("active_profiles"),
    )
