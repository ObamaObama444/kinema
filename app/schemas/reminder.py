from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_REMINDER_KIND_VALUES = {"workout", "water", "custom"}
_TRAINING_DAY_VALUES = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def _normalize_time(value: str) -> str:
    normalized = value.strip()
    parts = normalized.split(":")
    if len(parts) != 2:
        raise ValueError("Время должно быть в формате HH:MM.")
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError as exc:
        raise ValueError("Время должно быть в формате HH:MM.") from exc
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        raise ValueError("Время должно быть в формате HH:MM.")
    return f"{hours:02d}:{minutes:02d}"


def _normalize_days(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    normalized_items: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip().lower()
        if not normalized:
            continue
        if normalized not in _TRAINING_DAY_VALUES:
            raise ValueError("Дни могут быть только mon..sun.")
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_items.append(normalized)
    return normalized_items


class ReminderRuleBaseRequest(BaseModel):
    kind: str = Field(max_length=32)
    title: str = Field(min_length=1, max_length=140)
    message: str = Field(min_length=1, max_length=500)
    time_local: str
    days: list[str] = Field(default_factory=list, max_length=7)
    enabled: bool = True
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in _REMINDER_KIND_VALUES:
            raise ValueError("kind должен быть workout, water или custom.")
        return normalized

    @field_validator("time_local")
    @classmethod
    def validate_time_local(cls, value: str) -> str:
        return _normalize_time(value)

    @field_validator("days")
    @classmethod
    def validate_days(cls, value: list[str]) -> list[str]:
        return _normalize_days(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReminderRuleCreateRequest(ReminderRuleBaseRequest):
    pass


class ReminderRulePatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    message: str | None = Field(default=None, min_length=1, max_length=500)
    time_local: str | None = None
    days: list[str] | None = Field(default=None, max_length=7)
    enabled: bool | None = None
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("time_local")
    @classmethod
    def validate_time_local(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_time(value)

    @field_validator("days")
    @classmethod
    def validate_days(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_days(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReminderRuleResponse(BaseModel):
    id: int
    kind: str
    title: str
    message: str
    time_local: str
    days: list[str]
    enabled: bool
    timezone: str
    last_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    status: str = "active"


class ReminderRuleListResponse(BaseModel):
    items: list[ReminderRuleResponse]
