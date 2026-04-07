from __future__ import annotations

import logging
import threading
from typing import Any

from app.services.personalized_plan import build_plan_signature, generate_personalized_plan
from app.schemas.plan import PersonalizedPlanResponse
from app.services.personalized_plan_store import (
    is_complete_personalized_plan,
    read_cached_personalized_plan,
    write_cached_personalized_plan,
)

logger = logging.getLogger(__name__)

_state_lock = threading.Lock()
_running_jobs: set[str] = set()
PLAN_WARMUP_ATTEMPTS = 1


def _job_key(user_id: int, signature: str) -> str:
    return f"{int(user_id)}:{signature}"


def is_personalized_plan_generation_running(user_id: int, signature: str) -> bool:
    with _state_lock:
        return _job_key(user_id, signature) in _running_jobs


def _begin_job(user_id: int, signature: str) -> bool:
    key = _job_key(user_id, signature)
    with _state_lock:
        if key in _running_jobs:
            return False
        _running_jobs.add(key)
        return True


def _finish_job(user_id: int, signature: str) -> None:
    key = _job_key(user_id, signature)
    with _state_lock:
        _running_jobs.discard(key)


def generate_and_cache_personalized_plan(
    user_id: int,
    snapshot: dict[str, Any],
    *,
    force: bool = False,
) -> tuple[str, PersonalizedPlanResponse | None]:
    signature = build_plan_signature(snapshot["data"], snapshot=snapshot)
    if not force:
        cached = read_cached_personalized_plan(user_id, signature)
        if cached is not None:
            return signature, cached

    for attempt in range(1, PLAN_WARMUP_ATTEMPTS + 1):
        plan = generate_personalized_plan(snapshot["data"], snapshot=snapshot)
        if is_complete_personalized_plan(plan):
            write_cached_personalized_plan(user_id, plan)
            logger.info(
                "Personalized plan cached | user_id=%s | signature=%s | attempt=%s",
                user_id,
                signature,
                attempt,
            )
            return signature, plan
        logger.warning(
            "Plan generation returned incomplete payload | user_id=%s | signature=%s | attempt=%s | source=%s",
            user_id,
            signature,
            attempt,
            plan.source,
        )
    return signature, None


def schedule_personalized_plan_generation(
    user_id: int,
    snapshot: dict[str, Any],
    *,
    force: bool = False,
) -> tuple[str, bool]:
    signature = build_plan_signature(snapshot["data"], snapshot=snapshot)
    if not force and read_cached_personalized_plan(user_id, signature) is not None:
        return signature, False
    if not _begin_job(user_id, signature):
        return signature, False

    def worker() -> None:
        try:
            _signature, plan = generate_and_cache_personalized_plan(user_id, snapshot, force=force)
            if plan is not None:
                logger.info(
                    "Personalized plan cached in background | user_id=%s | signature=%s",
                    user_id,
                    _signature,
                )
                return
        except Exception as exc:  # pragma: no cover - defensive background guard
            logger.warning(
                "Background plan generation crashed | user_id=%s | signature=%s | error=%s",
                user_id,
                signature,
                exc,
            )
        finally:
            _finish_job(user_id, signature)

    thread = threading.Thread(
        target=worker,
        name=f"plan-gen-{user_id}-{signature[:8]}",
        daemon=True,
    )
    thread.start()
    return signature, True
