from datetime import date

from pydantic import BaseModel

from app.schemas.goal import GoalResponse
from app.schemas.program import ActiveProgramSummary


class ProgressCalendarDayResponse(BaseModel):
    date: date
    day_number: int
    weekday_short: str
    is_planned: bool = False
    is_completed: bool = False
    is_manual_completed: bool = False
    is_session_completed: bool = False
    is_today: bool = False
    can_toggle: bool = False


class ProgressCheckinRequest(BaseModel):
    date: date
    completed: bool = True


class ProgressWeightPointResponse(BaseModel):
    date: date
    weight_kg: float


class ProgressSummaryResponse(BaseModel):
    active_program: ActiveProgramSummary | None = None
    current_goal: GoalResponse | None = None
    streak_days: int = 0
    completed_this_month: int = 0
    month_key: str
    month_label: str
    calendar_days: list[ProgressCalendarDayResponse]
    latest_weight_kg: float | None = None
    initial_weight_kg: float | None = None
    previous_weight_kg: float | None = None
    previous_weight_days_ago: int | None = None
    bmi: float | None = None
    bmi_label: str | None = None
    weight_points: list[ProgressWeightPointResponse]
