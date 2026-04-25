from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exercise_catalog import (
    CATALOG_DB_NAME_BY_SLUG,
    EXERCISE_CATALOG,
    catalog_db_name_candidates,
    catalog_slug_by_db_name,
)
from app.core.deps import get_db
from app.models.exercise import Exercise
from app.models.exercise_technique_profile import ExerciseTechniqueProfile
from app.models.technique_session import TechniqueSession
from app.models.user import User
from app.services.generated_technique import compare_generated_rep, load_json
from app.services.technique_compare import compare_pushup_rep, compare_squat_rep

router = APIRouter(tags=["technique"])

LOGS_DIR = Path("data/session_logs")
SYSTEM_REFERENCE_DIR = Path("data/system_reference_profiles")
CANONICAL_TECHNIQUE_CONFIG: dict[str, dict[str, Any]] = {
    "squat": {"motion_family": "squat_like", "view_type": "side"},
    "pushup": {"motion_family": "push_like", "view_type": "side"},
    "lunge": {"motion_family": "lunge_like", "view_type": "side"},
    "glute_bridge": {"motion_family": "core_like", "view_type": "side", "primary_direction": "rise"},
    "leg_raise": {"motion_family": "core_like", "view_type": "side"},
    "crunch": {"motion_family": "core_like", "view_type": "side"},
}
TECHNIQUE_EXERCISE_SLUGS = tuple(CANONICAL_TECHNIQUE_CONFIG.keys())
TECHNIQUE_CATALOG_BY_SLUG = {
    str(item["slug"]): item
    for item in EXERCISE_CATALOG
}

QUALITY_LABELS = (
    ("отлично", 90.0),
    ("хорошо", 75.0),
    ("норм", 60.0),
)

METRIC_ISSUE_MAP: dict[str, dict[str, str]] = {
    "min_knee_angle": {
        "code": "knee_depth_control",
        "title": "Контроль глубины в колене",
        "explanation": "Амплитуда в коленном суставе отклоняется от целевой, повторы получаются нестабильными.",
        "severity": "med",
    },
    "min_hip_angle": {
        "code": "hip_depth_control",
        "title": "Контроль глубины в тазу",
        "explanation": "Глубина в тазобедренном суставе недостаточно ровная по повторам.",
        "severity": "med",
    },
    "max_depth_delta": {
        "code": "depth_stability",
        "title": "Нестабильная амплитуда",
        "explanation": "Амплитуда движения в нижней точке плавает между повторами.",
        "severity": "med",
    },
    "depth_ratio": {
        "code": "depth_ratio_mismatch",
        "title": "Отклонение рабочей глубины",
        "explanation": "Фактическая глубина отличается от ожидаемого диапазона.",
        "severity": "high",
    },
    "knee_ratio": {
        "code": "knee_ratio_mismatch",
        "title": "Отклонение по работе колена",
        "explanation": "Соотношение сгибания колена выходит за рабочий диапазон.",
        "severity": "med",
    },
    "hip_ratio": {
        "code": "hip_ratio_mismatch",
        "title": "Отклонение по работе таза",
        "explanation": "Соотношение сгибания в тазу не совпадает с целевым паттерном.",
        "severity": "med",
    },
    "max_torso_forward": {
        "code": "torso_forward",
        "title": "Избыточный наклон корпуса",
        "explanation": "Корпус уходит вперёд сильнее, чем нужно для безопасной механики.",
        "severity": "high",
    },
    "p90_heel_lift": {
        "code": "heel_lift",
        "title": "Отрыв пяток",
        "explanation": "На части повторов пятки отрываются от опоры и снижают стабильность.",
        "severity": "high",
    },
    "mean_side_view_score": {
        "code": "camera_side_view",
        "title": "Слабый боковой ракурс",
        "explanation": "Ракурс ухудшает точность оценки техники.",
        "severity": "low",
    },
    "min_elbow_angle": {
        "code": "elbow_depth_control",
        "title": "Контроль сгибания локтя",
        "explanation": "Глубина в локте нестабильна или недостаточна в нижней фазе.",
        "severity": "med",
    },
    "min_leg_knee_angle": {
        "code": "leg_line_break",
        "title": "Ломается линия ног",
        "explanation": "Ноги чрезмерно сгибаются и снижают стабильность корпуса.",
        "severity": "med",
    },
    "p90_depth_delta": {
        "code": "push_depth_stability",
        "title": "Плавающая глубина отжиманий",
        "explanation": "Глубина движения меняется от повтора к повтору.",
        "severity": "med",
    },
    "depth_ratio_raw": {
        "code": "excessive_depth_drop",
        "title": "Провал в нижней точке",
        "explanation": "Амплитуда в нижней фазе избыточна и теряется контроль.",
        "severity": "high",
    },
    "elbow_ratio": {
        "code": "elbow_ratio_mismatch",
        "title": "Отклонение по паттерну локтя",
        "explanation": "Соотношение сгибания локтя выходит за рабочий диапазон.",
        "severity": "med",
    },
    "p90_body_bend": {
        "code": "body_line_break",
        "title": "Потеря линии корпуса",
        "explanation": "Корпус сгибается сильнее целевого уровня во время повтора.",
        "severity": "high",
    },
}

ISSUE_META_BY_CODE: dict[str, dict[str, str]] = {
    "undersquat": {
        "code": "undersquat",
        "title": "Недостаточная глубина приседа",
        "explanation": "Повторы выполняются выше рабочей глубины, нагрузка уходит из целевой траектории.",
        "severity": "high",
    },
    "heel_lift": {
        "code": "heel_lift",
        "title": "Отрыв пяток",
        "explanation": "Пятки отрываются от пола и снижают устойчивость в нижней точке.",
        "severity": "high",
    },
    "torso_forward": {
        "code": "torso_forward",
        "title": "Избыточный наклон корпуса",
        "explanation": "Корпус уходит вперёд, что повышает нагрузку на поясницу.",
        "severity": "med",
    },
    "asymmetry": {
        "code": "asymmetry",
        "title": "Асимметрия сторон",
        "explanation": "Левая и правая стороны работают неравномерно по амплитуде или скорости.",
        "severity": "med",
    },
    "camera_side_view": {
        "code": "camera_side_view",
        "title": "Недостаточный боковой ракурс",
        "explanation": "Ракурс ограничивает точность оценки глубины и углов.",
        "severity": "low",
    },
    "good_rep": {
        "code": "good_rep",
        "title": "Чистый повтор",
        "explanation": "Повтор близок к целевой технике и может служить ориентиром.",
        "severity": "low",
    },
}

SEVERITY_WEIGHT = {"high": 3, "med": 2, "low": 1}

