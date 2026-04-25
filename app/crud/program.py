from typing import Any

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exercise_catalog import CATALOG_DB_ALIASES_BY_SLUG
from app.models.exercise import Exercise
from app.models.profile import Profile
from app.models.program import Program
from app.models.program_exercise import ProgramExercise

CUSTOM_PROGRAM_TITLE = "Моя программа"
CUSTOM_PROGRAM_DESCRIPTION = "Пользовательская программа, собранная из каталога упражнений."
CUSTOM_PROGRAM_LEVEL = "beginner"
CUSTOM_PROGRAM_DURATION_WEEKS = 4

_CATALOG_TO_EXERCISE_NAME = {
    "squat": "Приседания",
    "pushup": "Отжимания",
    "lunge": "Выпад назад",
    "glute_bridge": "Ягодичный мост",
    "leg_raise": "Подъёмы ног лежа",
    "crunch": "Скручивания",
}

_CATALOG_EXERCISE_FALLBACK = {
    "squat": {
        "name": "Приседания",
        "description": "Базовое упражнение на ноги и ягодицы.",
        "equipment": None,
        "primary_muscles": "Квадрицепсы, ягодицы",
        "difficulty": "easy",
    },
    "pushup": {
        "name": "Отжимания",
        "description": "Укрепление грудных мышц, плеч и трицепсов.",
        "equipment": None,
        "primary_muscles": "Грудь, трицепс, плечи",
        "difficulty": "medium",
    },
    "lunge": {
        "name": "Выпад назад",
        "description": "Контролируемый шаг назад для силы ног и устойчивости.",
        "equipment": None,
        "primary_muscles": "Квадрицепсы, ягодицы",
        "difficulty": "medium",
    },
    "glute_bridge": {
        "name": "Ягодичный мост",
        "description": "Изолированная работа ягодичных мышц.",
        "equipment": None,
        "primary_muscles": "Ягодицы, бицепс бедра",
        "difficulty": "easy",
    },
    "leg_raise": {
        "name": "Подъёмы ног лежа",
        "description": "Контроль пресса и подъёма ног без рывка.",
        "equipment": None,
        "primary_muscles": "Пресс, сгибатели бедра",
        "difficulty": "easy",
    },
    "crunch": {
        "name": "Скручивания",
        "description": "Базовая работа на пресс.",
        "equipment": None,
        "primary_muscles": "Пресс",
        "difficulty": "easy",
    },
}


