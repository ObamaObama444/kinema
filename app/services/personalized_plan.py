from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib import error, request

from app.core.config import settings
from app.core.onboarding import build_onboarding_derived
from app.schemas.plan import PersonalizedPlanResponse

logger = logging.getLogger(__name__)
MISTRAL_REQUEST_TIMEOUT_SEC = 12

MAIN_GOAL_LABELS = {
    "lose_weight": "Сбросить Вес",
    "gain_muscle": "Нарастить Мышечную Массу",
    "stay_fit": "Быть В Форме",
}
MAIN_GOAL_HEADLINES = {
    "lose_weight": "Сжигаем жир",
    "gain_muscle": "Строим силу",
    "stay_fit": "Держим тонус",
}
FOCUS_LABELS = {
    "shoulders": "Плечи",
    "arms": "Руки",
    "chest": "Грудь",
    "core": "Пресс",
    "legs": "Ноги",
    "full_body": "Все тело",
}
FITNESS_LEVEL_LABELS = {
    "beginner": "Новичок",
    "intermediate": "Любитель",
    "advanced": "Продвинутый",
    "unknown": "Адаптивный",
}
INJURY_LABELS = {
    "none": "Нет",
    "shoulders": "Плечи",
    "wrists": "Запястья",
    "knees": "Колени",
    "ankles": "Лодыжки",
}
EQUIPMENT_LABELS = {
    "none": "Нет",
    "dumbbells": "Гантели",
    "bands": "Резинки",
    "gym": "Зал",
}
INTEREST_LABELS = {
    "general": "База",
    "pilates": "Пилатес",
    "chair": "Стул",
    "dumbbells": "Гантели",
    "stretching": "Растяжка",
}
GOAL_PACE_LABELS = {
    "slow": "мягкий темп",
    "moderate": "рабочий темп",
    "fast": "ускоренный темп",
}
DAY_LABELS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
TRAINING_DAY_TO_PY = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
TRAINING_DAY_FALLBACKS = {
    1: ["wed"],
    2: ["tue", "fri"],
    3: ["mon", "wed", "fri"],
    4: ["mon", "tue", "thu", "sat"],
    5: ["mon", "tue", "wed", "fri", "sat"],
    6: ["mon", "tue", "wed", "thu", "sat", "sun"],
}
PLAN_TOTAL_DAYS = 10
PLAN_VERSION = "single_stage_10d_v3"
WORKOUT_EXERCISE_TARGET = 6
RECOVERY_EXERCISE_TARGET = 4
STAGE_CONFIG = [
    {
        "stage_number": 1,
        "badge": "Этап 1",
        "title": "Мягкий вход",
        "subtitle": "Привыкаем к ритму и технике.",
        "intensity": "low",
        "duration_shift": -1,
    },
]
WORKOUT_TITLE_VARIANTS = [
    "Техника и контроль",
    "База на выносливость",
    "Темп и сжигание",
    "Сила и устойчивость",
    "Динамика и дыхание",
    "Уверенный объем",
]
RECOVERY_TITLE_VARIANTS = [
    "Восстановление",
    "Мягкая мобильность",
    "День разгрузки",
    "Контроль корпуса",
]
EXERCISE_LIBRARY = {
    "squat": {"title": "Приседания", "areas": {"legs", "full_body"}, "details": "Базовый темп и контроль корпуса"},
    "pushup": {"title": "Отжимания", "areas": {"chest", "arms", "full_body"}, "details": "Без резких провалов в плечах"},
    "plank": {"title": "Планка", "areas": {"core", "full_body"}, "details": "Держать корпус ровно"},
    "lunge": {"title": "Выпады", "areas": {"legs", "full_body"}, "details": "Шаг назад и контроль колена"},
    "burpee": {"title": "Берпи", "areas": {"full_body"}, "details": "Только если темп уже устойчивый"},
    "band_row": {"title": "Тяга резинки", "areas": {"arms", "shoulders", "full_body"}, "details": "Мягкая тяга на спину и осанку"},
    "glute_bridge": {"title": "Ягодичный мост", "areas": {"legs", "core", "full_body"}, "details": "Ягодицы и задняя цепь"},
    "crunch": {"title": "Скручивания", "areas": {"core", "full_body"}, "details": "Короткая амплитуда и дыхание"},
    "calf_raise": {"title": "Подъемы на носки", "areas": {"legs"}, "details": "Икры и устойчивость голеностопа"},
    "superman": {"title": "Супермен", "areas": {"core", "shoulders", "full_body"}, "details": "Мягкое включение спины"},
    "dead_bug": {"title": "Дэд баг", "areas": {"core", "full_body"}, "details": "Поясница прижата, движения поочередно"},
    "bird_dog": {"title": "Берд-дог", "areas": {"core", "shoulders", "full_body"}, "details": "Баланс и стабилизация корпуса"},
    "side_plank": {"title": "Боковая планка", "areas": {"core", "shoulders", "full_body"}, "details": "Боковая линия корпуса и дыхание"},
    "leg_raise": {"title": "Подъемы ног", "areas": {"core", "full_body"}, "details": "Подконтрольный подъем без рывка"},
    "chair_squat": {"title": "Приседания к стулу", "areas": {"legs", "full_body"}, "details": "Контроль глубины через опору"},
    "wall_sit": {"title": "Стульчик у стены", "areas": {"legs", "full_body"}, "details": "Статика для ног и контроля колен"},
    "good_morning": {"title": "Наклоны с прямой спиной", "areas": {"legs", "core", "full_body"}, "details": "Спина длинная, таз назад"},
    "side_lunge": {"title": "Боковые выпады", "areas": {"legs", "full_body"}, "details": "Работаем в сторону и держим баланс"},
    "donkey_kick": {"title": "Отведение ноги назад", "areas": {"legs", "core", "full_body"}, "details": "Ягодицы и контроль таза"},
    "march_place": {"title": "Шаг на месте", "areas": {"legs", "full_body"}, "details": "Легкое кардио без спешки"},
    "wall_pushup": {"title": "Отжимания от стены", "areas": {"chest", "arms", "full_body"}, "details": "Щадящий угол и ровный корпус"},
    "incline_pushup": {"title": "Отжимания от опоры", "areas": {"chest", "arms", "full_body"}, "details": "Ладони выше опоры, спокойная амплитуда"},
    "shoulder_tap": {"title": "Касания плеч", "areas": {"arms", "shoulders", "core", "full_body"}, "details": "Без раскачки таза"},
    "band_pull_apart": {"title": "Разведение резинки", "areas": {"arms", "shoulders", "full_body"}, "details": "Осанка и задняя дельта"},
    "cat_cow": {"title": "Кошка-корова", "areas": {"core", "full_body"}, "details": "Мобилизация спины и дыхание"},
    "child_pose_reach": {"title": "Вытяжение в позе ребенка", "areas": {"shoulders", "core", "full_body"}, "details": "Мягко вытянуть спину и плечи"},
    "hamstring_fold": {"title": "Наклон на заднюю линию", "areas": {"legs", "full_body"}, "details": "Мягкая растяжка задней поверхности"},
}


