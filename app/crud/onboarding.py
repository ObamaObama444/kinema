from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.onboarding import DEFAULT_ONBOARDING_VERSION
from app.models.goal import Goal
from app.models.onboarding import UserOnboarding
from app.models.profile import Profile
from app.models.weight_entry import WeightEntry
from app.models.workout import WorkoutSession

_TARGET_WEIGHT_PATTERN = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*кг", re.IGNORECASE)


def _main_goal_from_goal_type(goal_type: str | None) -> str | None:
    mapping = {
        "weight_loss": "lose_weight",
        "muscle_gain": "gain_muscle",
        "endurance": "stay_fit",
    }
    return mapping.get((goal_type or "").strip().lower())


def _parse_target_weight_kg(target_value: str | None) -> float | None:
    raw_value = (target_value or "").strip()
    if not raw_value:
        return None

    match = _TARGET_WEIGHT_PATTERN.search(raw_value)
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _has_profile_seed_data(profile: Profile | None) -> bool:
    if profile is None:
        return False

    return any(
        value is not None
        for value in (
            profile.height_cm,
            profile.weight_kg,
            profile.age,
            profile.level,
            profile.active_program_id,
            profile.workouts_per_week,
        )
    )


def _has_legacy_app_data(db: Session, user_id: int) -> tuple[Profile | None, Goal | None, bool]:
    profile_stmt: Select[tuple[Profile]] = select(Profile).where(Profile.user_id == user_id)
    goal_stmt: Select[tuple[Goal]] = select(Goal).where(Goal.user_id == user_id)
    weight_stmt: Select[tuple[int]] = select(WeightEntry.id).where(WeightEntry.user_id == user_id).limit(1)
    workout_stmt: Select[tuple[int]] = select(WorkoutSession.id).where(WorkoutSession.user_id == user_id).limit(1)

    profile = db.execute(profile_stmt).scalar_one_or_none()
    goal = db.execute(goal_stmt).scalar_one_or_none()
    has_history = (
        db.execute(weight_stmt).scalar_one_or_none() is not None
        or db.execute(workout_stmt).scalar_one_or_none() is not None
    )
    return profile, goal, has_history


def get_user_onboarding(db: Session, user_id: int) -> UserOnboarding | None:
    stmt = select(UserOnboarding).where(UserOnboarding.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_effective_user_onboarding(db: Session, user_id: int) -> UserOnboarding | None:
    onboarding = get_user_onboarding(db, user_id)
    if onboarding is not None:
        return onboarding

    profile, goal, has_history = _has_legacy_app_data(db, user_id)
    if not _has_profile_seed_data(profile) and goal is None and not has_history:
        return None

    onboarding = UserOnboarding(
        user_id=user_id,
        is_completed=True,
        completed_at=datetime.now(timezone.utc),
        onboarding_version=DEFAULT_ONBOARDING_VERSION,
    )

    if profile is not None:
        onboarding.height_cm = profile.height_cm
        onboarding.current_weight_kg = float(profile.weight_kg) if profile.weight_kg is not None else None
        onboarding.age = profile.age
        onboarding.fitness_level = profile.level if profile.level in {"beginner", "intermediate", "advanced"} else None
        onboarding.training_frequency = profile.workouts_per_week

    if goal is not None:
        onboarding.main_goal = _main_goal_from_goal_type(goal.goal_type)
        onboarding.target_weight_kg = _parse_target_weight_kg(goal.target_value)

    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)
    return onboarding


def get_or_create_user_onboarding(db: Session, user_id: int) -> UserOnboarding:
    onboarding = get_user_onboarding(db, user_id)
    if onboarding is None:
        onboarding = UserOnboarding(user_id=user_id)
        db.add(onboarding)
        db.flush()
    return onboarding
