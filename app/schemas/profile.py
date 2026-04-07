from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.goal import GoalResponse
from app.schemas.program import ActiveProgramSummary

_ALLOWED_LEVELS = {"beginner", "intermediate", "advanced"}


class ProfileUpdateRequest(BaseModel):
    height_cm: int | None = Field(default=None, ge=100, le=260)
    weight_kg: int | None = Field(default=None, ge=25, le=350)
    age: int | None = Field(default=None, ge=10, le=110)
    level: str | None = Field(default=None, max_length=32)

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None

        if normalized not in _ALLOWED_LEVELS:
            raise ValueError("Уровень должен быть: beginner, intermediate или advanced.")
        return normalized


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int | None = None
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    height_cm: int | None = None
    weight_kg: int | None = None
    age: int | None = None
    level: str | None = None
    active_program_id: int | None = None
    workouts_per_week: int | None = None
    telegram_linked: bool = False
    telegram_user_id: str | None = None
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    current_goal: GoalResponse | None = None
    active_program: ActiveProgramSummary | None = None


class AccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None
    name: str | None
    avatar_url: str | None