def _bounded_int(raw_value: Any, fallback: int, minimum: int, maximum: int) -> int:
    try:
        value = int(float(raw_value))
    except (TypeError, ValueError):
        value = fallback
    return max(minimum, min(maximum, value))


def _compact_text(value: str | None, fallback: str, limit: int = 72) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        text = fallback
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _normalize_list(raw_value: object) -> list[str]:
    if not isinstance(raw_value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        normalized = str(item or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _label_join(values: list[str], mapping: dict[str, str], empty_label: str = "Нет") -> str:
    normalized = [mapping[item] for item in values if item in mapping and item != "none"]
    if not normalized:
        return empty_label
    return ", ".join(normalized[:3])


def _preferred_duration_value(data: dict[str, object]) -> tuple[int, str]:
    level = str(data.get("fitness_level") or "")
    pace = str(data.get("goal_pace") or "")
    base = {"beginner": 10, "intermediate": 16, "advanced": 22}.get(level, 12)
    pace_shift = {"slow": -2, "moderate": 1, "fast": 4}.get(pace, 0)
    minutes = max(8, min(32, base + pace_shift))

    if minutes <= 10:
        label = "<10 мин. в день"
    elif minutes <= 14:
        label = "10-14 мин. в день"
    elif minutes <= 20:
        label = "15-20 мин. в день"
    else:
        label = "20-30 мин. в день"
    return minutes, label


def _resolved_training_days(data: dict[str, object]) -> list[str]:
    explicit = [item for item in _normalize_list(data.get("training_days")) if item in TRAINING_DAY_TO_PY]
    if explicit:
        return explicit
    frequency = int(data.get("training_frequency") or 0)
    return list(TRAINING_DAY_FALLBACKS.get(frequency, ["mon", "wed", "fri"]))


def _build_day_slots(data: dict[str, object]) -> list[dict[str, object]]:
    training_days = {TRAINING_DAY_TO_PY[item] for item in _resolved_training_days(data)}
    start_date = date.today()
    slots: list[dict[str, object]] = []
    for index in range(PLAN_TOTAL_DAYS):
        current_date = start_date + timedelta(days=index)
        slots.append(
            {
                "day_number": index + 1,
                "stage_number": 1,
                "date_label": f"{current_date.day:02d}.{current_date.month:02d} · {DAY_LABELS[current_date.weekday()]}",
                "weekday": current_date.weekday(),
                "is_training_day": current_date.weekday() in training_days,
            }
        )
    return slots


def build_plan_signature(data: dict[str, object], snapshot: dict[str, Any] | None = None) -> str:
    payload = {
        "main_goal": data.get("main_goal"),
        "focus_area": data.get("focus_area"),
        "fitness_level": data.get("fitness_level"),
        "goal_pace": data.get("goal_pace"),
        "training_frequency": data.get("training_frequency"),
        "training_days": _normalize_list(data.get("training_days")),
        "equipment_tags": _normalize_list(data.get("equipment_tags")),
        "injury_areas": _normalize_list(data.get("injury_areas")),
        "interest_tags": _normalize_list(data.get("interest_tags")),
        "height_cm": data.get("height_cm"),
        "current_weight_kg": data.get("current_weight_kg"),
        "target_weight_kg": data.get("target_weight_kg"),
        "activity_level": data.get("activity_level"),
        "model": settings.mistral_plan_model,
        "plan_version": PLAN_VERSION,
        "snapshot_completed_at": (snapshot or {}).get("completed_at"),
        "snapshot_version": (snapshot or {}).get("snapshot_version"),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def _build_summary_items(data: dict[str, object]) -> list[dict[str, str]]:
    _, duration_label = _preferred_duration_value(data)
    return [
        {
            "label": "Сложность Плана",
            "value": FITNESS_LEVEL_LABELS.get(str(data.get("fitness_level") or ""), "Адаптивный"),
        },
        {
            "label": "Область Внимания",
            "value": FOCUS_LABELS.get(str(data.get("focus_area") or ""), "Все тело"),
        },
        {
            "label": "Предпочтительная Продолжительность",
            "value": duration_label,
        },
        {
            "label": "Цель",
            "value": MAIN_GOAL_LABELS.get(str(data.get("main_goal") or ""), "Поддерживать форму"),
        },
        {
            "label": "Травмированная Область",
            "value": _label_join(_normalize_list(data.get("injury_areas")), INJURY_LABELS),
        },
        {
            "label": "Доступное Оборудование",
            "value": _label_join(_normalize_list(data.get("equipment_tags")), EQUIPMENT_LABELS),
        },
    ]


def _fallback_tags(data: dict[str, object], derived: dict[str, object]) -> list[str]:
    injuries = _normalize_list(data.get("injury_areas"))
    tags: list[str] = []
    if injuries and injuries != ["none"]:
        tags.append("Щадящий режим")
    body_fat_delta = derived.get("body_fat_delta_percent")
    if isinstance(body_fat_delta, (int, float)) and body_fat_delta > 0:
        tags.append(f"Жир тела -{abs(float(body_fat_delta)):.0f}%")
    frequency = int(data.get("training_frequency") or 0)
    if frequency > 0:
        tags.append(f"{frequency} трен./нед.")
    interests = _normalize_list(data.get("interest_tags"))
    if interests:
        interest_label = INTEREST_LABELS.get(interests[0])
        if interest_label:
            tags.append(interest_label)
    return tags[:4]


def _exercise_pool(data: dict[str, object], recovery: bool = False) -> list[str]:
    focus = str(data.get("focus_area") or "full_body")
    injuries = set(_normalize_list(data.get("injury_areas")))
    equipment = set(_normalize_list(data.get("equipment_tags")))
    level = str(data.get("fitness_level") or "beginner")
    pool: list[str] = []

    if recovery:
        base = ["cat_cow", "bird_dog", "glute_bridge", "calf_raise", "dead_bug", "hamstring_fold", "child_pose_reach"]
        if "shoulders" in injuries:
            base = ["glute_bridge", "calf_raise", "dead_bug", "hamstring_fold"]
        if "wrists" in injuries:
            base = [slug for slug in base if slug not in {"bird_dog", "plank"}]
        return base

    for slug, item in EXERCISE_LIBRARY.items():
        areas = item["areas"]
        if focus in areas or "full_body" in areas:
            pool.append(slug)

    if "shoulders" in injuries:
        pool = [slug for slug in pool if slug not in {"pushup", "incline_pushup", "wall_pushup", "band_row", "band_pull_apart", "shoulder_tap", "side_plank", "burpee"}]
    if "wrists" in injuries:
        pool = [slug for slug in pool if slug not in {"pushup", "incline_pushup", "wall_pushup", "plank", "side_plank", "shoulder_tap", "burpee"}]
    if "knees" in injuries:
        pool = [slug for slug in pool if slug not in {"burpee", "side_lunge"}]
    if "none" in equipment:
        pool = [slug for slug in pool if slug not in {"band_row", "band_pull_apart"}]
    if level == "beginner":
        pool = [slug for slug in pool if slug not in {"burpee"}]

    if not pool:
        pool = ["glute_bridge", "dead_bug", "crunch", "chair_squat", "march_place"]
    return pool


def _exercise_payload(slug: str, sets: int, reps: int, rest_sec: int) -> dict[str, object]:
    item = EXERCISE_LIBRARY.get(slug, {"title": slug, "details": ""})
    return {
        "slug": slug,
        "title": str(item["title"]),
        "details": str(item["details"]),
        "sets": sets,
        "reps": reps,
        "rest_sec": rest_sec,
    }


def _fallback_exercises(data: dict[str, object], stage_number: int, kind: str, workout_index: int) -> list[dict[str, object]]:
    recovery = kind == "recovery"
    pool = _exercise_pool(data, recovery=recovery)
    count = RECOVERY_EXERCISE_TARGET if recovery else WORKOUT_EXERCISE_TARGET
    start = workout_index % len(pool)
    selected = [pool[(start + offset) % len(pool)] for offset in range(count)]
    sets = 1 if recovery else min(4, 2 + stage_number)
    reps = 10 if recovery else 8 + (stage_number * 2)
    rest_sec = 25 if recovery else max(20, 55 - (stage_number * 5))
    return [_exercise_payload(slug, sets, reps, rest_sec) for slug in selected]


def _workout_duration(base_minutes: int, stage_number: int, workout_index: int) -> int:
    shift = STAGE_CONFIG[stage_number - 1]["duration_shift"]
    wave = (workout_index % 3) - 1
    return max(8, min(40, base_minutes + int(shift) + wave * 2))


def _intensity_label(value: str) -> str:
    return {
        "low": "Легкий темп",
        "medium": "Рабочий темп",
        "high": "Плотный темп",
    }.get(value, "Рабочий темп")


def _focus_title(data: dict[str, object]) -> str:
    return FOCUS_LABELS.get(str(data.get("focus_area") or ""), "Все тело")


def _goal_headline(data: dict[str, object]) -> str:
    return MAIN_GOAL_HEADLINES.get(str(data.get("main_goal") or ""), "Держим тонус")


def _day_fallback(slot: dict[str, object], data: dict[str, object], derived: dict[str, object], workout_index: int) -> dict[str, object]:
    stage_number = int(slot["stage_number"])
    base_minutes, _ = _preferred_duration_value(data)
    focus_title = _focus_title(data)
    injuries = _normalize_list(data.get("injury_areas"))
    stage_config = STAGE_CONFIG[stage_number - 1]

    if slot["is_training_day"]:
        duration = _workout_duration(base_minutes, stage_number, workout_index)
        intensity = stage_config["intensity"]
        title = WORKOUT_TITLE_VARIANTS[(int(slot["day_number"]) + workout_index) % len(WORKOUT_TITLE_VARIANTS)]
        subtitle = f"{focus_title} · {MAIN_GOAL_LABELS.get(str(data.get('main_goal') or ''), 'Форма')}"
        note = "Щадим плечи и убираем резкие амплитуды." if "shoulders" in injuries else (
            "Снижаем ударную нагрузку и держим ось колена." if "knees" in injuries else (
                "Держим технику, дыхание и ровный темп без перегруза."
            )
        )
        kcal = max(45, int(round(duration * (5.8 + stage_number * 0.4))))
        emphasis = "Фокус: " + focus_title
        kind = "workout"
    else:
        duration = max(6, base_minutes - 3)
        intensity = "low"
        title = RECOVERY_TITLE_VARIANTS[int(slot["day_number"]) % len(RECOVERY_TITLE_VARIANTS)]
        subtitle = "Подвижность, дыхание и мягкое восстановление"
        note = "Короткая прогулка, растяжка и контроль самочувствия."
        kcal = max(18, int(round(duration * 3.2)))
        emphasis = "Фокус: восстановление"
        kind = "recovery"

    return {
        "day_number": int(slot["day_number"]),
        "stage_number": stage_number,
        "date_label": str(slot["date_label"]),
        "title": title,
        "subtitle": subtitle,
        "duration_min": duration,
        "estimated_kcal": kcal,
        "intensity": _intensity_label(intensity),
        "emphasis": emphasis,
        "note": note,
        "kind": kind,
        "exercises": _fallback_exercises(data, stage_number, kind, workout_index),
        "is_highlighted": False,
    }


def _group_stages(days: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: list[dict[str, object]] = []
    for stage_config in STAGE_CONFIG:
        stage_number = int(stage_config["stage_number"])
        grouped.append(
            {
                "stage_number": stage_number,
                "title": stage_config["title"],
                "subtitle": stage_config["subtitle"],
                "badge": stage_config["badge"],
                "days": [item for item in days if item["stage_number"] == stage_number],
            }
        )
    return grouped


def build_fallback_plan(
    data: dict[str, object],
    *,
    signature: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> PersonalizedPlanResponse:
    derived = build_onboarding_derived(data)
    signature_value = signature or build_plan_signature(data, snapshot=snapshot)
    slots = _build_day_slots(data)
    days: list[dict[str, object]] = []
    workout_index = 0
    for slot in slots:
        day = _day_fallback(slot, data, derived, workout_index)
        if slot["is_training_day"]:
            workout_index += 1
        days.append(day)

    for item in days:
        if item["kind"] == "workout":
            item["is_highlighted"] = True
            break

    payload = {
        "signature": signature_value,
        "source": "fallback",
        "generated_at": datetime.now(timezone.utc),
        "headline": _focus_title(data),
        "subheadline": _goal_headline(data),
        "tags": _fallback_tags(data, derived),
        "summary_items": _build_summary_items(data),
        "stages": _group_stages(days),
    }
    return PersonalizedPlanResponse.model_validate(payload)


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Mistral response does not contain choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("Mistral response does not contain message.")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "\n".join(parts)
    raise ValueError("Mistral response content is empty.")


def _strip_code_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _normalize_kind(raw_value: Any, fallback_kind: str) -> str:
    normalized = str(raw_value or "").strip().lower()
    if normalized in {"recovery", "rest", "restore", "восстановление", "восстановление/мобилити", "отдых"}:
        return "recovery"
    if normalized in {"workout", "training", "train", "тренировка", "тренировка/кардио", "силовая", "warm_up", "strength"}:
        return "workout"
    return fallback_kind


def _normalize_exercise_slug(raw_value: Any) -> str:
    normalized = _compact_text(str(raw_value or ""), "", 32).lower().replace("-", "_").replace(" ", "_")
    return normalized.strip("_")


def _exercise_reference(slug: str) -> dict[str, str]:
    normalized_slug = _normalize_exercise_slug(slug)
    item = EXERCISE_LIBRARY.get(normalized_slug)
    if not item:
        return {"slug": normalized_slug, "title": "", "details": ""}
    return {
        "slug": normalized_slug,
        "title": str(item["title"]),
        "details": str(item["details"]),
    }


def _allowed_exercises_for_prompt(data: dict[str, object]) -> dict[str, list[dict[str, str]]]:
    workout_items: list[dict[str, str]] = []
    recovery_items: list[dict[str, str]] = []

    for slug in _exercise_pool(data, recovery=False):
        workout_items.append(_exercise_reference(slug))
    for slug in _exercise_pool(data, recovery=True):
        recovery_items.append(_exercise_reference(slug))

    return {
        "workout": workout_items[:12],
        "recovery": recovery_items[:8],
    }


def _mistral_model_candidates() -> list[str]:
    configured = str(settings.mistral_plan_model or "").strip()
    candidates = [
        "mistral-small-latest",
        configured,
        "open-mistral-nemo",
        "mistral-small-2506",
    ]
    result: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _json_load_object(value: str) -> dict[str, Any]:
    stripped = _strip_code_fence(value).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(stripped[start:end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("Mistral payload is not an object.")
    return parsed


def _call_mistral(messages: list[dict[str, str]], *, model: str, max_tokens: int) -> dict[str, Any]:
    api_key = settings.mistral_api_key.strip()
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not configured.")

    endpoint = settings.mistral_api_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_object",
        },
    }
    req = request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with request.urlopen(req, timeout=MISTRAL_REQUEST_TIMEOUT_SEC) as response:
        raw_body = response.read().decode("utf-8")
    return json.loads(raw_body)


def _build_plan_mistral_prompt(
    data: dict[str, object],
    fallback_plan: PersonalizedPlanResponse,
    snapshot: dict[str, Any] | None,
) -> list[dict[str, str]]:
    injuries = _label_join(_normalize_list(data.get("injury_areas")), INJURY_LABELS)
    equipment = _label_join(_normalize_list(data.get("equipment_tags")), EQUIPMENT_LABELS)
    allowed_exercises = _allowed_exercises_for_prompt(data)
    fallback_stage = fallback_plan.stages[0]
    plan_days = [
        {
            "day_number": int(day.day_number),
            "date_label": str(day.date_label),
            "is_training_day": str(day.kind) == "workout",
            "fallback_title": str(day.title),
            "fallback_subtitle": str(day.subtitle),
        }
        for day in fallback_stage.days
    ]

    system_prompt = (
        "Ты составляешь цельный персональный домашний фитнес-план на 10 дней. "
        "Верни только JSON объект на русском языке. "
        "Нужны keys: headline, subheadline, tags, stage. "
        "headline — короткий фокус плана, например Ноги или Пресс. "
        "subheadline — короткая цель в верхнем регистре, например Сжигаем жир. "
        "tags — массив из 3 коротких зеленых плашек. "
        "stage — объект с keys: stage_number, title, subtitle, badge, days. "
        "В days верни ровно 10 объектов без сокращения списка. "
        "day_number должен идти подряд от 1 до 10. "
        "Каждый day должен содержать keys: day_number, title, subtitle, note, kind, exercises. "
        "kind должен быть workout или recovery. Для workout верни 6-7 упражнений. Для recovery верни 4-5 щадящих упражнения. "
        "Не возвращай дни с 2-3 упражнениями. Если сомневаешься, добавь еще безопасные упражнения из allowed_exercises. "
        "Используй только упражнения из allowed_exercises. "
        "Не пиши markdown. Не добавляй пояснений вне JSON. Строки делай короткими и пригодными для мобильного интерфейса."
    )
    user_prompt = json.dumps(
        {
            "first_interview_snapshot": snapshot or {"data": data},
            "plan_identity": {
                "focus_area_hint": _focus_title(data),
                "goal_headline_hint": _goal_headline(data),
                "fitness_level": FITNESS_LEVEL_LABELS.get(str(data.get("fitness_level") or ""), "Адаптивный"),
                "injuries": injuries,
                "equipment": equipment,
                "fallback_tags_hint": list(fallback_plan.tags),
            },
            "plan_request": {
                "days_total": PLAN_TOTAL_DAYS,
                "headline_fallback": fallback_plan.headline,
                "subheadline_fallback": fallback_plan.subheadline,
                "summary_items": [item.model_dump() for item in fallback_plan.summary_items],
                "stage_number": int(fallback_stage.stage_number),
                "title_hint": str(fallback_stage.title),
                "subtitle_hint": str(fallback_stage.subtitle),
                "badge": str(fallback_stage.badge),
                "day_number_sequence": list(range(1, PLAN_TOTAL_DAYS + 1)),
                "days": plan_days,
            },
            "allowed_exercises": allowed_exercises,
        },
        ensure_ascii=False,
        indent=2,
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_plan_container(raw_payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_payload.get("plan"), dict):
        return raw_payload["plan"]
    if isinstance(raw_payload.get("fitness_plan"), dict):
        return raw_payload["fitness_plan"]
    return raw_payload


def _extract_stage_container(raw_payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_payload.get("stage"), dict):
        return raw_payload["stage"]
    if isinstance(raw_payload.get("stages"), list) and raw_payload["stages"]:
        first_stage = raw_payload["stages"][0]
        if isinstance(first_stage, dict):
            return first_stage
    if isinstance(raw_payload.get("days"), list):
        return raw_payload
    return raw_payload


def _extract_stage_days(container: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [
        container.get("days"),
        container.get("plan_days"),
        container.get("schedule"),
        container.get("items"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _normalize_exercises(raw_value: Any, fallback_exercises: list[Any]) -> list[dict[str, object]]:
    if not isinstance(raw_value, list) or not raw_value:
        return [item.model_dump() if hasattr(item, "model_dump") else item for item in fallback_exercises]

    fallback_list = [item.model_dump() if hasattr(item, "model_dump") else item for item in fallback_exercises]
    fallback_kind = "workout"
    if fallback_list:
        sets_sample = int((fallback_list[0] or {}).get("sets") or 0)
        fallback_kind = "recovery" if sets_sample <= 1 else "workout"
    minimum_count = RECOVERY_EXERCISE_TARGET if fallback_kind == "recovery" else WORKOUT_EXERCISE_TARGET
    result: list[dict[str, object]] = []
    seen_slugs: set[str] = set()
    for index, item in enumerate(raw_value[:8]):
        if not isinstance(item, dict):
            continue

        raw_slug = item.get("slug") or item.get("id") or item.get("exercise")
        raw_title = item.get("title") or item.get("name") or item.get("exercise")
        reference = _exercise_reference(str(raw_slug or raw_title or ""))
        fallback_exercise = fallback_list[min(index, len(fallback_list) - 1)] if fallback_list else {}

        slug = _normalize_exercise_slug(raw_slug or raw_title or fallback_exercise.get("slug"))
        title = _compact_text(
            raw_title or reference.get("title") or fallback_exercise.get("title"),
            "Упражнение",
            32,
        )
        details = _compact_text(
            item.get("details") or item.get("description") or reference.get("details") or fallback_exercise.get("details"),
            "",
            44,
        )
        reps_value = item.get("reps")
        if reps_value in (None, ""):
            reps_value = item.get("duration") or fallback_exercise.get("reps") or 10
        rest_value = item.get("rest_sec")
        if rest_value in (None, ""):
            rest_value = item.get("rest") or fallback_exercise.get("rest_sec") or 30

        normalized_slug = slug or _normalize_exercise_slug(fallback_exercise.get("slug"))
        if normalized_slug in seen_slugs:
            continue
        seen_slugs.add(normalized_slug)

        result.append(
            {
                "slug": normalized_slug,
                "title": title,
                "details": details,
                "sets": _bounded_int(item.get("sets"), int(fallback_exercise.get("sets") or 2), 1, 10),
                "reps": _bounded_int(reps_value, int(fallback_exercise.get("reps") or 10), 1, 60),
                "rest_sec": _bounded_int(rest_value, int(fallback_exercise.get("rest_sec") or 30), 0, 300),
            }
        )

    for fallback_exercise in fallback_list:
        fallback_slug = _normalize_exercise_slug(fallback_exercise.get("slug"))
        if fallback_slug in seen_slugs:
            continue
        result.append(fallback_exercise)
        seen_slugs.add(fallback_slug)
        if len(result) >= minimum_count:
            break

    if result:
        return result
    return fallback_list


def _normalize_tags(raw_value: Any, fallback_tags: list[str]) -> list[str]:
    values: list[str] = []
    if isinstance(raw_value, list):
        for item in raw_value:
            text = _compact_text(str(item or ""), "", 24)
            if text:
                values.append(text)
    elif isinstance(raw_value, str):
        values = [_compact_text(item, "", 24) for item in raw_value.split(",")]
    values = [item for item in values if item]
    if not values:
        values = list(fallback_tags)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped[:3]


def _normalize_stage_plan(raw_payload: dict[str, Any], fallback_stage: Any) -> dict[str, object]:
    container = _extract_stage_container(raw_payload)
    raw_days = _extract_stage_days(container)
    if not raw_days:
        raise ValueError("Stage payload must contain at least one day.")

    fallback_days = list(fallback_stage.days)
    fallback_by_number = {int(day.day_number): day for day in fallback_days}
    normalized_days: list[dict[str, object]] = []
    used_day_numbers: set[int] = set()

    for index, raw_day in enumerate(raw_days):
        fallback_seed = fallback_days[min(index, len(fallback_days) - 1)]
        raw_day_number = _bounded_int(
            raw_day.get("day_number") or raw_day.get("day"),
            int(fallback_seed.day_number),
            1,
            PLAN_TOTAL_DAYS,
        )
        if raw_day_number in used_day_numbers:
            continue
        fallback_day = fallback_by_number.get(raw_day_number) or fallback_seed
        normalized_days.append(
            {
                "day_number": int(fallback_day.day_number),
                "stage_number": int(fallback_stage.stage_number),
                "date_label": str(fallback_day.date_label),
                "title": _compact_text(raw_day.get("title"), str(fallback_day.title), 34),
                "subtitle": _compact_text(raw_day.get("subtitle"), str(fallback_day.subtitle), 44),
                "duration_min": int(fallback_day.duration_min),
                "estimated_kcal": int(fallback_day.estimated_kcal),
                "intensity": str(fallback_day.intensity),
                "emphasis": str(fallback_day.emphasis),
                "note": _compact_text(raw_day.get("note") or raw_day.get("description"), str(fallback_day.note), 88),
                "kind": _normalize_kind(raw_day.get("kind") or raw_day.get("type"), str(fallback_day.kind)),
                "exercises": _normalize_exercises(raw_day.get("exercises") or raw_day.get("workout"), list(fallback_day.exercises)),
                "is_highlighted": False,
            }
        )
        used_day_numbers.add(int(fallback_day.day_number))

    for fallback_day in fallback_days:
        day_number = int(fallback_day.day_number)
        if day_number in used_day_numbers:
            continue
        normalized_days.append(fallback_day.model_dump(mode="json"))

    normalized_days.sort(key=lambda item: int(item["day_number"]))
    normalized_days = normalized_days[: len(fallback_days)]
    return {
        "stage_number": int(fallback_stage.stage_number),
        "title": _compact_text(container.get("title"), str(fallback_stage.title), 28),
        "subtitle": _compact_text(container.get("subtitle"), str(fallback_stage.subtitle), 46),
        "badge": _compact_text(container.get("badge"), str(fallback_stage.badge), 16),
        "days": normalized_days,
    }


def _normalize_plan_payload(
    raw_payload: dict[str, Any],
    fallback_plan: PersonalizedPlanResponse,
    data: dict[str, object],
) -> dict[str, object]:
    container = _extract_plan_container(raw_payload)
    fallback_stage = fallback_plan.stages[0]
    normalized_stage = _normalize_stage_plan(container, fallback_stage)

    raw_headline = container.get("headline") or container.get("focus") or container.get("title")
    raw_subheadline = container.get("subheadline") or container.get("goal") or container.get("headline_secondary")
    headline = _compact_text(str(raw_headline or ""), "", 22)
    subheadline = _compact_text(str(raw_subheadline or ""), "", 28)
    if not headline:
        raise ValueError("Mistral payload must contain headline.")
    if not subheadline:
        raise ValueError("Mistral payload must contain subheadline.")

    payload = {
        "signature": fallback_plan.signature,
        "source": "mistral",
        "generated_at": datetime.now(timezone.utc),
        "headline": headline,
        "subheadline": subheadline,
        "tags": _normalize_tags(container.get("tags") or container.get("pills"), list(fallback_plan.tags)),
        "summary_items": _build_summary_items(data),
        "stages": [normalized_stage],
    }
    return payload


def generate_personalized_plan(
    data: dict[str, object],
    *,
    snapshot: dict[str, Any] | None = None,
) -> PersonalizedPlanResponse:
    fallback = build_fallback_plan(data, snapshot=snapshot)
    last_exc: Exception | None = None
    messages = _build_plan_mistral_prompt(data, fallback, snapshot)

    for model in _mistral_model_candidates():
        try:
            response_payload = _call_mistral(messages, model=model, max_tokens=3800)
            content = _extract_message_content(response_payload)
            parsed = _json_load_object(content)
            plan = PersonalizedPlanResponse.model_validate(_normalize_plan_payload(parsed, fallback, data))
            logger.info("Personalized plan generated with Mistral model %s", model)
            return plan
        except (RuntimeError, ValueError, json.JSONDecodeError, error.URLError, error.HTTPError, TimeoutError) as exc:
            last_exc = exc
            logger.warning("Mistral plan generation failed with model %s: %s", model, exc)

    logger.warning("Falling back to local plan generator after model cascade: %s", last_exc)
    return fallback
