from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.plan import PersonalizedPlanResponse

MAIN_GOAL_VALUES = {"lose_weight", "gain_muscle", "stay_fit"}
MOTIVATION_VALUES = {"confidence", "look_better", "get_in_shape", "improve_health", "reduce_stress"}
DESIRED_OUTCOME_VALUES = {"disease_prevention", "healthy_habits", "energy", "better_sleep"}
FOCUS_AREA_VALUES = {"shoulders", "arms", "chest", "core", "legs", "full_body"}
GENDER_VALUES = {"male", "female", "other_or_skip"}
FITNESS_LEVEL_VALUES = {"beginner", "intermediate", "advanced", "unknown"}
ACTIVITY_LEVEL_VALUES = {"sedentary", "light", "moderate", "high", "very_high"}
GOAL_PACE_VALUES = {"slow", "moderate", "fast"}
INTEREST_TAG_VALUES = {"general", "pilates", "chair", "dumbbells", "stretching"}
EQUIPMENT_TAG_VALUES = {"none", "dumbbells", "bands", "gym"}
INJURY_AREA_VALUES = {"none", "shoulders", "wrists", "knees", "ankles"}
CALORIE_TRACKING_VALUES = {"yes", "curious", "not_interested"}
DIET_TYPE_VALUES = {"no_restrictions", "regular", "vegetarian", "vegan", "other"}
SELF_IMAGE_VALUES = {"healthy", "strong", "happy", "determined"}
TRAINING_DAY_VALUES = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def _normalize_choice(value: str | None, allowed: set[str]) -> str | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in allowed:
        raise ValueError(f"Допустимые значения: {', '.join(sorted(allowed))}.")
    return normalized


def _normalize_choice_list(value: list[str] | None, allowed: set[str]) -> list[str] | None:
    if value is None:
        return None

    seen: set[str] = set()
    normalized_items: list[str] = []
    for item in value:
        normalized = str(item).strip().lower()
        if not normalized:
            continue
        if normalized not in allowed:
            raise ValueError(f"Допустимые значения: {', '.join(sorted(allowed))}.")
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_items.append(normalized)
    return normalized_items


