from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import relationship, mapped_column

from app.core.database import Base


class ReminderRule(Base):
    __tablename__ = "reminder_rules"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = mapped_column(String(32), nullable=False)
    title = mapped_column(String(140), nullable=False)
    message = mapped_column(String(500), nullable=False)
    time_local = mapped_column(String(5), nullable=False)
    days_json = mapped_column(Text, nullable=True)
    enabled = mapped_column(Boolean, nullable=False, server_default=text("true"))
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    last_sent_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", backref="reminder_rules")
