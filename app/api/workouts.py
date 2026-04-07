from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.crud.notification import create_notification_safe
from app.crud.program import get_program_with_exercises
from app.crud.workout import (
    WORKOUT_STATUS_STARTED,
    WORKOUT_STATUS_STOPPED,
    create_workout_session,
    get_workout_session_by_id,
)
from app.models.program_exercise import ProgramExercise
from app.models.user import User
from app.models.workout import WorkoutSetLog
from app.schemas.program import WorkoutStartRequest, WorkoutStartResponse

router = APIRouter(tags=["workouts"])


class WorkoutSessionStateResponse(BaseModel):
    session_id: int
    program_id: int
    status: str


class WorkoutStopResponse(BaseModel):
    redirect_url: str


class WorkoutLogRequest(BaseModel):
    exercise_id: int | None = None
    set_number: int = Field(ge=1)
    reps_done: int = Field(ge=0)
    form_score_mock: int = Field(ge=0, le=100)  # MOCK
    notes_mock: str | None = Field(default=None, max_length=1000)  # MOCK

    @field_validator("notes_mock")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class WorkoutLogResponse(BaseModel):
    ok: bool


def _session_or_404(db: Session, user_id: int, session_id: int):
    session = get_workout_session_by_id(db, session_id=session_id, user_id=user_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тренировочная сессия не найдена.",
        )
    return session


def _resolve_exercise_id(db: Session, session_id: int, program_id: int, requested_exercise_id: int | None) -> int:
    if requested_exercise_id is not None:
        exists_stmt = select(ProgramExercise.id).where(
            ProgramExercise.program_id == program_id,
            ProgramExercise.exercise_id == requested_exercise_id,
        )
        exists = db.execute(exists_stmt).scalar_one_or_none()
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанное упражнение не относится к программе этой сессии.",
            )
        return requested_exercise_id

    fallback_stmt = (
        select(ProgramExercise.exercise_id)
        .where(ProgramExercise.program_id == program_id)
        .order_by(ProgramExercise.order)
        .limit(1)
    )
    fallback_exercise_id = db.execute(fallback_stmt).scalar_one_or_none()
    if fallback_exercise_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Для сессии #{session_id} не найдено упражнений для логирования.",
        )

    return int(fallback_exercise_id)


@router.post("/api/workouts/start", response_model=WorkoutStartResponse)
def start_workout(
    payload: WorkoutStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutStartResponse:
    try:
        program = get_program_with_exercises(db, payload.program_id, user_id=current_user.id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось запустить тренировку.",
        ) from exc

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выбранная программа не найдена.",
        )

    try:
        session = create_workout_session(
            db=db,
            user_id=current_user.id,
            program_id=program.id,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать тренировочную сессию.",
        ) from exc

    return WorkoutStartResponse(
        session_id=session.id,
        redirect_url="/app/catalog",
    )


@router.get("/api/workouts/{session_id}", response_model=WorkoutSessionStateResponse)
def get_workout_session_state(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutSessionStateResponse:
    session = _session_or_404(db, user_id=current_user.id, session_id=session_id)
    return WorkoutSessionStateResponse(
        session_id=session.id,
        program_id=session.program_id,
        status=session.status,
    )


@router.post("/api/workouts/{session_id}/stop", response_model=WorkoutStopResponse)
def stop_workout_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutStopResponse:
    session = _session_or_404(db, user_id=current_user.id, session_id=session_id)

    try:
        if session.status != WORKOUT_STATUS_STOPPED:
            session.status = WORKOUT_STATUS_STOPPED
            session.ended_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(session)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось остановить тренировочную сессию.",
        ) from exc

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Тренировка завершена",
        message=f"Сессия #{session.id} остановлена и сохранена.",
    )

    return WorkoutStopResponse(redirect_url="/app")


@router.post("/api/workouts/{session_id}/log", response_model=WorkoutLogResponse)
def create_workout_log(
    session_id: int,
    payload: WorkoutLogRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkoutLogResponse:
    session = _session_or_404(db, user_id=current_user.id, session_id=session_id)
    if session.status != WORKOUT_STATUS_STARTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя логировать подходы для неактивной сессии.",
        )

    exercise_id = _resolve_exercise_id(
        db=db,
        session_id=session.id,
        program_id=session.program_id,
        requested_exercise_id=payload.exercise_id,
    )

    try:
        log_entry = WorkoutSetLog(
            session_id=session.id,
            exercise_id=exercise_id,
            set_number=payload.set_number,
            reps_planned=payload.reps_done,
            reps_done=payload.reps_done,
            form_score_mock=payload.form_score_mock,  # MOCK
            notes_mock=payload.notes_mock,  # MOCK
        )
        db.add(log_entry)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить лог подхода.",
        ) from exc

    return WorkoutLogResponse(ok=True)
