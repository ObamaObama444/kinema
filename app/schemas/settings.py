from pydantic import BaseModel, Field, field_validator

_THEME_VALUES = {"system", "light", "dark"}
_LANGUAGE_VALUES = {"ru", "en"}
_WEIGHT_UNIT_VALUES = {"kg", "lb"}
_HEIGHT_UNIT_VALUES = {"cm", "in"}


def _normalize_choice(value: str | None, allowed: set[str], field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in allowed:
        raise ValueError(f"{field_name}: допустимые значения {', '.join(sorted(allowed))}.")
    return normalized


class UserSettingsPatchRequest(BaseModel):
    theme_preference: str | None = None
    language: str | None = None
    weight_unit: str | None = None
    height_unit: str | None = None
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("theme_preference")
    @classmethod
    def validate_theme_preference(cls, value: str | None) -> str | None:
        return _normalize_choice(value, _THEME_VALUES, "theme_preference")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str | None) -> str | None:
        return _normalize_choice(value, _LANGUAGE_VALUES, "language")

    @field_validator("weight_unit")
    @classmethod
    def validate_weight_unit(cls, value: str | None) -> str | None:
        return _normalize_choice(value, _WEIGHT_UNIT_VALUES, "weight_unit")

    @field_validator("height_unit")
    @classmethod
    def validate_height_unit(cls, value: str | None) -> str | None:
        return _normalize_choice(value, _HEIGHT_UNIT_VALUES, "height_unit")

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserSettingsResponse(BaseModel):
    theme_preference: str = "system"
    language: str = "ru"
    weight_unit: str = "kg"
    height_unit: str = "cm"
    timezone: str = "UTC"
    telegram_linked: bool = False
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_user_id: str | None = None
    telegram_bot_username: str | None = None
