from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal


class GoalAlreadyExistsError(ValueError):
    pass


def get_goal_by_user_id(db: Session, user_id: int) -> Goal | None:
    stmt = select(Goal).where(Goal.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_goals_by_user_id(db: Session, user_id: int) -> list[Goal]:
    goal = get_goal_by_user_id(db, user_id)
    return [goal] if goal is not None else []


def create_goal(db: Session, user_id: int, goal_type: str, target_value: str) -> Goal:
    existing = get_goal_by_user_id(db, user_id)
    if existing is not None:
        raise GoalAlreadyExistsError("У пользователя уже есть цель.")

    goal = Goal(
        user_id=user_id,
        goal_type=goal_type,
        target_value=target_value,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal_by_user_id(db: Session, user_id: int) -> bool:
    goal = get_goal_by_user_id(db, user_id)
    if goal is None:
        return False

    db.delete(goal)
    db.commit()
    return True
