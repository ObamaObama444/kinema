import json
import math
from datetime import date, timedelta

from app.schemas.onboarding import (
    ACTIVITY_LEVEL_VALUES,
    CALORIE_TRACKING_VALUES,
    DESIRED_OUTCOME_VALUES,
    DIET_TYPE_VALUES,
    EQUIPMENT_TAG_VALUES,
    FITNESS_LEVEL_VALUES,
    FOCUS_AREA_VALUES,
    GENDER_VALUES,
    GOAL_PACE_VALUES,
    INJURY_AREA_VALUES,
    INTEREST_TAG_VALUES,
    MAIN_GOAL_VALUES,
    MOTIVATION_VALUES,
    SELF_IMAGE_VALUES,
    TRAINING_DAY_VALUES,
)

ARRAY_FIELDS = {"interest_tags", "equipment_tags", "injury_areas", "training_days"}
DEFAULT_ONBOARDING_VERSION = "v1"
EMPTY_ARRAY_DEFAULTS = {field: [] for field in ARRAY_FIELDS}
RUSSIAN_MONTHS = [
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

NEUTRAL_SHAPE_LABELS = {
    1: "Стройная",
    2: "В форме",
    3: "Сбалансированная",
    4: "Мягкая",
    5: "Пышная",
}

BODY_SHAPE_RANGES = {
    "male": {
        1: ("6-9%", 7.5),
        2: ("10-15%", 12.5),
        3: ("16-20%", 18.0),
        4: ("21-25%", 23.0),
        5: ("26-31%", 28.5),
    },
    "female": {
        1: ("16-19%", 17.5),
        2: ("20-24%", 22.0),
        3: ("25-29%", 27.0),
        4: ("30-34%", 32.0),
        5: ("35-40%", 37.5),
    },
}

BODY_SHAPE_CAPTIONS = {
    1: "Фокус на рельеф и тонус.",
    2: "Сильная и подтянутая форма.",
    3: "Сбалансированный и устойчивый результат.",
    4: "Больше мягкости, но хороший потенциал прогресса.",
    5: "Нужен мягкий вход и постепенная адаптация.",
}

COMPLETE_FIELD_REQUIREMENTS: dict[str, list[str]] = {
    "main_goal": ["main_goal"],
    "focus_area": ["focus_area"],
    "gender": ["gender"],
    "age": ["age"],
    "height_cm": ["height_cm"],
    "current_weight_kg": ["current_weight_kg"],
    "target_weight_kg": ["target_weight_kg"],
    "fitness_level": ["fitness_level"],
    "activity_level": ["activity_level"],
    "goal_pace": ["goal_pace"],
    "interest_tags": ["interest_tags"],
    "equipment_tags": ["equipment_tags"],
    "training_frequency": ["training_frequency"],
    "injury_areas": ["injury_areas"],
    "schedule": ["training_days"],
}

CHOICE_FIELD_LABELS = {
    "main_goal": MAIN_GOAL_VALUES,
    "motivation": MOTIVATION_VALUES,
    "desired_outcome": DESIRED_OUTCOME_VALUES,
    "focus_area": FOCUS_AREA_VALUES,
    "gender": GENDER_VALUES,
    "fitness_level": FITNESS_LEVEL_VALUES,
    "activity_level": ACTIVITY_LEVEL_VALUES,
    "goal_pace": GOAL_PACE_VALUES,
    "calorie_tracking": CALORIE_TRACKING_VALUES,
    "diet_type": DIET_TYPE_VALUES,
    "self_image": SELF_IMAGE_VALUES,
}


def empty_onboarding_data() -> dict[str, object]:
    return {
        "main_goal": None,
        "motivation": None,
        "desired_outcome": None,
        "focus_area": None,
        "gender": None,
        "current_body_shape": None,
        "target_body_shape": None,
        "age": None,
        "height_cm": None,
        "current_weight_kg": None,
        "target_weight_kg": None,
        "fitness_level": None,
        "activity_level": None,
        "goal_pace": None,
        "training_frequency": None,
        "calorie_tracking": None,
        "diet_type": None,
        "self_image": None,
        "reminders_enabled": False,
        "reminder_time_local": None,
        "onboarding_version": DEFAULT_ONBOARDING_VERSION,
        "interest_tags": [],
        "equipment_tags": [],
        "injury_areas": [],
        "training_days": [],
    }


def parse_json_list(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    result: list[str] = []
    for item in parsed:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def dump_json_list(items: list[str] | None) -> str:
    return json.dumps(items or [], ensure_ascii=False)


def merge_onboarding_data(current: dict[str, object], payload: dict[str, object]) -> dict[str, object]:
    merged = empty_onboarding_data()
    merged.update(current)
    merged.update(payload)

    for field in ARRAY_FIELDS:
        value = merged.get(field)
        merged[field] = list(value) if isinstance(value, list) else []

    if merged.get("injury_areas") and "none" in merged["injury_areas"]:
        merged["injury_areas"] = ["none"]

    if merged.get("equipment_tags") and "none" in merged["equipment_tags"]:
        merged["equipment_tags"] = ["none"]

    if merged.get("reminders_enabled") is False:
        merged["reminder_time_local"] = None

    if not merged.get("onboarding_version"):
        merged["onboarding_version"] = DEFAULT_ONBOARDING_VERSION

    return merged


def has_onboarding_answers(data: dict[str, object]) -> bool:
    for key, value in data.items():
        if key == "onboarding_version":
            continue
        if isinstance(value, list) and value:
            return True
        if isinstance(value, list):
            continue
        if isinstance(value, bool):
            if value:
                return True
            continue
        if value not in (None, ""):
            return True
    return False


def resolve_onboarding_status(data: dict[str, object], is_completed: bool) -> str:
    if is_completed:
        return "completed"
    if has_onboarding_answers(data):
        return "in_progress"
    return "empty"


def resolve_resume_step(data: dict[str, object], is_completed: bool) -> str:
    if is_completed:
        return "result"

    if not has_onboarding_answers(data):
        return "splash"

    for step_key, fields in COMPLETE_FIELD_REQUIREMENTS.items():
        if step_key == "target_weight_kg" and not _requires_target_weight(data):
            continue
        if step_key == "schedule":
            training_days = data.get("training_days") or []
            reminders_enabled = bool(data.get("reminders_enabled"))
            reminder_time_local = data.get("reminder_time_local")
            if not training_days:
                return step_key
            if reminders_enabled and not reminder_time_local:
                return step_key
            continue

        if any(_is_missing_value(data.get(field_name)) for field_name in fields):
            return step_key

    return "schedule"


def _is_missing_value(value: object) -> bool:
    if isinstance(value, list):
        return len(value) == 0
    return value in (None, "")


def _requires_target_weight(data: dict[str, object]) -> bool:
    main_goal = data.get("main_goal")
    return main_goal in {"lose_weight", "gain_muscle"}


def _format_date_label(value: date | None) -> str | None:
    if value is None:
        return None
    return f"{value.day} {RUSSIAN_MONTHS[value.month]}"


def _bmi_label(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 18.5:
        return "Ниже нормы"
    if value < 25:
        return "Обычно"
    if value < 30:
        return "Выше нормы"
    return "Высокий"


def _body_shape_summary(shape: int | None, gender: str | None) -> dict[str, object]:
    if shape is None:
        return {
            "shape": None,
            "label": None,
            "range_text": None,
            "percent_value": None,
            "caption": None,
        }

    label = NEUTRAL_SHAPE_LABELS.get(shape)
    caption = BODY_SHAPE_CAPTIONS.get(shape)
    range_text = None
    percent_value = None

    if gender in BODY_SHAPE_RANGES:
        range_text, percent_value = BODY_SHAPE_RANGES[gender][shape]

    return {
        "shape": shape,
        "label": label,
        "range_text": range_text,
        "percent_value": percent_value,
        "caption": caption,
    }


def _goal_rate_per_week(main_goal: str | None, goal_pace: str | None, current_weight: float | None, target_weight: float | None) -> float | None:
    if goal_pace is None or current_weight is None or target_weight is None:
        return None

    pace_weights = {
        "lose_weight": {"slow": 0.25, "moderate": 0.45, "fast": 0.70},
        "gain_muscle": {"slow": 0.10, "moderate": 0.20, "fast": 0.30},
    }

    if main_goal == "stay_fit":
        if abs(target_weight - current_weight) < 1:
            return None
        main_goal = "lose_weight" if target_weight < current_weight else "gain_muscle"

    return pace_weights.get(main_goal or "", {}).get(goal_pace or "")


def estimate_target_timeline(data: dict[str, object]) -> tuple[int | None, date | None]:
    main_goal = data.get("main_goal")
    goal_pace = data.get("goal_pace")
    current_weight = data.get("current_weight_kg")
    target_weight = data.get("target_weight_kg")

    if not isinstance(current_weight, (int, float)) or not isinstance(target_weight, (int, float)):
        return None, None

    delta = abs(target_weight - current_weight)
    if delta < 0.01:
        return 6, date.today() + timedelta(weeks=6)

    if main_goal == "stay_fit" and delta < 1:
        return 6, date.today() + timedelta(weeks=6)

    rate = _goal_rate_per_week(main_goal if isinstance(main_goal, str) else None, goal_pace if isinstance(goal_pace, str) else None, float(current_weight), float(target_weight))
    if rate is None or rate <= 0:
        return None, None

    estimated_weeks = max(2, int(math.ceil(delta / rate)))
    return estimated_weeks, date.today() + timedelta(weeks=estimated_weeks)


def build_milestones(data: dict[str, object], estimated_weeks: int | None, target_date: date | None) -> list[dict[str, object]]:
    current_weight = data.get("current_weight_kg")
    target_weight = data.get("target_weight_kg")
    if not isinstance(current_weight, (int, float)) or not isinstance(target_weight, (int, float)):
        return []

    total_weeks = estimated_weeks or 6
    checkpoints = sorted({0, max(1, total_weeks // 3), max(2, (2 * total_weeks) // 3), total_weeks})
    milestones: list[dict[str, object]] = []
    start_date = date.today()

    for week in checkpoints:
        progress = 0 if total_weeks == 0 else week / total_weeks
        weight_value = float(current_weight) + (float(target_weight) - float(current_weight)) * progress
        milestone_date = target_date if week == total_weeks and target_date is not None else start_date + timedelta(weeks=week)
        milestones.append(
            {
                "week": week,
                "label": "Сегодня" if week == 0 else ("Цель" if week == total_weeks else f"Неделя {week}"),
                "date_label": _format_date_label(milestone_date) or "",
                "weight_kg": round(weight_value, 1),
                "is_target": week == total_weeks,
            }
        )
    return milestones


def build_goal_target_value(data: dict[str, object], derived: dict[str, object]) -> str | None:
    target_weight = data.get("target_weight_kg")
    target_date_label = derived.get("target_date_label")
    if not isinstance(target_weight, (int, float)) or not isinstance(target_date_label, str) or not target_date_label:
        return None
    return f"{float(target_weight):.1f} кг к {target_date_label}"


def main_goal_to_goal_type(main_goal: str | None) -> str | None:
    mapping = {
        "lose_weight": "weight_loss",
        "gain_muscle": "muscle_gain",
        "stay_fit": "endurance",
    }
    return mapping.get(main_goal or "")


def build_onboarding_derived(data: dict[str, object]) -> dict[str, object]:
    height_cm = data.get("height_cm")
    current_weight = data.get("current_weight_kg")
    target_weight = data.get("target_weight_kg")
    age = data.get("age")
    gender = data.get("gender")

    bmi = None
    if isinstance(height_cm, (int, float)) and isinstance(current_weight, (int, float)) and height_cm:
        bmi = round(float(current_weight) / math.pow(float(height_cm) / 100.0, 2), 1)

    bmr_kcal = None
    if all(isinstance(value, (int, float)) for value in (height_cm, current_weight, age)):
        base_value = 10 * float(current_weight) + 6.25 * float(height_cm) - 5 * float(age)
        if gender == "male":
            bmr_kcal = int(round(base_value + 5))
        elif gender == "female":
            bmr_kcal = int(round(base_value - 161))
        else:
            bmr_kcal = int(round(base_value - 80))

    estimated_weeks, target_date = estimate_target_timeline(data)
    current_body = _body_shape_summary(data.get("current_body_shape"), gender if isinstance(gender, str) else None)
    target_body = _body_shape_summary(data.get("target_body_shape"), gender if isinstance(gender, str) else None)

    body_fat_delta_percent = None
    if isinstance(current_body.get("percent_value"), (int, float)) and isinstance(target_body.get("percent_value"), (int, float)):
        body_fat_delta_percent = round(float(current_body["percent_value"]) - float(target_body["percent_value"]), 1)

    weight_delta_kg = None
    if isinstance(current_weight, (int, float)) and isinstance(target_weight, (int, float)):
        weight_delta_kg = round(float(target_weight) - float(current_weight), 1)

    derived = {
        "bmi": bmi,
        "bmi_label": _bmi_label(bmi),
        "bmr_kcal": bmr_kcal,
        "weight_delta_kg": weight_delta_kg,
        "estimated_weeks": estimated_weeks,
        "target_date_iso": target_date.isoformat() if target_date is not None else None,
        "target_date_label": _format_date_label(target_date),
        "goal_target_value": None,
        "body_fat_delta_percent": body_fat_delta_percent,
        "current_body": current_body,
        "target_body": target_body,
        "analysis_items": build_analysis_items(data, bmr_kcal),
        "milestones": build_milestones(data, estimated_weeks, target_date),
    }
    derived["goal_target_value"] = build_goal_target_value(data, derived)
    return derived


def build_analysis_items(data: dict[str, object], bmr_kcal: int | None) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    height_cm = data.get("height_cm")
    current_weight = data.get("current_weight_kg")
    focus_area = data.get("focus_area")
    level = data.get("fitness_level")

    if isinstance(height_cm, (int, float)) and isinstance(current_weight, (int, float)):
        items.append(
            {
                "title": "Анализируем данные",
                "value": f"{int(round(float(height_cm)))} см, {float(current_weight):.1f} кг",
            }
        )
    if bmr_kcal is not None:
        items.append(
            {
                "title": "Рассчитываем метаболизм",
                "value": f"{bmr_kcal} ккал",
            }
        )
    if isinstance(focus_area, str):
        focus_labels = {
            "shoulders": "Плечи",
            "arms": "Руки",
            "chest": "Грудь",
            "core": "Пресс",
            "legs": "Ноги",
            "full_body": "Всё тело",
        }
        items.append(
            {
                "title": "Настраиваем область фокуса",
                "value": focus_labels.get(focus_area, focus_area),
            }
        )
    if isinstance(level, str):
        level_labels = {
            "beginner": "Новичок",
            "intermediate": "Средний",
            "advanced": "Продвинутый",
            "unknown": "Пока не знаю",
        }
        items.append(
            {
                "title": "Выбираем уровень подготовки",
                "value": level_labels.get(level, level),
            }
        )
    return items


def validate_onboarding_data(data: dict[str, object], require_complete: bool = False) -> None:
    errors: list[str] = []

    main_goal = data.get("main_goal")
    if main_goal is not None and main_goal not in MAIN_GOAL_VALUES:
        errors.append("Некорректная цель пользователя.")

    motivation = data.get("motivation")
    if motivation is not None and motivation not in MOTIVATION_VALUES:
        errors.append("Некорректная мотивация.")

    desired_outcome = data.get("desired_outcome")
    if desired_outcome is not None and desired_outcome not in DESIRED_OUTCOME_VALUES:
        errors.append("Некорректный желаемый эффект.")

    focus_area = data.get("focus_area")
    if focus_area is not None and focus_area not in FOCUS_AREA_VALUES:
        errors.append("Некорректная зона проработки.")

    gender = data.get("gender")
    if gender is not None and gender not in GENDER_VALUES:
        errors.append("Некорректное значение пола.")

    fitness_level = data.get("fitness_level")
    if fitness_level is not None and fitness_level not in FITNESS_LEVEL_VALUES:
        errors.append("Некорректный уровень подготовки.")

    activity_level = data.get("activity_level")
    if activity_level is not None and activity_level not in ACTIVITY_LEVEL_VALUES:
        errors.append("Некорректный уровень активности.")

    goal_pace = data.get("goal_pace")
    if goal_pace is not None and goal_pace not in GOAL_PACE_VALUES:
        errors.append("Некорректная скорость достижения цели.")

    calorie_tracking = data.get("calorie_tracking")
    if calorie_tracking is not None and calorie_tracking not in CALORIE_TRACKING_VALUES:
        errors.append("Некорректное отношение к трекингу калорий.")

    diet_type = data.get("diet_type")
    if diet_type is not None and diet_type not in DIET_TYPE_VALUES:
        errors.append("Некорректный тип питания.")

    self_image = data.get("self_image")
    if self_image is not None and self_image not in SELF_IMAGE_VALUES:
        errors.append("Некорректный образ результата.")

    interest_tags = data.get("interest_tags") or []
    if len(interest_tags) > 3:
        errors.append("Можно выбрать не больше 3 форматов тренировок.")
    if any(item not in INTEREST_TAG_VALUES for item in interest_tags):
        errors.append("Некорректные форматы тренировок.")

    equipment_tags = data.get("equipment_tags") or []
    if any(item not in EQUIPMENT_TAG_VALUES for item in equipment_tags):
        errors.append("Некорректный инвентарь.")
    if "none" in equipment_tags and len(equipment_tags) > 1:
        errors.append("Вариант 'без инвентаря' нельзя комбинировать с другими вариантами.")

    injury_areas = data.get("injury_areas") or []
    if any(item not in INJURY_AREA_VALUES for item in injury_areas):
        errors.append("Некорректные зоны травм.")
    if "none" in injury_areas and len(injury_areas) > 1:
        errors.append("Значение 'none' нельзя комбинировать с другими травмами.")

    training_days = data.get("training_days") or []
    if any(item not in TRAINING_DAY_VALUES for item in training_days):
        errors.append("Некорректные дни тренировок.")

    training_frequency = data.get("training_frequency")
    if training_frequency is not None:
        if not isinstance(training_frequency, int) or training_frequency < 1 or training_frequency > 6:
            errors.append("Частота тренировок должна быть от 1 до 6 раз в неделю.")
        elif len(training_days) > training_frequency:
            errors.append("Выбрано слишком много тренировочных дней для текущей частоты.")

    reminders_enabled = bool(data.get("reminders_enabled"))
    reminder_time_local = data.get("reminder_time_local")
    if reminders_enabled and reminder_time_local in (None, "") and require_complete:
        errors.append("Укажите время напоминания.")

    if require_complete:
        required_field_labels = {
            "main_goal": "главную цель",
            "focus_area": "область фокуса",
            "gender": "пол",
            "age": "возраст",
            "height_cm": "рост",
            "current_weight_kg": "текущий вес",
            "fitness_level": "уровень подготовки",
            "activity_level": "уровень активности",
            "goal_pace": "подходящий темп",
            "training_frequency": "частоту тренировок",
        }
        required_scalars = [
            "main_goal",
            "focus_area",
            "gender",
            "age",
            "height_cm",
            "current_weight_kg",
            "fitness_level",
            "activity_level",
            "goal_pace",
            "training_frequency",
        ]
        for field_name in required_scalars:
            if _is_missing_value(data.get(field_name)):
                errors.append(f"Заполните {required_field_labels.get(field_name, field_name)}.")

        if _requires_target_weight(data) and _is_missing_value(data.get("target_weight_kg")):
            errors.append("Укажите желаемый вес.")
        if not interest_tags:
            errors.append("Выберите хотя бы один формат тренировок.")
        if not equipment_tags:
            errors.append("Выберите хотя бы один вариант инвентаря.")
        if not injury_areas:
            errors.append("Укажите травмы или выберите 'none'.")
        if not training_days:
            errors.append("Укажите дни тренировок.")
        elif isinstance(training_frequency, int) and len(training_days) != training_frequency:
            errors.append("Количество дней тренировок должно совпадать с выбранной частотой.")

    if errors:
        raise ValueError(errors[0])
