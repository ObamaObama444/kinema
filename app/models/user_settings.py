from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import backref, mapped_column, relationship

from app.core.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    theme_preference = mapped_column(String(16), nullable=False, server_default="system")
    language = mapped_column(String(8), nullable=False, server_default="ru")
    weight_unit = mapped_column(String(8), nullable=False, server_default="kg")
    height_unit = mapped_column(String(8), nullable=False, server_default="cm")
    timezone = mapped_column(String(64), nullable=False, server_default="UTC")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship(
        "User",
        backref=backref("settings", uselist=False),
        uselist=False,
    )