RECOMMENDATION_TEMPLATES: dict[str, dict[str, Any]] = {
    "knee_depth_control": {
        "advice": "Сделайте одинаковую глубину колена в каждом приседе.",
        "steps": [
            "Опускайтесь на счёт «раз-два», без ускорения вниз.",
            "Внизу зафиксируйте позицию на полсекунды.",
            "Если глубина плавает, снизьте темп и сделайте повтор заново.",
        ],
    },
    "hip_depth_control": {
        "advice": "Держите таз на одной рабочей глубине без провала.",
        "steps": [
            "Перед началом повторов выберите комфортную нижнюю точку.",
            "Следите, чтобы таз опускался до этой точки каждый раз.",
            "Если чувствуете потерю контроля, остановите повтор и начните заново.",
        ],
    },
    "depth_stability": {
        "advice": "Уберите «плавающую» амплитуду между повторами.",
        "steps": [
            "Первый повтор используйте как эталон по глубине.",
            "Каждый следующий повтор делайте на ту же глубину.",
            "Если ушли выше или ниже, замедлитесь на следующем повторе.",
        ],
    },
    "depth_ratio_mismatch": {
        "advice": "Верните глубину в стабильный рабочий диапазон.",
        "steps": [
            "Начните подход медленнее обычного.",
            "Не проваливайтесь внизу: остановка короткая и контролируемая.",
            "Поднимайтесь только после стабильной нижней позиции.",
        ],
    },
    "knee_ratio_mismatch": {
        "advice": "Стабилизируйте движение колена по одинаковой траектории.",
        "steps": [
            "Держите стопу полностью на полу весь повтор.",
            "Смотрите, чтобы колени шли по одной линии на каждом повторе.",
        ],
    },
    "hip_ratio_mismatch": {
        "advice": "Синхронизируйте движение таза и коленей.",
        "steps": [
            "Начинайте опускание одновременно тазом и коленями.",
            "Не допускайте резкого провала внизу.",
            "Если траектория сбилась, сократите амплитуду на 1-2 повтора.",
        ],
    },
    "torso_forward": {
        "advice": "Уменьшите лишний наклон корпуса вперёд.",
        "steps": [
            "Перед повтором поднимите грудь и зафиксируйте ровную спину.",
            "Опускаясь вниз, держите вес ближе к середине стопы.",
            "Если корпус заваливается, уменьшите глубину и восстановите контроль.",
        ],
    },
    "heel_lift": {
        "advice": "Удерживайте пятки на опоре в каждом повторе.",
        "steps": [
            "Держите давление в середине стопы и пятке.",
            "Если пятка отрывается, сразу уменьшите глубину.",
            "Добавляйте глубину постепенно, только когда пятка остаётся на полу.",
        ],
    },
    "undersquat": {
        "advice": "Добавьте рабочую глубину приседа, не ускоряясь внизу.",
        "steps": [
            "Опускайтесь медленно на счёт «раз-два».",
            "В нижней точке держите короткую паузу 0.3-0.5 секунды.",
            "Если глубина не достигнута, уменьшите темп и повторите.",
        ],
    },
    "asymmetry": {
        "advice": "Сделайте движение симметричным с обеих сторон.",
        "steps": [
            "Следите, чтобы колени и таз двигались с одинаковой скоростью.",
            "Контролируйте одинаковую глубину для левой и правой стороны.",
            "При перекосе остановите повтор и перезапустите движение.",
        ],
    },
    "camera_side_view": {
        "advice": "Улучшите ракурс, чтобы точнее оценивать технику.",
        "steps": [
            "Повернитесь к камере боком.",
            "Поставьте камеру на уровне таза (присед) или локтя (отжимания).",
        ],
    },
    "elbow_depth_control": {
        "advice": "Сделайте одинаковую глубину сгибания локтя в отжиманиях.",
        "steps": [
            "Опускайтесь до одной и той же нижней точки.",
            "Не меняйте глубину от повтора к повтору.",
            "Если амплитуда падает, сделайте паузу 10-15 секунд.",
        ],
    },
    "leg_line_break": {
        "advice": "Стабилизируйте ноги и линию корпуса.",
        "steps": [
            "Перед подходом зафиксируйте планку 5 секунд.",
            "Во время повторов не сгибайте колени сильнее необходимого.",
        ],
    },
    "push_depth_stability": {
        "advice": "Сделайте глубину отжиманий ровной на всех повторах.",
        "steps": [
            "Опускайтесь и поднимайтесь в одном темпе.",
            "Коротко фиксируйте нижнюю фазу без провала.",
            "Засчитывайте только повторы с одинаковой амплитудой.",
        ],
    },
    "excessive_depth_drop": {
        "advice": "Уберите провал в нижней точке отжимания.",
        "steps": [
            "Не падайте вниз: опускайтесь медленно и под контролем.",
            "Начинайте подъём сразу после рабочей глубины.",
            "При потере контроля уменьшите амплитуду на 1-2 повтора.",
        ],
    },
    "elbow_ratio_mismatch": {
        "advice": "Верните угол локтя в рабочий диапазон.",
        "steps": [
            "Следите за одинаковой траекторией локтей на каждом повторе.",
            "Избегайте слишком мелкой и слишком глубокой фазы.",
        ],
    },
    "body_line_break": {
        "advice": "Удерживайте ровную линию корпуса.",
        "steps": [
            "Напрягите пресс и ягодицы до старта повтора.",
            "Держите корпус прямой линией от плеч до пяток.",
            "Остановите повтор, если поясница начала проваливаться.",
        ],
    },
}

FALLBACK_RECOMMENDATIONS: list[dict[str, Any]] = [
    {
        "advice": "Снизьте темп и держите одинаковую амплитуду на всём подходе.",
        "steps": [
            "Делайте каждый повтор на счёт «раз-два» вниз и «раз-два» вверх.",
            "Сравнивайте каждый повтор с первым: глубина и темп должны совпадать.",
        ],
    },
    {
        "advice": "Проведите короткий технический сет перед рабочим подходом.",
        "steps": [
            "Сделайте 2-3 медленных повтора только на технику.",
            "Переходите к рабочему темпу только после стабильной формы.",
        ],
    },
    {
        "advice": "Останавливайте повтор при потере контроля, а не добивайте любой ценой.",
        "steps": [
            "Если траектория «поплыла», завершите повтор и перезапустите движение.",
            "После остановки сделайте 10-15 секунд паузы и продолжите.",
        ],
    },
]

RISK_TEMPLATE_BY_CODE: dict[str, str] = {
    "undersquat": "Риск недогрузки целевых мышц и закрепления неправильной амплитуды.",
    "torso_forward": "Высокий риск перегрузки поясницы при текущем наклоне корпуса.",
    "heel_lift": "Высокий риск потери устойчивости из-за отрыва пяток.",
    "body_line_break": "Высокий риск перегрузки плеч и поясницы из-за потери линии корпуса.",
    "excessive_depth_drop": "Высокий риск провала в нижней фазе и потери контроля.",
}


class TechniqueFrameMetric(BaseModel):
    timestamp_ms: int | None = None
    primary_angle: float
    secondary_angle: float | None = None
    depth_norm: float | None = None
    depth_delta: float | None = None
    torso_angle: float | None = None
    asymmetry: float | None = None
    hip_asymmetry: float | None = None
    side_view_score: float | None = None
    heel_lift_norm: float | None = None
    leg_angle: float | None = None
    posture_tilt_deg: float | None = None
    hip_ankle_vertical_norm: float | None = None


