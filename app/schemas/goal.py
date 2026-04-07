from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ALLOWED_GOAL_TYPES = {"weight_loss", "muscle_gain", "endurance"}


class GoalCreateRequest(BaseModel):
    goal_type: str = Field(max_length=64)
    target_value: str = Field(max_length=255)

    @field_validator("goal_type")
    @classmethod
    def validate_goal_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _ALLOWED_GOAL_TYPES:
            raise ValueError("Тип цели должен быть: weight_loss, muscle_gain или endurance.")
        return normalized

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Укажите желаемый результат более подробно.")
        return normalized


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    goal_type: str
    target_value: str
    created_at: datetime