def ensure_seed_programs(db: Session) -> None:
    existing_global_program_id = db.execute(
        select(Program.id).where(Program.owner_user_id.is_(None)).limit(1)
    ).scalar_one_or_none()
    if existing_global_program_id is not None:
        return

    exercises_payload = list(_CATALOG_EXERCISE_FALLBACK.values())

    exercise_by_name: dict[str, Exercise] = {}
    for payload in exercises_payload:
        aliases: list[str] = []
        for slug, fallback in _CATALOG_EXERCISE_FALLBACK.items():
            if fallback["name"] == payload["name"]:
                aliases = CATALOG_DB_ALIASES_BY_SLUG.get(slug, [])
                break

        existing = db.execute(
            select(Exercise).where(Exercise.name.in_([payload["name"], *aliases]))
        ).scalar_one_or_none()
        if existing is not None:
            existing.name = payload["name"]
            existing.description = payload["description"]
            existing.equipment = payload["equipment"]
            existing.primary_muscles = payload["primary_muscles"]
            existing.difficulty = payload["difficulty"]
            db.add(existing)
            exercise_by_name[existing.name] = existing
            continue

        exercise = Exercise(**payload)
        db.add(exercise)
        db.flush()
        exercise_by_name[exercise.name] = exercise

    programs_payload = [
        {
            "program": {
                "title": "Базовый старт",
                "description": "Программа для мягкого входа в регулярные тренировки.",
                "level": "beginner",
                "duration_weeks": 4,
            },
            "exercises": [
                {
                    "exercise_name": "Приседания",
                    "sets": 3,
                    "reps": 12,
                    "rest_sec": 60,
                    "tempo": "2-1-2",
                },
                {
                    "exercise_name": "Отжимания",
                    "sets": 3,
                    "reps": 8,
                    "rest_sec": 75,
                    "tempo": "2-0-2",
                },
                {
                    "exercise_name": "Скручивания",
                    "sets": 3,
                    "reps": 16,
                    "rest_sec": 45,
                    "tempo": "1-1-1",
                },
                {
                    "exercise_name": "Ягодичный мост",
                    "sets": 3,
                    "reps": 14,
                    "rest_sec": 60,
                    "tempo": "2-1-2",
                },
            ],
        },
        {
            "program": {
                "title": "Сила и тонус",
                "description": "Умеренная силовая программа для развития мышц всего тела.",
                "level": "intermediate",
                "duration_weeks": 6,
            },
            "exercises": [
                {
                    "exercise_name": "Выпад назад",
                    "sets": 4,
                    "reps": 10,
                    "rest_sec": 75,
                    "tempo": "2-1-2",
                },
                {
                    "exercise_name": "Отжимания",
                    "sets": 4,
                    "reps": 10,
                    "rest_sec": 70,
                    "tempo": "2-0-2",
                },
                {
                    "exercise_name": "Подъёмы ног лежа",
                    "sets": 3,
                    "reps": 14,
                    "rest_sec": 45,
                    "tempo": "1-1-1",
                },
                {
                    "exercise_name": "Скручивания",
                    "sets": 3,
                    "reps": 18,
                    "rest_sec": 40,
                    "tempo": "1-1-1",
                },
            ],
        },
        {
            "program": {
                "title": "Кардио выносливость",
                "description": "Интервальные нагрузки для улучшения выносливости и метаболизма.",
                "level": "advanced",
                "duration_weeks": 5,
            },
            "exercises": [
                {
                    "exercise_name": "Приседания",
                    "sets": 4,
                    "reps": 20,
                    "rest_sec": 60,
                    "tempo": "2-0-2",
                },
                {
                    "exercise_name": "Отжимания",
                    "sets": 4,
                    "reps": 12,
                    "rest_sec": 55,
                    "tempo": "2-0-2",
                },
                {
                    "exercise_name": "Выпад назад",
                    "sets": 4,
                    "reps": 12,
                    "rest_sec": 50,
                    "tempo": "2-0-2",
                },
                {
                    "exercise_name": "Подъёмы ног лежа",
                    "sets": 3,
                    "reps": 16,
                    "rest_sec": 45,
                    "tempo": "2-1-2",
                },
            ],
        },
    ]

    for program_payload in programs_payload:
        program = Program(**program_payload["program"], owner_user_id=None)
        db.add(program)
        db.flush()

        for index, item in enumerate(program_payload["exercises"], start=1):
            exercise = exercise_by_name[item["exercise_name"]]
            link = ProgramExercise(
                program_id=program.id,
                exercise_id=exercise.id,
                order=index,
                sets=item["sets"],
                reps=item["reps"],
                rest_sec=item["rest_sec"],
                tempo=item["tempo"],
            )
            db.add(link)

    db.commit()


def _catalog_exercise(slug: str) -> Exercise:
    exercise_name = _CATALOG_TO_EXERCISE_NAME[slug]
    fallback = _CATALOG_EXERCISE_FALLBACK[slug]

    return Exercise(
        name=exercise_name,
        description=fallback["description"],
        equipment=fallback["equipment"],
        primary_muscles=fallback["primary_muscles"],
        difficulty=fallback["difficulty"],
    )


def _get_or_create_catalog_exercise(db: Session, slug: str) -> Exercise:
    exercise_name = _CATALOG_TO_EXERCISE_NAME[slug]
    exercise = db.execute(
        select(Exercise).where(Exercise.name == exercise_name)
    ).scalar_one_or_none()
    if exercise is not None:
        return exercise

    exercise = _catalog_exercise(slug)
    db.add(exercise)
    db.flush()
    return exercise


