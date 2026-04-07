from datetime import datetime

from pydantic import BaseModel, Field


class PlanSummaryItemResponse(BaseModel):
    label: str
    value: str


class PlanExerciseResponse(BaseModel):
    slug: str
    title: str
    details: str
    sets: int = Field(ge=1, le=10)
    reps: int = Field(ge=1, le=60)
    rest_sec: int = Field(ge=0, le=300)


class PlanDayResponse(BaseModel):
    day_number: int = Field(ge=1, le=30)
    stage_number: int = Field(ge=1, le=3)
    date_label: str
    title: str
    subtitle: str
    duration_min: int = Field(ge=0, le=120)
    estimated_kcal: int = Field(ge=0, le=1500)
    intensity: str
    emphasis: str
    note: str
    kind: str
    exercises: list[PlanExerciseResponse] = Field(default_factory=list)
    is_highlighted: bool = False


class PlanStageResponse(BaseModel):
    stage_number: int = Field(ge=1, le=3)
    title: str
    subtitle: str
    badge: str
    days: list[PlanDayResponse] = Field(default_factory=list)


class PersonalizedPlanResponse(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    signature: str
    source: str
    generated_at: datetime
    headline: str
    subheadline: str
    tags: list[str] = Field(default_factory=list)
    summary_items: list[PlanSummaryItemResponse] = Field(default_factory=list)
    stages: list[PlanStageResponse] = Field(default_factory=list)
