from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exercise_catalog import catalog_slug_by_db_name
from app.core.deps import get_db
from app.crud.favorite import list_favorites_by_type
from app.crud.notification import create_notification_safe
from app.crud.profile import get_active_program_snapshot, set_active_program
from app.crud.program import (
    get_user_custom_program,
    get_program_with_exercises,
    list_programs,
    upsert_user_custom_program,
)
from app.models.user import User
from app.schemas.program import (
    ActiveProgramSummary,
    CustomProgramSyncRequest,
    CustomProgramSyncResponse,
    ProgramCardResponse,
    ProgramDetailResponse,
    ProgramExerciseItemResponse,
    ProgramSelectRequest,
    ProgramSelectResponse,
)

router = APIRouter(tags=["programs"])


def _exercise_name_to_slug(name: str) -> str:
    return catalog_slug_by_db_name(name) or "squat"


def _custom_program_signature(program) -> list[tuple[str, int, int, int]]:
    if program is None:
        return []

    result: list[tuple[str, int, int, int]] = []
    links = sorted(program.program_exercises, key=lambda item: item.order)
    for link in links:
        result.append(
            (
                _exercise_name_to_slug(link.exercise.name),
                int(link.sets),
                int(link.reps),
                int(link.rest_sec),
            )
        )
    return result


def _request_signature(payload: CustomProgramSyncRequest) -> list[tuple[str, int, int, int]]:
    return [
        (
            item.exercise_slug,
            int(item.sets),
            int(item.target_reps),
            int(item.rest_sec),
        )
        for item in payload.items
    ]


@router.get("/api/programs", response_model=list[ProgramCardResponse])
def get_programs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProgramCardResponse]:
    try:
        programs = list_programs(db, user_id=current_user.id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось получить список программ.",
        ) from exc

    favorite_ids = {
        item.item_id
        for item in list_favorites_by_type(db, current_user.id, "program")
    }

    return [
        ProgramCardResponse(
            id=program.id,
            title=program.title,
            description=program.description,
            level=program.level,
            duration_weeks=program.duration_weeks,
            is_custom=program.owner_user_id is not None,
            is_favorite=program.id in favorite_ids,
        )
        for program in programs
    ]


@router.get("/api/programs/{program_id}", response_model=ProgramDetailResponse)
def get_program_detail(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgramDetailResponse:
    try:
        program = get_program_with_exercises(db, program_id, user_id=current_user.id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить программу.",
        ) from exc

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Программа не найдена.",
        )

    ordered_links = sorted(program.program_exercises, key=lambda item: item.order)
    favorite_ids = {
        item.item_id
        for item in list_favorites_by_type(db, current_user.id, "program")
    }
    exercises = [
        ProgramExerciseItemResponse(
            id=link.id,
            order=link.order,
            sets=link.sets,
            reps=link.reps,
            rest_sec=link.rest_sec,
            tempo=link.tempo,
            exercise_id=link.exercise.id,
            exercise_name=link.exercise.name,
            exercise_description=link.exercise.description,
            equipment=link.exercise.equipment,
            primary_muscles=link.exercise.primary_muscles,
            difficulty=link.exercise.difficulty,
        )
        for link in ordered_links
    ]

    return ProgramDetailResponse(
        id=program.id,
        title=program.title,
        description=program.description,
        level=program.level,
        duration_weeks=program.duration_weeks,
        is_favorite=program.id in favorite_ids,
        exercises=exercises,
    )


@router.post("/api/programs/select", response_model=ProgramSelectResponse)
def select_active_program(
    payload: ProgramSelectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgramSelectResponse:
    try:
        program = get_program_with_exercises(db, payload.program_id, user_id=current_user.id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось выбрать программу.",
        ) from exc

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Программа не найдена.",
        )

    try:
        profile = set_active_program(
            db=db,
            user_id=current_user.id,
            program_id=program.id,
            workouts_per_week=payload.workouts_per_week,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить активную программу.",
        ) from exc

    active_program_snapshot = get_active_program_snapshot(db, current_user.id, profile)
    if active_program_snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Активную программу не удалось подготовить для отображения.",
        )

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Активная программа обновлена",
        message=f"Вы выбрали программу «{program.title}» ({payload.workouts_per_week} раз(а) в неделю).",
    )

    return ProgramSelectResponse(
        message="Программа успешно выбрана.",
        active_program=ActiveProgramSummary.model_validate(active_program_snapshot),
    )


@router.post("/api/programs/custom", response_model=CustomProgramSyncResponse)
def sync_custom_program(
    payload: CustomProgramSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CustomProgramSyncResponse:
    before_program = get_user_custom_program(db, current_user.id)
    before_signature = _custom_program_signature(before_program)
    requested_signature = _request_signature(payload)

    try:
        custom_program = upsert_user_custom_program(
            db=db,
            user_id=current_user.id,
            items=[item.model_dump() for item in payload.items],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось синхронизировать пользовательскую программу.",
        ) from exc

    if custom_program is None:
        if before_signature:
            create_notification_safe(
                db,
                user_id=current_user.id,
                title="Пользовательская программа удалена",
                message="Ваша программа из каталога очищена.",
            )
        return CustomProgramSyncResponse(
            message="Пользовательская программа удалена.",
            custom_program_id=None,
            exercises_count=0,
        )

    if before_signature != requested_signature:
        create_notification_safe(
            db,
            user_id=current_user.id,
            title="Пользовательская программа сохранена",
            message=f"Сохранено упражнений: {len(custom_program.program_exercises)}.",
        )

    return CustomProgramSyncResponse(
        message="Пользовательская программа сохранена.",
        custom_program_id=custom_program.id,
        exercises_count=len(custom_program.program_exercises),
    )
