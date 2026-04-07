from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True)
    email = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash = mapped_column(String(255), nullable=False)
    name = mapped_column(String(120), nullable=True)
    avatar_url = mapped_column(String(255), nullable=True)
    telegram_user_id = mapped_column(String(64), unique=True, index=True, nullable=True)
    telegram_username = mapped_column(String(120), nullable=True)
    telegram_first_name = mapped_column(String(120), nullable=True)
    telegram_linked_at = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_last_seen_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
