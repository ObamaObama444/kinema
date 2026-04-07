from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class VitalMeasurement(Base):
    __tablename__ = "vital_measurements"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    local_date = mapped_column(Date, nullable=False, index=True)
    metric_type = mapped_column(String(24), nullable=False, index=True)
    pulse_bpm = mapped_column(Integer, nullable=True)
    systolic_mmhg = mapped_column(Integer, nullable=True)
    diastolic_mmhg = mapped_column(Integer, nullable=True)
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    recorded_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", backref="vital_measurements")
