import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(max_length=128)
    name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Укажите корректный email.")
        return email

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value
        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов.")
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный для bcrypt (максимум 72 байта).")
        return password


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Укажите корректный email.")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = value
        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов.")
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный для bcrypt (максимум 72 байта).")
        return password


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    name: str | None
    avatar_url: str | None
    created_at: datetime
