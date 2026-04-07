import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.core.onboarding import (
    DEFAULT_ONBOARDING_VERSION,
    dump_json_list,
    empty_onboarding_data,
    main_goal_to_goal_type,
    merge_onboarding_data,
    parse_json_list,
    resolve_onboarding_status,
    resolve_resume_step,
    validate_onboarding_data,
    build_goal_target_value,
    build_onboarding_derived,
)
from app.core.config import settings
from app.core.telegram import send_telegram_message
from app.crud.onboarding import get_effective_user_onboarding, get_or_create_user_onboarding, get_user_onboarding
from app.crud.profile import get_or_create_profile
from app.models.goal import Goal
from app.models.user import User
from app.services.first_interview_snapshot import ensure_first_interview_snapshot
from app.services.personalized_plan_jobs import (
    generate_and_cache_personalized_plan,
    schedule_personalized_plan_generation,
)
from app.services.personalized_plan_store import clear_latest_cached_personalized_plan
from app.schemas.onboarding import (
    OnboardingCompleteResponse,
    OnboardingDataResponse,
    OnboardingDerivedResponse,
    OnboardingPatchRequest,
    OnboardingResetResponse,
    OnboardingStateResponse,
)

router = APIRouter(tags=["onboarding"])
logger = logging.getLogger(__name__)
PLAN_GENERATION_UNAVAILABLE_CODE = "PLAN_GENERATION_UNAVAILABLE"


def _row_to_data(record) -> dict[str, object]:
    if record is None:
        return empty_onboarding_data()

    return {
        "main_goal": record.main_goal,
        "motivation": record.motivation,
        "desired_outcome": record.desired_outcome,
        "focus_area": record.focus_area,
        "gender": record.gender,
        "current_body_shape": record.current_body_shape,
        "target_body_shape": record.target_body_shape,
        "age": record.age,
        "height_cm": record.height_cm,
        "current_weight_kg": record.current_weight_kg,
        "target_weight_kg": record.target_weight_kg,
        "fitness_level": record.fitness_level,
        "activity_level": record.activity_level,
        "goal_pace": record.goal_pace,
        "training_frequency": record.training_frequency,
        "calorie_tracking": record.calorie_tracking,
        "diet_type": record.diet_type,
        "self_image": record.self_image,
        "reminders_enabled": bool(record.reminders_enabled),
        "reminder_time_local": record.reminder_time_local,
        "onboarding_version": record.onboarding_version or DEFAULT_ONBOARDING_VERSION,
        "interest_tags": parse_json_list(record.interest_tags),
        "equipment_tags": parse_json_list(record.equipment_tags),
        "injury_areas": parse_json_list(record.injury_areas),
        "training_days": parse_json_list(record.training_days),
    }


def _apply_snapshot(record, data: dict[str, object]) -> None:
    record.main_goal = data.get("main_goal")
    record.motivation = data.get("motivation")
    record.desired_outcome = data.get("desired_outcome")
    record.focus_area = data.get("focus_area")
    record.gender = data.get("gender")
    record.current_body_shape = data.get("current_body_shape")
    record.target_body_shape = data.get("target_body_shape")
    record.age = data.get("age")
    record.height_cm = data.get("height_cm")
    record.current_weight_kg = data.get("current_weight_kg")
    record.target_weight_kg = data.get("target_weight_kg")
    record.fitness_level = data.get("fitness_level")
    record.activity_level = data.get("activity_level")
    record.goal_pace = data.get("goal_pace")
    record.training_frequency = data.get("training_frequency")
    record.calorie_tracking = data.get("calorie_tracking")
    record.diet_type = data.get("diet_type")
    record.self_image = data.get("self_image")
    record.reminders_enabled = bool(data.get("reminders_enabled"))
    record.reminder_time_local = data.get("reminder_time_local")
    record.onboarding_version = str(data.get("onboarding_version") or DEFAULT_ONBOARDING_VERSION)
    record.interest_tags = dump_json_list(data.get("interest_tags"))
    record.equipment_tags = dump_json_list(data.get("equipment_tags"))
    record.injury_areas = dump_json_list(data.get("injury_areas"))
    record.training_days = dump_json_list(data.get("training_days"))


def _state_response(record) -> OnboardingStateResponse:
    data = _row_to_data(record)
    is_completed = bool(record and record.is_completed)
    derived = build_onboarding_derived(data)
    return OnboardingStateResponse(
        status=resolve_onboarding_status(data, is_completed),
        is_completed=is_completed,
        resume_step=resolve_resume_step(data, is_completed),
        data=OnboardingDataResponse(**data),
        derived=OnboardingDerivedResponse(**derived),
    )


