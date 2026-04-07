from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship, mapped_column

from app.core.database import Base


class WeightEntry(Base):
    __tablename__ = "weight_entries"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weight_kg = mapped_column(Float, nullable=False)
    recorded_on_local_date = mapped_column(Date, nullable=False)
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", backref="weight_entries")