def _normalize_time(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parts = normalized.split(":")
    if len(parts) != 2:
        raise ValueError("Время напоминания должно быть в формате HH:MM.")

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError as exc:
        raise ValueError("Время напоминания должно быть в формате HH:MM.") from exc

    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        raise ValueError("Время напоминания должно быть в формате HH:MM.")

    return f"{hours:02d}:{minutes:02d}"


class OnboardingPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    main_goal: str | None = None
    motivation: str | None = None
    desired_outcome: str | None = None
    focus_area: str | None = None
    gender: str | None = None
    current_body_shape: int | None = Field(default=None, ge=1, le=5)
    target_body_shape: int | None = Field(default=None, ge=1, le=5)
    age: int | None = Field(default=None, ge=10, le=110)
    height_cm: int | None = Field(default=None, ge=100, le=260)
    current_weight_kg: float | None = Field(default=None, ge=25, le=350)
    target_weight_kg: float | None = Field(default=None, ge=25, le=350)
    fitness_level: str | None = None
    activity_level: str | None = None
    goal_pace: str | None = None
    training_frequency: int | None = Field(default=None, ge=1, le=6)
    calorie_tracking: str | None = None
    diet_type: str | None = None
    self_image: str | None = None
    reminders_enabled: bool | None = None
    reminder_time_local: str | None = None
    interest_tags: list[str] | None = Field(default=None, max_length=3)
    equipment_tags: list[str] | None = Field(default=None, max_length=4)
    injury_areas: list[str] | None = Field(default=None, max_length=5)
    training_days: list[str] | None = Field(default=None, max_length=7)

    @field_validator("main_goal")
    @classmethod
    def validate_main_goal(cls, value: str | None) -> str | None:
        return _normalize_choice(value, MAIN_GOAL_VALUES)

    @field_validator("motivation")
    @classmethod
    def validate_motivation(cls, value: str | None) -> str | None:
        return _normalize_choice(value, MOTIVATION_VALUES)

    @field_validator("desired_outcome")
    @classmethod
    def validate_desired_outcome(cls, value: str | None) -> str | None:
        return _normalize_choice(value, DESIRED_OUTCOME_VALUES)

    @field_validator("focus_area")
    @classmethod
    def validate_focus_area(cls, value: str | None) -> str | None:
        return _normalize_choice(value, FOCUS_AREA_VALUES)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str | None) -> str | None:
        return _normalize_choice(value, GENDER_VALUES)

    @field_validator("fitness_level")
    @classmethod
    def validate_fitness_level(cls, value: str | None) -> str | None:
        return _normalize_choice(value, FITNESS_LEVEL_VALUES)

    @field_validator("activity_level")
    @classmethod
    def validate_activity_level(cls, value: str | None) -> str | None:
        return _normalize_choice(value, ACTIVITY_LEVEL_VALUES)

    @field_validator("goal_pace")
    @classmethod
    def validate_goal_pace(cls, value: str | None) -> str | None:
        return _normalize_choice(value, GOAL_PACE_VALUES)

    @field_validator("calorie_tracking")
    @classmethod
    def validate_calorie_tracking(cls, value: str | None) -> str | None:
        return _normalize_choice(value, CALORIE_TRACKING_VALUES)

    @field_validator("diet_type")
    @classmethod
    def validate_diet_type(cls, value: str | None) -> str | None:
        return _normalize_choice(value, DIET_TYPE_VALUES)

    @field_validator("self_image")
    @classmethod
    def validate_self_image(cls, value: str | None) -> str | None:
        return _normalize_choice(value, SELF_IMAGE_VALUES)

    @field_validator("interest_tags")
    @classmethod
    def validate_interest_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_choice_list(value, INTEREST_TAG_VALUES)

    @field_validator("equipment_tags")
    @classmethod
    def validate_equipment_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_choice_list(value, EQUIPMENT_TAG_VALUES)

    @field_validator("injury_areas")
    @classmethod
    def validate_injury_areas(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_choice_list(value, INJURY_AREA_VALUES)

    @field_validator("training_days")
    @classmethod
    def validate_training_days(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_choice_list(value, TRAINING_DAY_VALUES)

    @field_validator("reminder_time_local")
    @classmethod
    def validate_reminder_time_local(cls, value: str | None) -> str | None:
        return _normalize_time(value)


class OnboardingDataResponse(BaseModel):
    main_goal: str | None = None
    motivation: str | None = None
    desired_outcome: str | None = None
    focus_area: str | None = None
    gender: str | None = None
    current_body_shape: int | None = None
    target_body_shape: int | None = None
    age: int | None = None
    height_cm: int | None = None
    current_weight_kg: float | None = None
    target_weight_kg: float | None = None
    fitness_level: str | None = None
    activity_level: str | None = None
    goal_pace: str | None = None
    training_frequency: int | None = None
    calorie_tracking: str | None = None
    diet_type: str | None = None
    self_image: str | None = None
    reminders_enabled: bool = False
    reminder_time_local: str | None = None
    onboarding_version: str = "v1"
    interest_tags: list[str] = Field(default_factory=list)
    equipment_tags: list[str] = Field(default_factory=list)
    injury_areas: list[str] = Field(default_factory=list)
    training_days: list[str] = Field(default_factory=list)


class OnboardingBodyShapeDerivedResponse(BaseModel):
    shape: int | None = None
    label: str | None = None
    range_text: str | None = None
    percent_value: float | None = None
    caption: str | None = None


class OnboardingMilestoneResponse(BaseModel):
    week: int
    label: str
    date_label: str
    weight_kg: float
    is_target: bool = False


class OnboardingAnalysisItemResponse(BaseModel):
    title: str
    value: str


class OnboardingDerivedResponse(BaseModel):
    bmi: float | None = None
    bmi_label: str | None = None
    bmr_kcal: int | None = None
    weight_delta_kg: float | None = None
    estimated_weeks: int | None = None
    target_date_iso: str | None = None
    target_date_label: str | None = None
    goal_target_value: str | None = None
    body_fat_delta_percent: float | None = None
    current_body: OnboardingBodyShapeDerivedResponse = Field(default_factory=OnboardingBodyShapeDerivedResponse)
    target_body: OnboardingBodyShapeDerivedResponse = Field(default_factory=OnboardingBodyShapeDerivedResponse)
    analysis_items: list[OnboardingAnalysisItemResponse] = Field(default_factory=list)
    milestones: list[OnboardingMilestoneResponse] = Field(default_factory=list)


class OnboardingStateResponse(BaseModel):
    status: str
    is_completed: bool
    resume_step: str
    data: OnboardingDataResponse
    derived: OnboardingDerivedResponse


class OnboardingResetResponse(BaseModel):
    ok: bool
    message: str
    telegram_notification_sent: bool = False


class OnboardingCompleteResponse(OnboardingStateResponse):
    completed_at: datetime | None = None
    plan_ready: bool = False
    plan: PersonalizedPlanResponse | None = None
