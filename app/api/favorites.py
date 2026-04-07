from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.api.custom_exercises import favorite_payload_for_exercise
from app.core.deps import get_db
from app.core.exercise_catalog import CATALOG_DB_NAME_BY_SLUG, EXERCISE_CATALOG
from app.crud.favorite import add_favorite, list_favorites_by_type, remove_favorite
from app.crud.program import get_program_by_id
from app.models.exercise import Exercise
from app.models.user import User
from app.schemas.favorite import (
    FavoriteExerciseItemResponse,
    FavoriteMutationResponse,
    FavoriteProgramItemResponse,
    FavoritesResponse,
)

router = APIRouter(tags=["favorites"])

_SLUG_BY_DB_NAME = {value: key for key, value in CATALOG_DB_NAME_BY_SLUG.items()}
_CATALOG_BY_SLUG = {item["slug"]: item for item in EXERCISE_CATALOG}


def _exercise_favorite_payload(db: Session, exercise: Exercise, created_at) -> FavoriteExerciseItemResponse:
    slug = _SLUG_BY_DB_NAME.get(exercise.name) or f"exercise-{exercise.id}"
    catalog_item = _CATALOG_BY_SLUG.get(slug, {})
    custom_item = None
    if not catalog_item:
        custom_item = favorite_payload_for_exercise(db, exercise=exercise)  # type: ignore[name-defined]
        if custom_item:
            slug = str(custom_item.get("slug") or slug)

    return FavoriteExerciseItemResponse(
        id=exercise.id,
        slug=slug,
        title=str((custom_item or catalog_item).get("title") or exercise.name),
        description=str((custom_item or catalog_item).get("description") or exercise.description),
        tags=list((custom_item or catalog_item).get("tags") or []),
        technique_available=bool((custom_item or catalog_item).get("technique_available")),
        created_at=created_at,
    )


@router.get("/api/favorites", response_model=FavoritesResponse)
def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoritesResponse:
    program_items = list_favorites_by_type(db, current_user.id, "program")
    exercise_items = list_favorites_by_type(db, current_user.id, "exercise")

    program_ids = [item.item_id for item in program_items]
    exercise_ids = [item.item_id for item in exercise_items]

    programs_by_id = {}
    if program_ids:
        programs_by_id = {
            program.id: program
            for program in (
                get_program_by_id(db, program_id, user_id=current_user.id) for program_id in program_ids
            )
            if program is not None
        }

    exercises_by_id = {}
    if exercise_ids:
        exercises_by_id = {
            exercise.id: exercise
            for exercise in db.execute(
                select(Exercise).where(Exercise.id.in_(exercise_ids))
            ).scalars().all()
        }

    return FavoritesResponse(
        programs=[
            FavoriteProgramItemResponse(
                id=program.id,
                title=program.title,
                description=program.description,
                level=program.level,
                duration_weeks=program.duration_weeks,
                created_at=item.created_at,
            )
            for item in program_items
            if (program := programs_by_id.get(item.item_id)) is not None
        ],
        exercises=[
            _exercise_favorite_payload(db, exercise, item.created_at)
            for item in exercise_items
            if (exercise := exercises_by_id.get(item.item_id)) is not None
        ],
    )


@router.post("/api/favorites/programs/{program_id}", response_model=FavoriteMutationResponse)
def favorite_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteMutationResponse:
    program = get_program_by_id(db, program_id, user_id=current_user.id)
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Программа не найдена.")
    add_favorite(db, current_user.id, "program", program_id)
    return FavoriteMutationResponse(ok=True, item_type="program", item_id=program_id)


@router.delete("/api/favorites/programs/{program_id}", response_model=FavoriteMutationResponse)
def unfavorite_program(
    program_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteMutationResponse:
    removed = remove_favorite(db, current_user.id, "program", program_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Избранная программа не найдена.")
    return FavoriteMutationResponse(ok=True, item_type="program", item_id=program_id)


@router.post("/api/favorites/exercises/{exercise_id}", response_model=FavoriteMutationResponse)
def favorite_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteMutationResponse:
    exercise = db.execute(select(Exercise).where(Exercise.id == exercise_id)).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Упражнение не найдено.")
    add_favorite(db, current_user.id, "exercise", exercise_id)
    return FavoriteMutationResponse(ok=True, item_type="exercise", item_id=exercise_id)


@router.delete("/api/favorites/exercises/{exercise_id}", response_model=FavoriteMutationResponse)
def unfavorite_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteMutationResponse:
    removed = remove_favorite(db, current_user.id, "exercise", exercise_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Избранное упражнение не найдено.")
    return FavoriteMutationResponse(ok=True, item_type="exercise", item_id=exercise_id)
