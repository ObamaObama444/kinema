from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.plan import PersonalizedPlanResponse

logger = logging.getLogger(__name__)
PLAN_CACHE_SCHEMA_VERSION = "v3"
SUPPORTED_PLAN_CACHE_SCHEMA_VERSIONS = {"v2", PLAN_CACHE_SCHEMA_VERSION}
ALLOWED_PLAN_SOURCES = {"mistral", "fallback"}


def _plan_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "personalized_plans"


def _plan_path(user_id: int, signature: str) -> Path:
    normalized_signature = str(signature or "").strip() or "latest"
    return _plan_dir() / f"user_{int(user_id)}_{normalized_signature}.json"


def _latest_plan_path(user_id: int) -> Path:
    return _plan_dir() / f"user_{int(user_id)}_latest.json"


def is_complete_personalized_plan(plan: PersonalizedPlanResponse) -> bool:
    if str(plan.source or "").strip() not in ALLOWED_PLAN_SOURCES:
        return False
    if not str(plan.headline or "").strip():
        return False
    if not str(plan.subheadline or "").strip():
        return False
    if len(plan.tags) == 0:
        return False
    if len(plan.summary_items) == 0:
        return False
    if len(plan.stages) != 1:
        return False

    total_days = 0
    for stage in plan.stages:
        if len(stage.days) == 0:
            return False
        for day in stage.days:
            total_days += 1
            if not str(day.title or "").strip():
                return False
            if len(day.exercises) == 0:
                return False
            for exercise in day.exercises:
                if not str(exercise.title or "").strip():
                    return False
                if int(exercise.sets) <= 0 or int(exercise.reps) <= 0:
                    return False
    return total_days == 10


def _attach_user_id(plan: PersonalizedPlanResponse, user_id: int | None) -> PersonalizedPlanResponse:
    if user_id is None:
        return plan
    if plan.user_id == int(user_id):
        return plan
    return plan.model_copy(update={"user_id": int(user_id)})


def _normalize_cached_plan_shape(plan: PersonalizedPlanResponse) -> PersonalizedPlanResponse:
    if len(plan.stages) <= 1:
        return plan
    first_stage = plan.stages[0].model_copy(update={"days": list(plan.stages[0].days)[:10]})
    return plan.model_copy(update={"stages": [first_stage]})


def _extract_cached_plan(payload: Any, *, expected_user_id: int | None = None) -> PersonalizedPlanResponse | None:
    if not isinstance(payload, dict):
        return None
    if str(payload.get("schema_version") or "") not in SUPPORTED_PLAN_CACHE_SCHEMA_VERSIONS:
        return None
    raw_plan = payload.get("plan")
    if not isinstance(raw_plan, dict):
        return None

    try:
        plan = PersonalizedPlanResponse.model_validate(raw_plan)
    except Exception as exc:  # pragma: no cover - defensive cache recovery
        logger.warning("Failed to validate personalized plan cache payload: %s", exc)
        return None

    payload_user_id = payload.get("user_id")
    normalized_expected_user_id = int(expected_user_id) if expected_user_id is not None else None
    normalized_payload_user_id = int(payload_user_id) if isinstance(payload_user_id, int) else None
    normalized_plan_user_id = int(plan.user_id) if plan.user_id is not None else None

    plan = _normalize_cached_plan_shape(plan)

    if normalized_expected_user_id is not None:
        if normalized_payload_user_id is not None and normalized_payload_user_id != normalized_expected_user_id:
            logger.warning(
                "Discarding personalized plan cache because payload user_id=%s does not match expected_user_id=%s.",
                normalized_payload_user_id,
                normalized_expected_user_id,
            )
            return None
        if normalized_plan_user_id is not None and normalized_plan_user_id != normalized_expected_user_id:
            logger.warning(
                "Discarding personalized plan cache because plan user_id=%s does not match expected_user_id=%s.",
                normalized_plan_user_id,
                normalized_expected_user_id,
            )
            return None
        plan = _attach_user_id(plan, normalized_expected_user_id)
    elif normalized_payload_user_id is not None:
        plan = _attach_user_id(plan, normalized_payload_user_id)

    if not is_complete_personalized_plan(plan):
        logger.warning("Discarding personalized plan cache because it is incomplete or has unsupported source.")
        return None
    return plan


def _read_cached_personalized_plan_from_path(path: Path, *, user_id: int) -> PersonalizedPlanResponse | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read personalized plan cache for user_id=%s: %s", user_id, exc)
        return None

    plan = _extract_cached_plan(payload, expected_user_id=user_id)
    if plan is None:
        logger.warning("Ignoring invalid personalized plan cache for user_id=%s.", user_id)
    return plan


def read_cached_personalized_plan(user_id: int, signature: str) -> PersonalizedPlanResponse | None:
    return _read_cached_personalized_plan_from_path(_plan_path(user_id, signature), user_id=user_id)


def read_latest_cached_personalized_plan(user_id: int) -> PersonalizedPlanResponse | None:
    return _read_cached_personalized_plan_from_path(_latest_plan_path(user_id), user_id=user_id)


def clear_latest_cached_personalized_plan(user_id: int) -> None:
    try:
        _latest_plan_path(user_id).unlink(missing_ok=True)
    except OSError:
        return


def write_cached_personalized_plan(user_id: int, plan: PersonalizedPlanResponse) -> None:
    plan_with_user = _attach_user_id(plan, user_id)
    if not is_complete_personalized_plan(plan_with_user):
        raise ValueError("Only complete personalized plans can be cached.")

    cache_dir = _plan_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PLAN_CACHE_SCHEMA_VERSION,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "user_id": int(user_id),
        "plan": plan_with_user.model_dump(mode="json"),
    }

    for path in (_plan_path(user_id, plan_with_user.signature), _latest_plan_path(user_id)):
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)