def _normalize_positive_int(value: Any, *, min_value: int, max_value: int, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Поле {field_name} должно быть целым числом.") from exc

    if number < min_value or number > max_value:
        raise ValueError(f"Поле {field_name} должно быть в диапазоне {min_value}-{max_value}.")

    return number


def _normalize_custom_plan_items(items: list[dict[str, Any]]) -> list[dict[str, int | str]]:
    normalized_items: list[dict[str, int | str]] = []
    seen_slugs: set[str] = set()
    allowed_slugs = ", ".join(sorted(_CATALOG_TO_EXERCISE_NAME.keys()))

    for item in items:
        slug_raw = str(item.get("exercise_slug", "")).strip().lower()
        if slug_raw not in _CATALOG_TO_EXERCISE_NAME:
            raise ValueError(f"Поддерживаются только упражнения: {allowed_slugs}.")

        if slug_raw in seen_slugs:
            raise ValueError("Каждое упражнение можно добавить в программу только один раз.")
        seen_slugs.add(slug_raw)

        normalized_items.append(
            {
                "exercise_slug": slug_raw,
                "sets": _normalize_positive_int(item.get("sets"), min_value=1, max_value=20, field_name="sets"),
                "target_reps": _normalize_positive_int(item.get("target_reps"), min_value=1, max_value=300, field_name="target_reps"),
                "rest_sec": _normalize_positive_int(item.get("rest_sec"), min_value=10, max_value=600, field_name="rest_sec"),
            }
        )

    return normalized_items


def get_user_custom_program(db: Session, user_id: int) -> Program | None:
    programs = list(
        db.execute(
            select(Program).where(Program.owner_user_id == user_id).order_by(Program.id.asc())
        ).scalars().all()
    )
    if not programs:
        return None

    primary = programs[0]
    if len(programs) == 1:
        return primary

    duplicate_ids = {program.id for program in programs[1:]}
    profile = db.execute(
        select(Profile).where(Profile.user_id == user_id)
    ).scalar_one_or_none()
    if profile is not None and profile.active_program_id in duplicate_ids:
        profile.active_program_id = primary.id

    for duplicate in programs[1:]:
        db.delete(duplicate)
    db.flush()

    return primary


def upsert_user_custom_program(db: Session, user_id: int, items: list[dict[str, Any]]) -> Program | None:
    ensure_seed_programs(db)
    normalized_items = _normalize_custom_plan_items(items)

    custom_program = get_user_custom_program(db, user_id)
    profile = db.execute(
        select(Profile).where(Profile.user_id == user_id)
    ).scalar_one_or_none()

    if not normalized_items:
        if custom_program is None:
            return None

        removed_program_id = custom_program.id
        db.delete(custom_program)

        if profile is not None and profile.active_program_id == removed_program_id:
            profile.active_program_id = None
            profile.workouts_per_week = None

        db.commit()
        return None

    if custom_program is None:
        custom_program = Program(
            title=CUSTOM_PROGRAM_TITLE,
            description=CUSTOM_PROGRAM_DESCRIPTION,
            level=CUSTOM_PROGRAM_LEVEL,
            duration_weeks=CUSTOM_PROGRAM_DURATION_WEEKS,
            owner_user_id=user_id,
        )
        db.add(custom_program)
        db.flush()
    else:
        custom_program.title = CUSTOM_PROGRAM_TITLE
        custom_program.description = CUSTOM_PROGRAM_DESCRIPTION
        custom_program.level = CUSTOM_PROGRAM_LEVEL
        custom_program.duration_weeks = CUSTOM_PROGRAM_DURATION_WEEKS

    db.execute(
        delete(ProgramExercise).where(ProgramExercise.program_id == custom_program.id)
    )

    for order_index, item in enumerate(normalized_items, start=1):
        exercise = _get_or_create_catalog_exercise(db, str(item["exercise_slug"]))
        db.add(
            ProgramExercise(
                program_id=custom_program.id,
                exercise_id=exercise.id,
                order=order_index,
                sets=int(item["sets"]),
                reps=int(item["target_reps"]),
                rest_sec=int(item["rest_sec"]),
                tempo="контрольный",
            )
        )

    db.commit()
    db.refresh(custom_program)
    return custom_program


def list_programs(db: Session, user_id: int | None = None) -> list[Program]:
    ensure_seed_programs(db)
    stmt: Select[tuple[Program]] = select(Program)

    if user_id is None:
        stmt = stmt.where(Program.owner_user_id.is_(None))
    else:
        stmt = stmt.where(
            or_(Program.owner_user_id.is_(None), Program.owner_user_id == user_id)
        )

    stmt = stmt.order_by(Program.owner_user_id.is_not(None).desc(), Program.id)
    return list(db.execute(stmt).scalars().all())


def get_program_with_exercises(db: Session, program_id: int, user_id: int | None = None) -> Program | None:
    ensure_seed_programs(db)
    stmt = (
        select(Program)
        .options(joinedload(Program.program_exercises).joinedload(ProgramExercise.exercise))
        .where(Program.id == program_id)
    )
    if user_id is not None:
        stmt = stmt.where(
            or_(Program.owner_user_id.is_(None), Program.owner_user_id == user_id)
        )

    return db.execute(stmt).unique().scalar_one_or_none()


def get_program_by_id(db: Session, program_id: int, user_id: int | None = None) -> Program | None:
    ensure_seed_programs(db)
    stmt = select(Program).where(Program.id == program_id)
    if user_id is not None:
        stmt = stmt.where(
            or_(Program.owner_user_id.is_(None), Program.owner_user_id == user_id)
        )

    return db.execute(stmt).scalar_one_or_none()
