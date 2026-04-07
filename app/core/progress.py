from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.goal import get_goal_by_user_id
from app.crud.onboarding import get_user_onboarding
from app.crud.profile import get_active_program_snapshot, get_profile_by_user_id
from app.crud.weight import list_weight_entries
from app.models.user import User
from app.models.workout_checkin import WorkoutCheckin
from app.models.workout import WorkoutSession

_COMPLETED_SESSION_STATUSES = {"finished", "stopped"}
_WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
_TRAINING_DAY_FALLBACKS = {
    1: ["wed"],
    2: ["tue", "fri"],
    3: ["mon", "wed", "fri"],
    4: ["mon", "tue", "thu", "sat"],
    5: ["mon", "tue", "wed", "fri", "sat"],
    6: ["mon", "tue", "wed", "thu", "sat", "sun"],
}
_MONTH_NAMES_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}
_MONTH_NAMES_EN = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}
_WEEKDAY_LABELS_RU = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}
_WEEKDAY_LABELS_EN = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def bmi_label(bmi: float | None, language: str = "ru") -> str | None:
    if bmi is None:
        return None
    if bmi < 18.5:
        return "Ниже нормы" if language == "ru" else "Underweight"
    if bmi < 25:
        return "Норма" if language == "ru" else "Normal"
    if bmi < 30:
        return "Избыточный" if language == "ru" else "Overweight"
    return "Высокий" if language == "ru" else "High"


def compute_bmi(height_cm: int | None, weight_kg: float | None) -> float | None:
    if not height_cm or weight_kg is None:
        return None
    if height_cm <= 0:
        return None
    return round(float(weight_kg) / ((float(height_cm) / 100.0) ** 2), 1)


def resolve_timezone_name(timezone_name: str | None) -> str:
    if not timezone_name:
        return "UTC"
    try:
        ZoneInfo(timezone_name)
    except Exception:
        return "UTC"
    return timezone_name


def resolve_calendar_month(month_key: str | None, today_local: date) -> date:
    if not month_key:
        return today_local.replace(day=1)
    try:
        year_str, month_str = month_key.split("-", 1)
        return date(int(year_str), int(month_str), 1)
    except (TypeError, ValueError):
        raise ValueError("Некорректный формат месяца. Используйте YYYY-MM.")


def build_progress_summary(
    db: Session,
    user: User,
    settings_language: str = "ru",
    settings_timezone: str = "UTC",
    month_key: str | None = None,
) -> dict[str, object]:
    timezone_name = resolve_timezone_name(settings_timezone)
    tz = ZoneInfo(timezone_name)
    today_local = datetime.now(timezone.utc).astimezone(tz).date()
    month_start = resolve_calendar_month(month_key, today_local)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    profile = get_profile_by_user_id(db, user.id)
    active_program = get_active_program_snapshot(db, user.id, profile)
    current_goal = get_goal_by_user_id(db, user.id)
    onboarding = get_user_onboarding(db, user.id)
    training_days = []
    if onboarding and onboarding.training_days:
        import json

        try:
            parsed = json.loads(onboarding.training_days)
            if isinstance(parsed, list):
                training_days = [str(item).strip().lower() for item in parsed if str(item).strip().lower() in _WEEKDAY_INDEX]
        except json.JSONDecodeError:
            training_days = []
    if not training_days and onboarding and isinstance(onboarding.training_frequency, int):
        training_days = list(_TRAINING_DAY_FALLBACKS.get(onboarding.training_frequency, []))

    sessions = list(
        db.execute(
            select(WorkoutSession).where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.status.in_(_COMPLETED_SESSION_STATUSES),
            )
        ).scalars().all()
    )
    completed_dates: set[date] = set()
    for session in sessions:
        source_dt = session.ended_at or session.started_at
        if source_dt is None:
            continue
        local_date = source_dt.astimezone(tz).date() if source_dt.tzinfo else source_dt.replace(tzinfo=timezone.utc).astimezone(tz).date()
        completed_dates.add(local_date)

    manual_checkins = list(
        db.execute(
            select(WorkoutCheckin).where(
                WorkoutCheckin.user_id == user.id,
                WorkoutCheckin.local_date >= month_start,
                WorkoutCheckin.local_date <= month_end,
            )
        ).scalars().all()
    )
    manual_completed_dates = {item.local_date for item in manual_checkins}

    streak_days = 0
    cursor = today_local
    all_completed_dates = completed_dates | manual_completed_dates
    while cursor in all_completed_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    calendar_days: list[dict[str, object]] = []
    current_day = month_start
    weekday_map = _WEEKDAY_LABELS_EN if settings_language == "en" else _WEEKDAY_LABELS_RU
    planned_weekdays = {_WEEKDAY_INDEX[item] for item in training_days}
    while current_day <= month_end:
        is_session_completed = current_day in completed_dates
        is_manual_completed = current_day in manual_completed_dates
        calendar_days.append(
            {
                "date": current_day,
                "day_number": current_day.day,
                "weekday_short": weekday_map.get(current_day.weekday(), ""),
                "is_planned": current_day.weekday() in planned_weekdays,
                "is_completed": is_session_completed or is_manual_completed,
                "is_manual_completed": is_manual_completed,
                "is_session_completed": is_session_completed,
                "is_today": current_day == today_local,
                "can_toggle": current_day <= today_local and not is_session_completed,
            }
        )
        current_day += timedelta(days=1)

    weight_entries = list_weight_entries(db, user.id)
    latest_weight = weight_entries[-1].weight_kg if weight_entries else (float(profile.weight_kg) if profile and profile.weight_kg is not None else None)
    initial_weight = weight_entries[0].weight_kg if weight_entries else latest_weight
    previous_weight = None
    previous_days_ago = None
    if len(weight_entries) >= 2:
        previous_entry = weight_entries[-2]
        previous_weight = previous_entry.weight_kg
        previous_days_ago = max(1, (today_local - previous_entry.recorded_on_local_date).days)

    bmi = compute_bmi(profile.height_cm if profile else None, latest_weight)
    month_name_map = _MONTH_NAMES_EN if settings_language == "en" else _MONTH_NAMES_RU

    return {
        "active_program": active_program,
        "current_goal": current_goal,
        "streak_days": streak_days,
        "completed_this_month": len([item for item in all_completed_dates if month_start <= item <= month_end]),
        "month_key": month_start.strftime("%Y-%m"),
        "month_label": f"{month_name_map.get(month_start.month, '')} {month_start.year}".strip(),
        "calendar_days": calendar_days,
        "latest_weight_kg": round(latest_weight, 1) if latest_weight is not None else None,
        "initial_weight_kg": round(initial_weight, 1) if initial_weight is not None else None,
        "previous_weight_kg": round(previous_weight, 1) if previous_weight is not None else None,
        "previous_weight_days_ago": previous_days_ago,
        "bmi": bmi,
        "bmi_label": bmi_label(bmi, language=settings_language),
        "weight_points": [
            {"date": entry.recorded_on_local_date, "weight_kg": round(entry.weight_kg, 1)}
            for entry in weight_entries[-12:]
        ],
    }
