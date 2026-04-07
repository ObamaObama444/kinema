from datetime import datetime

from pydantic import BaseModel


class FavoriteProgramItemResponse(BaseModel):
    id: int
    title: str
    description: str
    level: str
    duration_weeks: int
    created_at: datetime


class FavoriteExerciseItemResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    tags: list[str]
    technique_available: bool
    created_at: datetime


class FavoritesResponse(BaseModel):
    programs: list[FavoriteProgramItemResponse]
    exercises: list[FavoriteExerciseItemResponse]


class FavoriteMutationResponse(BaseModel):
    ok: bool
    item_type: str
    item_id: int
