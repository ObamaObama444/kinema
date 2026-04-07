from datetime import datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.workout import WorkoutSession


WORKOUT_STATUS_STARTED = "started"
WORKOUT_STATUS_FINISHED = "finished"
WORKOUT_STATUS_STOPPED = "stopped"


def create_workout_session(db: Session, user_id: int, program_id: int) -> WorkoutSession:
    session = WorkoutSession(
        user_id=user_id,
        program_id=program_id,
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        status=WORKOUT_STATUS_STARTED,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_workout_session_by_id(
    db: Session,
    session_id: int,
    user_id: int,
) -> WorkoutSession | None:
    stmt: Select[tuple[WorkoutSession]] = select(WorkoutSession).where(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()
