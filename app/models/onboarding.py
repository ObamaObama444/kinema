from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class UserOnboarding(Base):
    __tablename__ = "user_onboarding"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    is_completed = mapped_column(Boolean, nullable=False, server_default=text("false"))
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    main_goal = mapped_column(String(64), nullable=True)
    motivation = mapped_column(String(64), nullable=True)
    desired_outcome = mapped_column(String(64), nullable=True)
    focus_area = mapped_column(String(64), nullable=True)
    gender = mapped_column(String(32), nullable=True)
    current_body_shape = mapped_column(Integer, nullable=True)
    target_body_shape = mapped_column(Integer, nullable=True)
    age = mapped_column(Integer, nullable=True)
    height_cm = mapped_column(Integer, nullable=True)
    current_weight_kg = mapped_column(Float, nullable=True)
    target_weight_kg = mapped_column(Float, nullable=True)
    fitness_level = mapped_column(String(32), nullable=True)
    activity_level = mapped_column(String(32), nullable=True)
    goal_pace = mapped_column(String(32), nullable=True)
    training_frequency = mapped_column(Integer, nullable=True)
    calorie_tracking = mapped_column(String(32), nullable=True)
    diet_type = mapped_column(String(32), nullable=True)
    self_image = mapped_column(String(32), nullable=True)
    reminders_enabled = mapped_column(Boolean, nullable=False, server_default=text("false"))
    reminder_time_local = mapped_column(String(5), nullable=True)
    onboarding_version = mapped_column(String(32), nullable=False, server_default="v1")
    interest_tags = mapped_column(Text, nullable=True)
    equipment_tags = mapped_column(Text, nullable=True)
    injury_areas = mapped_column(Text, nullable=True)
    training_days = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        backref=backref("onboarding", uselist=False),
        uselist=False,
    )
