from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.custom_exercises import published_catalog_items
from app.core.exercise_catalog import EXERCISE_CATALOG
from app.core.exercise_catalog import CATALOG_DB_NAME_BY_SLUG
from app.core.deps import get_db
from app.crud.favorite import list_favorites_by_type
from app.models.exercise import Exercise
from app.models.user import User
from app.schemas.exercise import ExerciseCatalogItemResponse

router = APIRouter(tags=["exercises"])
HIDDEN_CATALOG_SLUGS = {"pushup"}


@router.get("/api/exercises/catalog", response_model=list[ExerciseCatalogItemResponse])
def get_exercise_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExerciseCatalogItemResponse]:
    names = list(CATALOG_DB_NAME_BY_SLUG.values())
    exercise_rows = db.execute(
        select(Exercise.id, Exercise.name).where(Exercise.name.in_(names))
    ).all()
    exercise_id_by_name = {name: exercise_id for exercise_id, name in exercise_rows}
    favorite_ids = {
        item.item_id
        for item in list_favorites_by_type(db, current_user.id, "exercise")
    }

    items: list[ExerciseCatalogItemResponse] = []
    for item in EXERCISE_CATALOG:
        # Временно скрываем из пользовательского списка, но оставляем в кодовой базе.
        if item["slug"] in HIDDEN_CATALOG_SLUGS:
            continue
        exercise_id = exercise_id_by_name.get(CATALOG_DB_NAME_BY_SLUG.get(item["slug"], ""))
        items.append(
            ExerciseCatalogItemResponse(
                **item,
                id=exercise_id,
                is_favorite=exercise_id in favorite_ids if exercise_id is not None else False,
            )
        )
    items.extend(
        published_catalog_items(
            db,
            current_user=current_user,
            favorite_ids=favorite_ids,
        )
    )
    return items
