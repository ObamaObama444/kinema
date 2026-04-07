from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.core.onboarding import parse_json_list
from app.crud.onboarding import get_effective_user_onboarding
from app.models.user import User
from app.schemas.plan import PersonalizedPlanResponse
from app.services.first_interview_snapshot import ensure_first_interview_snapshot, read_first_interview_snapshot
from app.services.personalized_plan import build_plan_signature
from app.services.personalized_plan_jobs import (
    generate_and_cache_personalized_plan,
    is_personalized_plan_generation_running,
    schedule_personalized_plan_generation,
)
from app.services.personalized_plan_store import (
    read_cached_personalized_plan,
    read_latest_cached_personalized_plan,
)

router = APIRouter(tags=["plan"])
PLAN_GENERATION_UNAVAILABLE_CODE = "PLAN_GENERATION_UNAVAILABLE"


def _onboarding_row_to_data(record) -> dict[str, object]:
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
        "interest_tags": parse_json_list(record.interest_tags),
        "equipment_tags": parse_json_list(record.equipment_tags),
        "injury_areas": parse_json_list(record.injury_areas),
        "training_days": parse_json_list(record.training_days),
    }


def _plan_generation_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": PLAN_GENERATION_UNAVAILABLE_CODE,
            "message": "План еще собирается. Повторите попытку через несколько секунд.",
        },
    )


@router.get("/api/plan", response_model=PersonalizedPlanResponse)
def get_personalized_plan(
    refresh: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PersonalizedPlanResponse:
    snapshot = read_first_interview_snapshot(current_user.id)
    if snapshot is None:
        onboarding = get_effective_user_onboarding(db, current_user.id)
        if onboarding is None or not onboarding.is_completed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Onboarding не найден. Сначала завершите первое интервью.",
            )
        snapshot = ensure_first_interview_snapshot(
            current_user.id,
            _onboarding_row_to_data(onboarding),
            completed_at=onboarding.completed_at,
            overwrite=False,
        )

    signature = build_plan_signature(snapshot["data"], snapshot=snapshot)
    cached = read_cached_personalized_plan(current_user.id, signature)
    if cached is None:
        cached = read_latest_cached_personalized_plan(current_user.id)
    if cached is not None and not refresh:
        return cached

    if refresh:
        _signature, plan = generate_and_cache_personalized_plan(current_user.id, snapshot, force=True)
        if plan is not None:
            return plan
        if cached is not None:
            schedule_personalized_plan_generation(current_user.id, snapshot, force=True)
            return cached
        raise _plan_generation_unavailable()

    if cached is not None:
        return cached

    if not is_personalized_plan_generation_running(current_user.id, signature):
        schedule_personalized_plan_generation(current_user.id, snapshot)
    raise _plan_generation_unavailable()
