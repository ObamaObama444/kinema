EXERCISE_CATALOG = [
    {
        "slug": "squat",
        "title": "Приседания",
        "description": "Базовое упражнение на ноги и корпус для развития силы и выносливости.",
        "tags": ["Без инвентаря", "Новичкам", "Ноги / Ягодицы"],
        "technique_available": True,
    },
    {
        "slug": "pushup",
        "title": "Отжимания",
        "description": "Классическое упражнение для груди, плеч и стабилизаторов корпуса.",
        "tags": ["Без инвентаря", "Новичкам", "Грудь / Трицепс"],
        "technique_available": True,
    },
    {
        "slug": "lunge",
        "title": "Выпад назад",
        "description": "Контролируемый шаг назад для силы ног, баланса и устойчивости таза.",
        "tags": ["Без инвентаря", "Ноги / Ягодицы", "Средний уровень"],
        "technique_available": True,
    },
    {
        "slug": "glute_bridge",
        "title": "Ягодичный мост",
        "description": "Акцентированно включает ягодицы и заднюю поверхность бедра.",
        "tags": ["Без инвентаря", "Ягодицы", "Лёгкий уровень"],
        "technique_available": True,
    },
    {
        "slug": "leg_raise",
        "title": "Подъёмы ног лежа",
        "description": "Подконтрольный подъём ног лёжа для пресса и контроля корпуса.",
        "tags": ["Без инвентаря", "Пресс", "Лёгкий уровень"],
        "technique_available": True,
    },
    {
        "slug": "crunch",
        "title": "Скручивания",
        "description": "Базовое упражнение на мышцы пресса и контроль корпуса.",
        "tags": ["Без инвентаря", "Пресс", "Лёгкий уровень"],
        "technique_available": True,
    },
]

CATALOG_DB_NAME_BY_SLUG = {
    "squat": "Приседания",
    "pushup": "Отжимания",
    "lunge": "Выпад назад",
    "glute_bridge": "Ягодичный мост",
    "leg_raise": "Подъёмы ног лежа",
    "crunch": "Скручивания",
}

CATALOG_TITLE_BY_SLUG = dict(CATALOG_DB_NAME_BY_SLUG)

CATALOG_DB_ALIASES_BY_SLUG = {
    "squat": ["Приседания с собственным весом"],
    "pushup": [],
    "lunge": ["Выпады"],
    "glute_bridge": [],
    "leg_raise": ["Подъемы ног", "Подъёмы ног"],
    "crunch": [],
}


def catalog_db_name_candidates(slug: str) -> list[str]:
    normalized = str(slug or "").strip().lower()
    primary = CATALOG_DB_NAME_BY_SLUG.get(normalized)
    if not primary:
        return []
    return [primary, *CATALOG_DB_ALIASES_BY_SLUG.get(normalized, [])]


def catalog_slug_by_db_name(name: str) -> str | None:
    normalized = str(name or "").strip()
    for slug, candidates in CATALOG_DB_ALIASES_BY_SLUG.items():
        if normalized in candidates:
            return slug
    for slug, db_name in CATALOG_DB_NAME_BY_SLUG.items():
        if normalized == db_name:
            return slug
    return None