def _upsert_goal(db: Session, user_id: int, main_goal: str | None, goal_target_value: str | None) -> None:
    goal_type = main_goal_to_goal_type(main_goal)
    if goal_type is None or not goal_target_value:
        return

    goal = db.query(Goal).filter(Goal.user_id == user_id).one_or_none()
    if goal is None:
        goal = Goal(user_id=user_id, goal_type=goal_type, target_value=goal_target_value)
        db.add(goal)
        return

    goal.goal_type = goal_type
    goal.target_value = goal_target_value


@router.get("/api/onboarding", response_model=OnboardingStateResponse)
def get_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingStateResponse:
    return _state_response(get_effective_user_onboarding(db, current_user.id))


@router.patch("/api/onboarding", response_model=OnboardingStateResponse)
def patch_onboarding(
    payload: OnboardingPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingStateResponse:
    current_record = get_user_onboarding(db, current_user.id)
    current_data = _row_to_data(current_record)
    incoming = payload.model_dump(exclude_unset=True)
    if not incoming:
        return _state_response(current_record)

    candidate = merge_onboarding_data(current_data, incoming)
    try:
        validate_onboarding_data(candidate, require_complete=False)
        record = get_or_create_user_onboarding(db, current_user.id)
        _apply_snapshot(record, candidate)
        db.commit()
        db.refresh(record)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить шаг onboarding.",
        ) from exc

    return _state_response(record)


@router.post("/api/onboarding/complete", response_model=OnboardingCompleteResponse)
def complete_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingCompleteResponse:
    record = get_user_onboarding(db, current_user.id)
    candidate = _row_to_data(record)

    try:
        validate_onboarding_data(candidate, require_complete=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        record = get_or_create_user_onboarding(db, current_user.id)
        _apply_snapshot(record, candidate)
        record.is_completed = True
        record.completed_at = datetime.now(timezone.utc)

        profile = get_or_create_profile(db, current_user.id)
        profile.height_cm = candidate.get("height_cm")
        current_weight = candidate.get("current_weight_kg")
        profile.weight_kg = int(round(float(current_weight))) if isinstance(current_weight, (int, float)) else None
        profile.age = candidate.get("age")
        profile.level = candidate.get("fitness_level") if candidate.get("fitness_level") in {"beginner", "intermediate", "advanced"} else None

        derived = build_onboarding_derived(candidate)
        goal_target_value = build_goal_target_value(candidate, derived)
        _upsert_goal(db, current_user.id, candidate.get("main_goal"), goal_target_value)

        db.commit()
        db.refresh(record)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось завершить onboarding.",
        ) from exc

    try:
        clear_latest_cached_personalized_plan(current_user.id)
        snapshot = ensure_first_interview_snapshot(
            current_user.id,
            candidate,
            completed_at=record.completed_at,
            overwrite=True,
        )
        _signature, generated_plan = generate_and_cache_personalized_plan(current_user.id, snapshot)
        plan_ready = generated_plan is not None
        if not plan_ready:
            schedule_personalized_plan_generation(current_user.id, snapshot, force=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": PLAN_GENERATION_UNAVAILABLE_CODE,
                    "message": "Интервью сохранено, но Mistral еще не успел собрать итоговый план. Откройте вкладку плана еще раз через несколько секунд.",
                },
            )
    except OSError as exc:
        logger.warning("Failed to persist first interview snapshot for user_id=%s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить данные первого интервью.",
        ) from exc

    state = _state_response(record)
    return OnboardingCompleteResponse(
        **state.model_dump(),
        completed_at=record.completed_at,
        plan_ready=plan_ready,
        plan=generated_plan,
    )


@router.post("/api/onboarding/reset", response_model=OnboardingResetResponse)
def reset_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OnboardingResetResponse:
    record = get_user_onboarding(db, current_user.id)

    try:
        if record is None:
            record = get_or_create_user_onboarding(db, current_user.id)

        _apply_snapshot(record, empty_onboarding_data())
        record.is_completed = False
        record.completed_at = None
        db.add(record)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось очистить данные onboarding.",
        ) from exc

    telegram_notification_sent = False
    if current_user.telegram_user_id and settings.telegram_bot_token:
        try:
            send_telegram_message(
                settings.telegram_bot_token,
                str(current_user.telegram_user_id),
                "Данные onboarding очищены. Можно пройти приветственное интервью заново.",
            )
            telegram_notification_sent = True
        except Exception as exc:  # pragma: no cover - best effort notification
            logger.warning(
                "Failed to send onboarding reset confirmation to telegram_user_id=%s: %s",
                current_user.telegram_user_id,
                exc,
            )

    return OnboardingResetResponse(
        ok=True,
        message="Onboarding очищен. Можно пройти сценарий заново.",
        telegram_notification_sent=telegram_notification_sent,
    )
