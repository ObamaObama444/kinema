from pydantic import BaseModel


class ExerciseCatalogItemResponse(BaseModel):
    id: int | None = None
    slug: str
    title: str
    description: str
    tags: list[str]
    technique_available: bool
    is_favorite: bool = False
    technique_launch_url: str | None = None
