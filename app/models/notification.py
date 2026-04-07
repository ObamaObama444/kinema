from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import mapped_column, relationship

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = mapped_column(String(140), nullable=False)
    message = mapped_column(String(500), nullable=False)
    action_type = mapped_column(String(64), nullable=True)
    action_label = mapped_column(String(140), nullable=True)
    action_payload = mapped_column(Text, nullable=True)
    is_read = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", backref="notifications")