class CompareRequest(BaseModel):
    rep_index: int = Field(ge=1)
    frame_metrics: list[TechniqueFrameMetric] = Field(min_length=4)


class CompareResponse(BaseModel):
    rep_index: int
    rep_score: int
    quality: str
    errors: list[str]
    tips: list[str]
    metrics: dict[str, float]
    details: dict[str, Any]


class SavedRepPayload(BaseModel):
    repIndex: int = Field(ge=1)
    repScore: float = Field(ge=0, le=100)
    metrics: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    details: dict[str, Any] | None = None
    frameMetrics: list[TechniqueFrameMetric] | None = None


class SaveTechniqueLogRequest(BaseModel):
    exercise: str = Field(min_length=1, max_length=64)
    sessionId: str = Field(min_length=1, max_length=120)
    reps: list[SavedRepPayload] = Field(min_length=1)
    aggregates: dict[str, Any] | None = None

    @field_validator("exercise")
    @classmethod
    def normalize_exercise(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in TECHNIQUE_EXERCISE_SLUGS:
            allowed = ", ".join(TECHNIQUE_EXERCISE_SLUGS)
            raise ValueError(f"Поддерживаются только упражнения: {allowed}.")
        return normalized

    @field_validator("sessionId")
    @classmethod
    def normalize_session_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("sessionId не должен быть пустым.")
        return normalized


class SaveTechniqueLogResponse(BaseModel):
    ok: bool
    file_path: str


class TechniqueExerciseResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    technique_available: bool
    motion_family: str
    view_type: str
    profile_id: int | None = None
    reference_based: bool = False


class TechniqueSessionStartRequest(BaseModel):
    exercise_slug: str = Field(min_length=1, max_length=64)

    @field_validator("exercise_slug")
    @classmethod
    def normalize_exercise_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in TECHNIQUE_EXERCISE_SLUGS:
            allowed = ", ".join(TECHNIQUE_EXERCISE_SLUGS)
            raise ValueError(f"Сейчас техника доступна только для: {allowed}.")
        return normalized


class TechniqueSessionStartResponse(BaseModel):
    session_id: int
    redirect_url: str
    exercise: TechniqueExerciseResponse


class TechniqueSessionResponse(BaseModel):
    session_id: int
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    reps_count: int
    avg_score: float | None = None
    log_path: str | None = None
    exercise: TechniqueExerciseResponse


class TechniqueBaselineSnapshot(BaseModel):
    baseline_primary: float | None = None
    baseline_depth: float | None = None
    baseline_heel: float | None = None
    baseline_primary_initial: float | None = None
    baseline_depth_initial: float | None = None


class TechniqueLiveRequest(BaseModel):
    session_id: int = Field(ge=1)
    phase: Literal["WAIT_READY", "TOP", "DOWN", "RISING"] = "WAIT_READY"
    frame_metric: TechniqueFrameMetric
    baseline_snapshot: TechniqueBaselineSnapshot | None = None


class TechniqueSessionLiveRequest(BaseModel):
    phase: Literal["WAIT_READY", "TOP", "DOWN", "RISING"] = "WAIT_READY"
    frame_metric: TechniqueFrameMetric
    baseline_snapshot: TechniqueBaselineSnapshot | None = None


class TechniqueLiveResponse(BaseModel):
    hint: str
    tone: Literal["low", "med", "high"]
    posture_ok: bool
    phase: str
    debug: dict[str, float | bool | str] | None = None


class FinishTechniqueSessionRequest(BaseModel):
    exercise: str = Field(min_length=1, max_length=64)
    reps: list[SavedRepPayload] = Field(default_factory=list)
    aggregates: dict[str, Any] | None = None

    @field_validator("exercise")
    @classmethod
    def normalize_finish_exercise(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in TECHNIQUE_EXERCISE_SLUGS:
            allowed = ", ".join(TECHNIQUE_EXERCISE_SLUGS)
            raise ValueError(f"Сейчас техника доступна только для: {allowed}.")
        return normalized


class TechniqueSessionFinishResponse(BaseModel):
    ok: bool
    session_id: int
    status: str
    reps_count: int
    avg_score: float | None = None
    log_path: str | None = None
    redirect_url: str
    ui: dict[str, Any] | None = None


def _catalog_item_by_slug(slug: str) -> dict[str, Any]:
    item = TECHNIQUE_CATALOG_BY_SLUG.get(slug)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Упражнение не найдено в каталоге.",
        )
    return item


def _technique_defaults(slug: str) -> dict[str, Any]:
    defaults = CANONICAL_TECHNIQUE_CONFIG.get(slug)
    if defaults is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Упражнение не поддерживается для проверки техники.",
        )
    return defaults


def _load_system_profile_from_disk(slug: str) -> dict[str, Any] | None:
    target_path = SYSTEM_REFERENCE_DIR / f"{slug}.json"
    if not target_path.exists():
        return None
    try:
        return json.loads(target_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _published_system_profile_for_slug(db: Session, slug: str) -> ExerciseTechniqueProfile | None:
    candidates = catalog_db_name_candidates(slug)
    if not candidates:
        return None
    return db.execute(
        select(ExerciseTechniqueProfile)
        .join(Exercise, Exercise.id == ExerciseTechniqueProfile.exercise_id)
        .where(
            ExerciseTechniqueProfile.status == "published",
            ExerciseTechniqueProfile.is_system.is_(True),
            Exercise.name.in_(candidates),
        )
        .order_by(ExerciseTechniqueProfile.id.desc())
    ).scalar_one_or_none()


def _resolved_reference_payload(db: Session, slug: str) -> dict[str, Any]:
    defaults = _technique_defaults(slug)
    if slug == "squat":
        return {
            "profile_id": None,
            "motion_family": str(defaults["motion_family"]),
            "view_type": str(defaults["view_type"]),
            "reference_based": False,
            "reference_model": None,
            "calibration_profile": None,
        }

    profile = _published_system_profile_for_slug(db, slug)
    if profile is not None:
        return {
            "profile_id": int(profile.id),
            "motion_family": str(profile.motion_family),
            "view_type": str(profile.view_type),
            "reference_based": True,
            "reference_model": load_json(profile.reference_model_json, {}),
            "calibration_profile": load_json(profile.calibration_profile_json, {}),
        }

    disk_payload = _load_system_profile_from_disk(slug)
    if isinstance(disk_payload, dict):
        return {
            "profile_id": None,
            "motion_family": str(disk_payload.get("motion_family") or defaults["motion_family"]),
            "view_type": str(disk_payload.get("view_type") or defaults["view_type"]),
            "reference_based": True,
            "reference_model": load_json(json.dumps(disk_payload.get("reference_model") or {}), {}),
            "calibration_profile": load_json(json.dumps(disk_payload.get("calibration_profile") or {}), {}),
        }

    return {
        "profile_id": None,
        "motion_family": str(defaults["motion_family"]),
        "view_type": str(defaults["view_type"]),
        "reference_based": True,
        "reference_model": None,
        "calibration_profile": None,
    }


def _difficulty_from_tags(tags: list[str]) -> str:
    normalized = " ".join(str(tag).strip().lower() for tag in tags)
    if "продвинут" in normalized:
        return "hard"
    if "средн" in normalized:
        return "medium"
    return "easy"


def _get_or_create_catalog_exercise(db: Session, slug: str) -> Exercise:
    db_name = CATALOG_DB_NAME_BY_SLUG.get(slug)
    if not db_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Упражнение не поддерживается.",
        )

    exercise = db.execute(
        select(Exercise).where(Exercise.name.in_(catalog_db_name_candidates(slug)))
    ).scalar_one_or_none()
    if exercise is not None:
        if exercise.name != db_name:
            exercise.name = db_name
            db.add(exercise)
            db.flush()
        return exercise

    catalog_item = _catalog_item_by_slug(slug)
    tags = [str(item).strip() for item in catalog_item.get("tags", []) if str(item).strip()]
    exercise = Exercise(
        name=db_name,
        description=str(catalog_item.get("description") or db_name),
        equipment=None,
        primary_muscles=tags[-1] if tags else None,
        difficulty=_difficulty_from_tags(tags),
    )
    db.add(exercise)
    db.flush()
    return exercise


