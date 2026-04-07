from datetime import date, datetime

from pydantic import BaseModel, Field


class WeightEntryCreateRequest(BaseModel):
    weight_kg: float = Field(ge=25, le=350)


class WeightEntryResponse(BaseModel):
    id: int
    weight_kg: float
    recorded_on_local_date: date
    timezone: str
    created_at: datetime


class WeightHistorySummaryResponse(BaseModel):
    entries: list[WeightEntryResponse]
    latest_weight_kg: float | None = None
    initial_weight_kg: float | None = None
    target_weight_kg: float | None = None
    bmi: float | None = None
    bmi_label: str | None = None
    can_add_now: bool = True
    next_allowed_at: datetime | None = None
    latest_entry_created_at: datetime | None = None
    hours_until_next_entry: float | None = None
    latest_days_ago: int | None = None
    previous_weight_kg: float | None = None
    last_seven_days_delta_kg: float = 0.0
    last_thirty_days_delta_kg: float = 0.0
