from datetime import date, datetime

from pydantic import BaseModel, Field


class StepsGoalUpdateRequest(BaseModel):
    value: int = Field(ge=0, le=50000)


class WaterGoalUpdateRequest(BaseModel):
    value: int = Field(ge=0, le=20)


class WaterIntakeUpdateRequest(BaseModel):
    value: int = Field(ge=0, le=20)


class PulseMeasurementCreateRequest(BaseModel):
    bpm: int = Field(ge=30, le=220)


class BloodPressureMeasurementCreateRequest(BaseModel):
    systolic: int = Field(ge=60, le=240)
    diastolic: int = Field(ge=40, le=180)


class PulsePointResponse(BaseModel):
    id: int
    bpm: int
    hour: int
    minute: int
    recorded_at: datetime


class BloodPressurePointResponse(BaseModel):
    id: int
    systolic: int
    diastolic: int
    hour: int
    minute: int
    recorded_at: datetime


class RecordsSummaryResponse(BaseModel):
    local_date: date
    steps_goal: int = 0
    water_goal_glasses: int = 0
    water_consumed_glasses: int = 0
    latest_pulse_bpm: int | None = None
    latest_systolic: int | None = None
    latest_diastolic: int | None = None
    pulse_points: list[PulsePointResponse] = Field(default_factory=list)
    blood_pressure_points: list[BloodPressurePointResponse] = Field(default_factory=list)
