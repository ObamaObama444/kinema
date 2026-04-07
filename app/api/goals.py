from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.crud.goal import GoalAlreadyExistsError, create_goal, delete_goal_by_user_id, get_goal_by_user_id, get_goals_by_user_id
from app.models.user import User
from app.schemas.goal import GoalCreateRequest, GoalResponse

router = APIRouter(tags=["goals"])


@router.get("/api/goals", response_model=list[GoalResponse])
def list_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GoalResponse]:
    goals = get_goals_by_user_id(db, current_user.id)
    return [GoalResponse.model_validate(goal) for goal in goals]


@router.post("/api/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def add_goal(
    payload: GoalCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    try:
        goal = create_goal(
            db=db,
            user_id=current_user.id,
            goal_type=payload.goal_type,
            target_value=payload.target_value,
        )
    except GoalAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У вас уже есть цель. Сначала удалите текущую цель.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать цель. Попробуйте позже.",
        ) from exc

    return GoalResponse.model_validate(goal)


@router.delete("/api/goals/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        deleted = delete_goal_by_user_id(db, current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить цель. Попробуйте позже.",
        ) from exc

    if not deleted:
        goal = get_goal_by_user_id(db, current_user.id)
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Текущая цель не найдена.",
            )
