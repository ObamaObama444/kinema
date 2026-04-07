from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class ExerciseTechniqueProfile(Base):
    __tablename__ = "exercise_technique_profiles"

    id = mapped_column(Integer, primary_key=True)
    exercise_id = mapped_column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    owner_user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    public_slug = mapped_column(String(160), nullable=False, unique=True, index=True)
    status = mapped_column(String(32), nullable=False)
    motion_family = mapped_column(String(32), nullable=False)
    view_type = mapped_column(String(32), nullable=False)
    source_video_name = mapped_column(String(255), nullable=True)
    source_video_path = mapped_column(Text, nullable=True)
    source_video_meta_json = mapped_column(Text, nullable=True)
    reference_model_json = mapped_column(Text, nullable=False)
    calibration_profile_json = mapped_column(Text, nullable=False)
    latest_test_summary_json = mapped_column(Text, nullable=True)
    published_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), nullable=True)

    exercise = relationship("Exercise", foreign_keys=[exercise_id])
    owner_user = relationship("User", foreign_keys=[owner_user_id])
