from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.onboarding import build_onboarding_derived

logger = logging.getLogger(__name__)

SNAPSHOT_VERSION = "v1"


def _snapshot_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "first_interviews"


def _snapshot_path(user_id: int) -> Path:
    return _snapshot_dir() / f"user_{int(user_id)}_first_interview.json"


def _normalize_timestamp(value: datetime | None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.isoformat()


def _build_payload(user_id: int, data: dict[str, object], completed_at: datetime | None) -> dict[str, Any]:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "user_id": int(user_id),
        "saved_at": _normalize_timestamp(datetime.now(timezone.utc)),
        "completed_at": _normalize_timestamp(completed_at),
        "data": data,
        "derived": build_onboarding_derived(data),
    }


def read_first_interview_snapshot(user_id: int) -> dict[str, Any] | None:
    path = _snapshot_path(user_id)
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read first interview snapshot for user_id=%s: %s", user_id, exc)
        return None

    if not isinstance(raw, dict) or not isinstance(raw.get("data"), dict):
        return None
    return raw


def ensure_first_interview_snapshot(
    user_id: int,
    data: dict[str, object],
    *,
    completed_at: datetime | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    existing = read_first_interview_snapshot(user_id)
    if existing is not None and not overwrite:
        return existing

    payload = _build_payload(user_id, data, completed_at)
    path = _snapshot_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)
    return payload