def _serialize_exercise(exercise: Exercise, slug: str, db: Session) -> TechniqueExerciseResponse:
    catalog_item = _catalog_item_by_slug(slug)
    reference_payload = _resolved_reference_payload(db, slug)
    return TechniqueExerciseResponse(
        id=exercise.id,
        slug=slug,
        title=str(catalog_item.get("title") or exercise.name),
        description=str(catalog_item.get("description") or exercise.description),
        tags=[str(item).strip() for item in catalog_item.get("tags", []) if str(item).strip()],
        technique_available=bool(catalog_item.get("technique_available")),
        motion_family=str(reference_payload["motion_family"]),
        view_type=str(reference_payload["view_type"]),
        profile_id=reference_payload["profile_id"],
        reference_based=bool(reference_payload["reference_based"]),
    )


def _session_slug(session: TechniqueSession) -> str:
    slug = catalog_slug_by_db_name(session.exercise.name)
    if slug:
        return slug
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Не удалось определить упражнение для technique-сессии.")


def _get_owned_technique_session(
    db: Session,
    user_id: int,
    session_id: int,
) -> TechniqueSession:
    session = db.execute(
        select(TechniqueSession)
        .where(
            TechniqueSession.id == session_id,
            TechniqueSession.user_id == user_id,
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Technique-сессия не найдена.",
        )
    return session


def _serialize_session(session: TechniqueSession) -> TechniqueSessionResponse:
    slug = _session_slug(session)
    session_db = session.exercise._sa_instance_state.session
    return TechniqueSessionResponse(
        session_id=session.id,
        status=str(session.status),
        started_at=session.started_at,
        ended_at=session.ended_at,
        reps_count=int(session.reps_count or 0),
        avg_score=float(session.avg_score) if session.avg_score is not None else None,
        log_path=str(session.log_path) if session.log_path else None,
        exercise=_serialize_exercise(session.exercise, slug, session_db),
    )


def _float_or(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _sanitize_session_id(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", session_id)
    safe = safe.strip("-")
    if not safe:
        return "session"
    return safe[:80]


def _build_aggregates(reps: list[SavedRepPayload]) -> dict[str, Any]:
    scores = [float(item.repScore) for item in reps]
    avg_score = round(sum(scores) / len(scores), 2)

    # Find the worst metric value among numeric metrics of the lowest-scored rep.
    worst_rep = min(reps, key=lambda item: float(item.repScore))
    numeric_metrics = {
        key: float(value)
        for key, value in worst_rep.metrics.items()
        if isinstance(value, (int, float))
    }
    worst_metrics = dict(sorted(numeric_metrics.items(), key=lambda pair: pair[1])[:3])

    tips_counter = Counter(
        tip
        for rep in reps
        for tip in rep.tips
        if isinstance(tip, str) and tip.strip()
    )
    summary_tips = [tip for tip, _ in tips_counter.most_common(3)]

    return {
        "avgScore": avg_score,
        "worstMetrics": worst_metrics,
        "summaryTips": summary_tips,
    }


def _quality_label(score: float | None) -> str:
    if score is None:
        return "нужно улучшить"
    for label, threshold in QUALITY_LABELS:
        if score >= threshold:
            return label
    return "нужно улучшить"


def _issue_meta_for_metric(metric_key: str) -> dict[str, str]:
    mapped = METRIC_ISSUE_MAP.get(metric_key)
    if mapped:
        return mapped

    return {
        "code": f"metric_{metric_key}",
        "title": f"Метрика {metric_key}",
        "explanation": "Зафиксировано отклонение по метрике, требует контроля в следующем подходе.",
        "severity": "med",
    }


def _issue_meta_for_code(code: str) -> dict[str, str]:
    mapped = ISSUE_META_BY_CODE.get(code)
    if mapped:
        return mapped

    for metric_issue in METRIC_ISSUE_MAP.values():
        if metric_issue.get("code") == code:
            return {
                "code": code,
                "title": str(metric_issue.get("title", "Техническое отклонение")),
                "explanation": str(
                    metric_issue.get(
                        "explanation",
                        "Зафиксировано отклонение техники, требуется корректировка в следующем подходе.",
                    )
                ),
                "severity": str(metric_issue.get("severity", "med")),
            }

    return {
        "code": code,
        "title": "Техническое отклонение",
        "explanation": "Зафиксировано отклонение техники. Сосредоточьтесь на контроле амплитуды и темпа.",
        "severity": "med",
    }


def _issue_code_from_error_text(error_text: str) -> str | None:
    lowered = error_text.lower()
    if "пят" in lowered:
        return "heel_lift"
    if "недостаточ" in lowered and "глуб" in lowered:
        return "undersquat"
    if "наклон корпуса" in lowered:
        return "torso_forward"
    if "асиммет" in lowered:
        return "asymmetry"
    if "ракурс" in lowered:
        return "camera_side_view"
    if "линия корпуса" in lowered:
        return "body_line_break"
    return None


def _build_top_issues(reps: list[SavedRepPayload], aggregates: dict[str, Any]) -> list[dict[str, str]]:
    issue_stats: dict[str, dict[str, Any]] = {}

    def _touch(code: str, evidence_ref: str, boost: float = 1.0) -> None:
        meta = _issue_meta_for_code(code)
        if code not in issue_stats:
            issue_stats[code] = {
                "count": 0.0,
                "severity": meta["severity"],
                "title": meta["title"],
                "explanation": meta["explanation"],
                "evidenceRef": evidence_ref,
            }
        issue_stats[code]["count"] += boost

    for rep_index, rep in enumerate(reps):
        details = rep.details if isinstance(rep.details, dict) else {}
        hint_codes = details.get("hint_codes")
        if isinstance(hint_codes, list):
            for code_raw in hint_codes:
                code = str(code_raw).strip()
                if not code or code == "good_rep":
                    continue
                _touch(code, f"reps[{rep_index}].details.hint_codes", boost=1.2)

        for error in rep.errors:
            code_from_error = _issue_code_from_error_text(str(error))
            if not code_from_error:
                continue
            _touch(code_from_error, f"reps[{rep_index}].errors", boost=1.0)

    worst_metrics = aggregates.get("worstMetrics")
    if isinstance(worst_metrics, dict):
        for metric_key in worst_metrics.keys():
            metric = str(metric_key)
            meta = _issue_meta_for_metric(metric)
            _touch(meta["code"], f"aggregates.worstMetrics.{metric}", boost=0.7)

    if not issue_stats:
        return []

    ranked = sorted(
        issue_stats.items(),
        key=lambda item: (
            float(item[1]["count"]) * 10.0
            + float(SEVERITY_WEIGHT.get(str(item[1]["severity"]), 1)) * 100.0
        ),
        reverse=True,
    )

    top_issues: list[dict[str, str]] = []
    for code, stat in ranked[:3]:
        top_issues.append(
            {
                "code": code,
                "title": str(stat["title"]),
                "explanation": str(stat["explanation"]),
                "severity": str(stat["severity"]),
                "evidenceRef": str(stat["evidenceRef"]),
            }
        )
    return top_issues


def _build_recommendations(
    top_issues: list[dict[str, str]],
    aggregates: dict[str, Any],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for index, issue in enumerate(top_issues):
        code = issue.get("code", "")
        if not code or code in seen_codes:
            continue

        template = RECOMMENDATION_TEMPLATES.get(code)
        if not template:
            template = {
                "advice": f"Сфокусируйтесь на улучшении: {issue.get('title', code)}.",
                "steps": [
                    "Снизьте темп повтора для контроля техники.",
                    "Проверьте, что амплитуда остаётся стабильной во всех повторах.",
                ],
            }

        steps = [str(item).strip() for item in template.get("steps", []) if str(item).strip()]
        if len(steps) < 2:
            steps = [
                "Снизьте темп повтора для контроля техники.",
                "Проверьте, что амплитуда остаётся стабильной во всех повторах.",
            ]

        recommendations.append(
            {
                "advice": str(template.get("advice", "")).strip() or "Сфокусируйтесь на стабильности техники.",
                "steps": steps[:4],
                "evidenceRef": f"ui.topIssues[{index}].code",
            }
        )
        seen_codes.add(code)

    summary_tips = aggregates.get("summaryTips")
    if isinstance(summary_tips, list):
        for idx, tip in enumerate(summary_tips):
            if len(recommendations) >= 5:
                break
            tip_text = str(tip).strip()
            if not tip_text:
                continue
            if any(item["advice"] == tip_text for item in recommendations):
                continue

            recommendations.append(
                {
                    "advice": tip_text,
                    "steps": [
                        "Сделайте 2 медленных повтора и не ускоряйтесь внизу.",
                        "Убедитесь, что следующий повтор повторяет ту же амплитуду.",
                    ],
                    "evidenceRef": f"aggregates.summaryTips[{idx}]",
                }
            )

    for fallback in FALLBACK_RECOMMENDATIONS:
        if len(recommendations) >= 5:
            break

        advice_text = str(fallback.get("advice", "")).strip()
        if not advice_text:
            continue
        if any(item.get("advice") == advice_text for item in recommendations):
            continue

        fallback_steps = [str(step).strip() for step in fallback.get("steps", []) if str(step).strip()]
        if len(fallback_steps) < 2:
            fallback_steps = [
                "Сделайте 2 медленных повтора под контроль техники.",
                "Повторите подход в том же темпе без ускорений.",
            ]

        recommendations.append(
            {
                "advice": advice_text,
                "steps": fallback_steps[:4],
                "evidenceRef": "ui.summary.qualityLabel",
            }
        )

        if len(recommendations) >= 3:
            break

    return recommendations[:5]


def _build_risks(top_issues: list[dict[str, str]]) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []
    for index, issue in enumerate(top_issues):
        if issue.get("severity") != "high":
            continue

        code = issue.get("code", "")
        title = issue.get("title", "Риск техники")
        description = RISK_TEMPLATE_BY_CODE.get(code)
        if description is None:
            description = f"Высокий риск по зоне «{title}», требуется снижение нагрузки и контроль техники."

        risks.append(
            {
                "code": f"risk_{code}",
                "title": f"Риск: {title}",
                "description": description,
                "severity": "high",
                "evidenceRef": f"ui.topIssues[{index}].severity",
            }
        )

    return risks


def _motivation_for_quality(quality_label: str) -> str:
    motivational_map = {
        "отлично": "Сильный подход, закрепляйте текущую технику.",
        "хорошо": "Хороший результат, доведите стабильность до уровня «отлично».",
        "норм": "Нормальный уровень, сфокусируйтесь на ключевых корректировках.",
        "нужно улучшить": "Есть зона роста, снижайте темп и отрабатывайте технику по шагам.",
    }
    return motivational_map.get(quality_label, motivational_map["нужно улучшить"])


def _build_ui_block(reps: list[SavedRepPayload], aggregates: dict[str, Any]) -> dict[str, Any]:
    raw_score = aggregates.get("avgScore")
    score = float(raw_score) if isinstance(raw_score, (int, float)) else None
    quality_label = _quality_label(score)

    top_issues = _build_top_issues(reps, aggregates)
    recommendations = _build_recommendations(top_issues=top_issues, aggregates=aggregates)
    risks = _build_risks(top_issues=top_issues)

    return {
        "summary": {
            "score": round(score, 2) if isinstance(score, float) else None,
            "qualityLabel": quality_label,
            "repsCount": len(reps),
        },
        "topIssues": top_issues,
        "recommendations": recommendations,
        "risks": risks,
        "motivation": _motivation_for_quality(quality_label),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = (len(ordered) - 1) * (pct / 100.0)
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    if left == right:
        return ordered[left]
    weight = position - left
    return ordered[left] * (1.0 - weight) + ordered[right] * weight


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _round_number(value: float, precision: int = 4) -> float:
    return round(float(value), precision)


def _build_report_summary(reps: list[SavedRepPayload], aggregates: dict[str, Any]) -> dict[str, Any]:
    raw_avg = aggregates.get("avgScore")
    avg_score = _as_float(raw_avg)
    if avg_score is None:
        rep_scores = [float(rep.repScore) for rep in reps]
        avg_score = round(sum(rep_scores) / len(rep_scores), 2) if rep_scores else None

    quality_label = _quality_label(avg_score)
    return {
        "avgScore": _round_number(avg_score, 2) if avg_score is not None else None,
        "qualityLabel": quality_label,
        "repsCount": len(reps),
    }


def _top_unique(items: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _build_report_rep_breakdown(reps: list[SavedRepPayload]) -> list[dict[str, Any]]:
    rep_breakdown: list[dict[str, Any]] = []

    for rep in reps:
        numeric_metrics = {
            str(key): _round_number(float(value), 4)
            for key, value in rep.metrics.items()
            if _as_float(value) is not None
        }
        details = rep.details if isinstance(rep.details, dict) else {}
        score_breakdown = details.get("score_breakdown") if isinstance(details.get("score_breakdown"), dict) else None

        rep_breakdown.append(
            {
                "repIndex": rep.repIndex,
                "repScore": _round_number(float(rep.repScore), 2),
                "quality": _quality_label(float(rep.repScore)),
                "topErrors": _top_unique(rep.errors, 3),
                "topTips": _top_unique(rep.tips, 3),
                "keyMetrics": numeric_metrics,
                "scoreBreakdown": score_breakdown,
            }
        )

    return rep_breakdown


def _build_report_metric_stats(reps: list[SavedRepPayload]) -> dict[str, dict[str, float]]:
    metrics_accumulator: dict[str, list[float]] = {}

    for rep in reps:
        for key, value in rep.metrics.items():
            numeric = _as_float(value)
            if numeric is None:
                continue
            metrics_accumulator.setdefault(str(key), []).append(numeric)

    metric_stats: dict[str, dict[str, float]] = {}
    for key, values in metrics_accumulator.items():
        if not values:
            continue
        metric_stats[key] = {
            "min": _round_number(min(values), 4),
            "max": _round_number(max(values), 4),
            "mean": _round_number(sum(values) / len(values), 4),
            "p50": _round_number(_percentile(values, 50), 4),
            "p90": _round_number(_percentile(values, 90), 4),
        }

    return metric_stats


def _build_report_depth_stats(reps: list[SavedRepPayload]) -> dict[str, float]:
    depth_ratio_values: list[float] = []
    knee_ratio_values: list[float] = []
    min_knee_values: list[float] = []
    max_depth_delta_values: list[float] = []

    for rep in reps:
        depth_ratio = _as_float(rep.metrics.get("depth_ratio"))
        knee_ratio = _as_float(rep.metrics.get("knee_ratio"))
        min_knee = _as_float(rep.metrics.get("min_knee_angle"))
        max_depth_delta = _as_float(rep.metrics.get("max_depth_delta"))
        if depth_ratio is not None:
            depth_ratio_values.append(depth_ratio)
        if knee_ratio is not None:
            knee_ratio_values.append(knee_ratio)
        if min_knee is not None:
            min_knee_values.append(min_knee)
        if max_depth_delta is not None:
            max_depth_delta_values.append(max_depth_delta)

    return {
        "depthRatioMean": _round_number(sum(depth_ratio_values) / len(depth_ratio_values), 4) if depth_ratio_values else 0.0,
        "depthRatioP90": _round_number(_percentile(depth_ratio_values, 90), 4) if depth_ratio_values else 0.0,
        "kneeRatioMean": _round_number(sum(knee_ratio_values) / len(knee_ratio_values), 4) if knee_ratio_values else 0.0,
        "kneeRatioP90": _round_number(_percentile(knee_ratio_values, 90), 4) if knee_ratio_values else 0.0,
        "minKneeAngleMean": _round_number(sum(min_knee_values) / len(min_knee_values), 4) if min_knee_values else 0.0,
        "maxDepthDeltaMean": _round_number(sum(max_depth_delta_values) / len(max_depth_delta_values), 4) if max_depth_delta_values else 0.0,
    }


def _build_report_penalty_stats(reps: list[SavedRepPayload]) -> dict[str, dict[str, float]]:
    buckets: dict[str, list[float]] = {}
    for rep in reps:
        details = rep.details if isinstance(rep.details, dict) else {}
        breakdown = details.get("score_breakdown") if isinstance(details.get("score_breakdown"), dict) else {}
        penalty_parts = breakdown.get("penalty_parts") if isinstance(breakdown.get("penalty_parts"), dict) else {}
        for key, value in penalty_parts.items():
            numeric = _as_float(value)
            if numeric is None:
                continue
            buckets.setdefault(str(key), []).append(numeric)

    result: dict[str, dict[str, float]] = {}
    for key, values in buckets.items():
        if not values:
            continue
        result[key] = {
            "mean": _round_number(sum(values) / len(values), 4),
            "p90": _round_number(_percentile(values, 90), 4),
            "max": _round_number(max(values), 4),
        }
    return result


def _build_report_issue_stats(reps: list[SavedRepPayload]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for rep in reps:
        details = rep.details if isinstance(rep.details, dict) else {}
        hint_codes = details.get("hint_codes")
        if isinstance(hint_codes, list):
            for code in hint_codes:
                code_text = str(code).strip()
                if not code_text or code_text == "good_rep":
                    continue
                counter[code_text] += 1
    return dict(counter)


def _build_report_rule_flags(reps: list[SavedRepPayload]) -> dict[str, list[int]]:
    heel_fail_reps: list[int] = []
    undersquat_reps: list[int] = []
    undersquat_severe_reps: list[int] = []
    good_pose_reps: list[int] = []

    for rep in reps:
        details = rep.details if isinstance(rep.details, dict) else {}
        if bool(details.get("heel_fail")):
            heel_fail_reps.append(rep.repIndex)
        if bool(details.get("undersquat")):
            undersquat_reps.append(rep.repIndex)
        if bool(details.get("undersquat_severe")):
            undersquat_severe_reps.append(rep.repIndex)
        if bool(details.get("good_pose")) or bool(details.get("excellent_pose")):
            good_pose_reps.append(rep.repIndex)

    return {
        "heelFailReps": heel_fail_reps,
        "undersquatReps": undersquat_reps,
        "undersquatSevereReps": undersquat_severe_reps,
        "goodPoseReps": good_pose_reps,
    }


def _build_report_block(
    reps: list[SavedRepPayload],
    aggregates: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": "v2",
        "summary": _build_report_summary(reps, aggregates),
        "repBreakdown": _build_report_rep_breakdown(reps),
        "metricStats": _build_report_metric_stats(reps),
        "depthStats": _build_report_depth_stats(reps),
        "penaltyStats": _build_report_penalty_stats(reps),
        "issueStats": _build_report_issue_stats(reps),
        "ruleFlags": _build_report_rule_flags(reps),
        "promptReady": True,
    }


def _ensure_logs_dir() -> None:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось подготовить директорию для логов.",
        ) from exc


def _write_technique_log(
    *,
    exercise: str,
    session_id: str,
    reps: list[SavedRepPayload],
    aggregates: dict[str, Any] | None,
    current_user: User,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    _ensure_logs_dir()

    timestamp = datetime.now(timezone.utc)
    timestamp_human = timestamp.strftime("%Y-%m-%d__%H-%M-%S")
    session_safe = _sanitize_session_id(session_id)
    filename = f"{timestamp_human}__{exercise}__{session_safe}.json"
    target_path = LOGS_DIR / filename

    aggregates_block = aggregates or _build_aggregates(reps)
    ui_block = _build_ui_block(reps, aggregates_block)
    report_block = _build_report_block(reps, aggregates_block)
    output = {
        "meta": {
            "exercise": exercise,
            "timestamp": timestamp.isoformat(),
            "sessionId": session_id,
            "userId": current_user.id,
        },
        "reps": [item.model_dump() for item in reps],
        "aggregates": aggregates_block,
        "ui": ui_block,
        "report": report_block,
    }

    try:
        with target_path.open("w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить JSON-лог подхода.",
        ) from exc

    return str(target_path), aggregates_block, ui_block


def _posture_ok(motion_family: str, metric: TechniqueFrameMetric) -> bool:
    if motion_family in {"squat_like", "lunge_like"}:
        return (
            _float_or(metric.side_view_score, 0.0) >= 0.22
            and _float_or(metric.torso_angle, 90.0) <= 68.0
            and _float_or(metric.hip_ankle_vertical_norm, 0.0) >= 0.22
        )
    if motion_family == "push_like":
        return (
            _float_or(metric.side_view_score, 0.0) >= 0.35
            and _float_or(metric.posture_tilt_deg, 90.0) <= 34.0
            and _float_or(metric.hip_ankle_vertical_norm, 1.0) <= 0.45
        )
    return (
        _float_or(metric.side_view_score, 0.0) >= 0.35
        and _float_or(metric.posture_tilt_deg, 90.0) <= 48.0
    )


def _build_live_hint(
    *,
    exercise_slug: str,
    motion_family: str,
    metric: TechniqueFrameMetric,
    phase: str,
    baseline: TechniqueBaselineSnapshot | None,
) -> TechniqueLiveResponse:
    posture_ok = _posture_ok(motion_family, metric)
    primary_angle = _float_or(metric.primary_angle, 180.0)
    depth_norm = _float_or(metric.depth_norm, 0.0)
    torso_angle = _float_or(metric.torso_angle, 0.0)
    asymmetry = max(
        _float_or(metric.asymmetry, 0.0),
        _float_or(metric.hip_asymmetry, 0.0),
    )
    leg_angle = _float_or(metric.leg_angle, 180.0)
    heel_lift = _float_or(metric.heel_lift_norm, 0.0)
    side_view_score = _float_or(metric.side_view_score, 0.0)
    baseline_primary = _float_or(
        baseline.baseline_primary if baseline else None,
        primary_angle,
    )
    baseline_depth = _float_or(
        baseline.baseline_depth if baseline else None,
        depth_norm,
    )
    baseline_heel = max(
        0.0,
        _float_or(baseline.baseline_heel if baseline else None, 0.0),
    )
    primary_drop = max(0.0, baseline_primary - primary_angle)
    depth_delta = max(0.0, baseline_depth - depth_norm)
    heel_lift_delta = max(0.0, heel_lift - baseline_heel)

    hint = "Держите темп ровным."
    tone: Literal["low", "med", "high"] = "low"

    if not posture_ok:
        if motion_family in {"squat_like", "lunge_like"}:
            hint = "Встаньте боком к камере и держите корпус с ногами полностью в кадре."
        elif motion_family == "push_like":
            hint = "Повернитесь боком, примите упор лёжа и держите корпус ровной линией."
        else:
            hint = "Лягте боком к камере и оставьте корпус с ногами в кадре."
        tone = "high"
    elif motion_family in {"squat_like", "lunge_like"}:
        if (
            phase in ("DOWN", "RISING")
            and side_view_score >= 0.62
            and primary_drop >= 10.0
            and depth_delta >= 0.06
            and heel_lift_delta > 0.055
            and heel_lift > max(0.075, baseline_heel + 0.035)
        ):
            hint = "Пятки на пол, уменьшите глубину на 10-15%."
            tone = "high"
        elif phase == "DOWN" and primary_drop >= 12.0 and depth_delta < 0.055:
            hint = "Добавьте глубину приседа и не ускоряйтесь внизу."
            tone = "med"
        elif torso_angle > 52.0:
            hint = "Грудь выше и держите вес в середине стопы."
            tone = "med"
        elif asymmetry > 14.0:
            hint = "Двигайтесь симметрично: одинаковая глубина и скорость сторон."
            tone = "med"
        elif phase == "RISING":
            hint = "Поднимайтесь ровно, без рывка."
        else:
            hint = "Темп ровный, амплитуда стабильная."
    elif motion_family == "push_like":
        if leg_angle < 132.0:
            hint = "Выпрямите ноги сильнее и удерживайте корпус одной линией."
            tone = "high"
        elif torso_angle > 16.0 or _float_or(metric.posture_tilt_deg, 90.0) > 34.0:
            hint = "Подтяните корпус: не проваливайте таз и поясницу."
            tone = "med"
        elif phase == "DOWN" and primary_drop >= 18.0 and depth_delta < 0.055:
            hint = "Опуститесь чуть ниже и держите локти под контролем."
            tone = "med"
        elif asymmetry > 14.0:
            hint = "Держите руки и плечи симметрично по всей траектории."
            tone = "med"
        elif phase == "RISING":
            hint = "Поднимайтесь без рывка и не ломайте линию корпуса."
        else:
            hint = "Контролируйте локти и глубину без провала."
    else:
        if exercise_slug == "glute_bridge":
            bridge_rise = max(0.0, primary_angle - baseline_primary)
            if phase in ("DOWN", "RISING") and bridge_rise < 14.0:
                hint = "Поднимайте таз выше и фиксируйте верхнюю точку."
                tone = "med"
            elif asymmetry > 16.0:
                hint = "Поднимайте таз ровно, без перекоса сторон."
                tone = "med"
            else:
                hint = "Подъём таза плавный, опускайтесь под контролем."
        elif depth_delta < 0.03 and phase == "DOWN":
            hint = "Добавьте амплитуду без рывка."
            tone = "med"
        elif asymmetry > 18.0:
            hint = "Выравняйте движение сторон и не раскачивайтесь."
            tone = "med"
        elif phase == "RISING":
            hint = "Возвращайтесь в стартовую позицию без рывка."
        else:
            hint = "Корпус стабилен, темп ровный."

    return TechniqueLiveResponse(
        hint=hint,
        tone=tone,
        posture_ok=posture_ok,
        phase=phase,
        debug={
            "exercise": exercise_slug,
            "primary_drop": round(primary_drop, 4),
            "depth_delta": round(depth_delta, 4),
            "heel_lift_norm": round(heel_lift, 4),
            "heel_lift_delta": round(heel_lift_delta, 4),
            "baseline_heel": round(baseline_heel, 4),
            "torso_angle": round(torso_angle, 4),
            "asymmetry": round(asymmetry, 4),
            "leg_angle": round(leg_angle, 4),
            "side_view_score": round(side_view_score, 4),
            "posture_ok": posture_ok,
        },
    )


@router.post("/api/technique/sessions/start", response_model=TechniqueSessionStartResponse)
def start_technique_session(
    payload: TechniqueSessionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechniqueSessionStartResponse:
    exercise = _get_or_create_catalog_exercise(db, payload.exercise_slug)
    session = TechniqueSession(
        user_id=current_user.id,
        exercise_id=exercise.id,
        status="active",
        started_at=datetime.now(timezone.utc),
        reps_count=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return TechniqueSessionStartResponse(
        session_id=session.id,
        redirect_url=f"/app/technique/{session.id}",
        exercise=_serialize_exercise(exercise, payload.exercise_slug, db),
    )


@router.get("/api/technique/sessions/{session_id}", response_model=TechniqueSessionResponse)
def get_technique_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechniqueSessionResponse:
    session = _get_owned_technique_session(db, current_user.id, session_id)
    return _serialize_session(session)


@router.post("/api/technique/sessions/{session_id}/live", response_model=TechniqueLiveResponse)
def get_session_live_technique_hint(
    session_id: int,
    payload: TechniqueSessionLiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechniqueLiveResponse:
    session = _get_owned_technique_session(db, current_user.id, session_id)
    if session.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Technique-сессия уже завершена.")

    session_slug = _session_slug(session)
    reference_payload = _resolved_reference_payload(db, session_slug)
    return _build_live_hint(
        exercise_slug=session_slug,
        motion_family=str(reference_payload["motion_family"]),
        metric=payload.frame_metric,
        phase=payload.phase,
        baseline=payload.baseline_snapshot,
    )


@router.post("/api/technique/live/{exercise}", response_model=TechniqueLiveResponse)
def get_live_technique_hint(
    exercise: str,
    payload: TechniqueLiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechniqueLiveResponse:
    exercise_slug = exercise.strip().lower()
    if exercise_slug not in TECHNIQUE_EXERCISE_SLUGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Live-подсказки доступны только для канонических упражнений техники.",
        )

    session = _get_owned_technique_session(db, current_user.id, payload.session_id)
    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Technique-сессия уже завершена.",
        )

    session_slug = _session_slug(session)
    effective_slug = session_slug if session_slug in TECHNIQUE_EXERCISE_SLUGS else exercise_slug
    reference_payload = _resolved_reference_payload(db, effective_slug)

    return _build_live_hint(
        exercise_slug=effective_slug,
        motion_family=str(reference_payload["motion_family"]),
        metric=payload.frame_metric,
        phase=payload.phase,
        baseline=payload.baseline_snapshot,
    )


@router.post("/api/technique/sessions/{session_id}/finish", response_model=TechniqueSessionFinishResponse)
def finish_technique_session(
    session_id: int,
    payload: FinishTechniqueSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TechniqueSessionFinishResponse:
    session = _get_owned_technique_session(db, current_user.id, session_id)
    session_slug = _session_slug(session)
    effective_exercise = session_slug

    log_path: str | None = None
    ui_block: dict[str, Any] | None = None
    avg_score: float | None = None
    reps_count = len(payload.reps)

    if payload.reps:
        log_path, aggregates, ui_block = _write_technique_log(
            exercise=effective_exercise,
            session_id=str(session.id),
            reps=payload.reps,
            aggregates=payload.aggregates,
            current_user=current_user,
        )
        raw_avg = aggregates.get("avgScore")
        avg_score = float(raw_avg) if isinstance(raw_avg, (int, float)) else None

    session.status = "finished" if payload.reps else "stopped"
    session.ended_at = datetime.now(timezone.utc)
    session.reps_count = reps_count
    session.avg_score = avg_score
    session.log_path = log_path
    db.add(session)
    db.commit()
    db.refresh(session)

    return TechniqueSessionFinishResponse(
        ok=True,
        session_id=session.id,
        status=str(session.status),
        reps_count=int(session.reps_count or 0),
        avg_score=float(session.avg_score) if session.avg_score is not None else None,
        log_path=str(session.log_path) if session.log_path else None,
        redirect_url="/app/catalog",
        ui=ui_block,
    )


@router.post("/api/technique/sessions/{session_id}/compare", response_model=CompareResponse)
def compare_session_rep(
    session_id: int,
    payload: CompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompareResponse:
    session = _get_owned_technique_session(db, current_user.id, session_id)
    session_slug = _session_slug(session)
    frame_metrics = [item.model_dump() for item in payload.frame_metrics]

    if session_slug == "squat":
        legacy_result = compare_squat_rep(frame_metrics)
        return CompareResponse(
            rep_index=payload.rep_index,
            rep_score=legacy_result.rep_score,
            quality=legacy_result.quality,
            errors=legacy_result.errors,
            tips=legacy_result.tips,
            metrics=legacy_result.metrics,
            details=legacy_result.details,
        )

    reference_payload = _resolved_reference_payload(db, session_slug)
    if reference_payload["reference_model"] and reference_payload["calibration_profile"]:
        result = compare_generated_rep(
            frame_metrics=frame_metrics,
            reference_model=reference_payload["reference_model"],
            calibration_profile=reference_payload["calibration_profile"],
        )
        return CompareResponse(
            rep_index=payload.rep_index,
            rep_score=int(result["rep_score"]),
            quality=str(result["quality"]),
            errors=list(result["errors"]),
            tips=list(result["tips"]),
            metrics=dict(result["metrics"]),
            details=dict(result["details"]),
        )

    if session_slug == "pushup":
        legacy_result = compare_pushup_rep(frame_metrics)
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Для этого упражнения эталон ещё не опубликован. Запустите импорт системных reference-профилей.",
        )

    return CompareResponse(
        rep_index=payload.rep_index,
        rep_score=legacy_result.rep_score,
        quality=legacy_result.quality,
        errors=legacy_result.errors,
        tips=legacy_result.tips,
        metrics=legacy_result.metrics,
        details=legacy_result.details,
    )


@router.post("/api/compare/squat", response_model=CompareResponse)
def compare_squat(
    payload: CompareRequest,
    current_user: User = Depends(get_current_user),
) -> CompareResponse:
    _ = current_user
    result = compare_squat_rep([item.model_dump() for item in payload.frame_metrics])
    return CompareResponse(
        rep_index=payload.rep_index,
        rep_score=result.rep_score,
        quality=result.quality,
        errors=result.errors,
        tips=result.tips,
        metrics=result.metrics,
        details=result.details,
    )


@router.post("/api/compare/pushup", response_model=CompareResponse)
def compare_pushup(
    payload: CompareRequest,
    current_user: User = Depends(get_current_user),
) -> CompareResponse:
    _ = current_user
    result = compare_pushup_rep([item.model_dump() for item in payload.frame_metrics])
    return CompareResponse(
        rep_index=payload.rep_index,
        rep_score=result.rep_score,
        quality=result.quality,
        errors=result.errors,
        tips=result.tips,
        metrics=result.metrics,
        details=result.details,
    )


@router.post("/api/logs/save", response_model=SaveTechniqueLogResponse)
def save_technique_log(
    payload: SaveTechniqueLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaveTechniqueLogResponse:
    file_path, _, _ = _write_technique_log(
        exercise=payload.exercise,
        session_id=payload.sessionId,
        reps=payload.reps,
        aggregates=payload.aggregates,
        current_user=current_user,
    )
    return SaveTechniqueLogResponse(ok=True, file_path=file_path)
