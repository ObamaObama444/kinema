from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GeneratedTechniqueFrameMetric(BaseModel):
    timestamp_ms: int | None = None
    primary_angle: float
    secondary_angle: float | None = None
    depth_norm: float | None = None
    torso_angle: float | None = None
    asymmetry: float | None = None
    hip_asymmetry: float | None = None
    side_view_score: float | None = None
    heel_lift_norm: float | None = None
    leg_angle: float | None = None
    posture_tilt_deg: float | None = None
    hip_ankle_vertical_norm: float | None = None


class ExerciseTechniqueProfileResponse(BaseModel):
    id: int
    exercise_id: int
    slug: str
    title: str
    description: str
    status: str
    is_system: bool = False
    motion_family: str
    motion_family_label: str
    view_type: str
    view_type_label: str
    source_video_name: str | None = None
    source_video_meta: dict[str, Any] | None = None
    reference_model: dict[str, Any]
    calibration_profile: dict[str, Any]
    latest_test_summary: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    published_at: datetime | None = None
    can_edit: bool = False
    launch_url: str


class CalibrationProfileUpdateRequest(BaseModel):
    calibration_profile: dict[str, Any]


class GeneratedExerciseCompareRequest(BaseModel):
    frame_metrics: list[GeneratedTechniqueFrameMetric] = Field(min_length=10)
    duration_ms: int | None = Field(default=None, ge=1)


class GeneratedExerciseCompareResponse(BaseModel):
    rep_score: int
    quality: str
    errors: list[str]
    tips: list[str]
    metrics: dict[str, float]
    details: dict[str, Any]


class ExerciseTechniquePublishResponse(BaseModel):
    ok: bool
    profile: ExerciseTechniqueProfileResponse
