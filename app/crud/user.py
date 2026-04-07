import secrets
from datetime import datetime, timezone

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.favorite import FavoriteItem
from app.models.goal import Goal
from app.models.notification import Notification
from app.models.onboarding import UserOnboarding
from app.models.profile import Profile
from app.models.program import Program
from app.models.reminder import ReminderRule
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.weight_entry import WeightEntry
from app.models.workout import WorkoutSession


class TelegramLinkConflictError(ValueError):
    pass


def get_public_user_email(user: User) -> str | None:
    if is_telegram_synthetic_email(user.email):
        return None
    return user.email


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.email == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_telegram_user_id(db: Session, telegram_user_id: str) -> User | None:
    stmt: Select[tuple[User]] = select(User).where(User.telegram_user_id == telegram_user_id.strip())
    return db.execute(stmt).scalar_one_or_none()


def normalize_telegram_username(telegram_username: str | None) -> str | None:
    value = str(telegram_username or "").strip().lstrip("@").lower()
    return value or None


def get_user_by_telegram_username(db: Session, telegram_username: str | None) -> User | None:
    normalized = normalize_telegram_username(telegram_username)
    if not normalized:
        return None

    stmt: Select[tuple[User]] = select(User).where(func.lower(User.telegram_username) == normalized)
    return db.execute(stmt).scalar_one_or_none()


def create_user(db: Session, email: str, password: str, name: str | None = None) -> User:
    user = User(
        email=email.strip().lower(),
        password_hash=get_password_hash(password),
        name=name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_name(db: Session, user: User, name: str | None) -> User:
    user.name = name.strip() if isinstance(name, str) and name.strip() else None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_avatar(db: Session, user: User, avatar_url: str | None) -> User:
    user.avatar_url = avatar_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_telegram_link(
    db: Session,
    user: User,
    telegram_user_id: str,
    telegram_username: str | None,
    telegram_first_name: str | None,
    fallback_name: str | None = None,
) -> User:
    user.telegram_user_id = telegram_user_id
    user.telegram_username = normalize_telegram_username(telegram_username)
    user.telegram_first_name = telegram_first_name
    if fallback_name and not (user.name or "").strip():
        user.name = fallback_name.strip()
    if user.telegram_linked_at is None:
        user.telegram_linked_at = datetime.now(timezone.utc)
    user.telegram_last_seen_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def is_telegram_synthetic_email(email: str | None) -> bool:
    value = (email or "").strip().lower()
    return value.startswith("tg_") and value.endswith("@telegram.local")


def _resolve_existing_telegram_user(
    db: Session,
    telegram_user_id: str,
    telegram_username: str | None,
) -> User | None:
    by_username = get_user_by_telegram_username(db, telegram_username)
    by_user_id = get_user_by_telegram_user_id(db, telegram_user_id)

    if by_username is None or by_user_id is None or by_username.id == by_user_id.id:
        return by_username or by_user_id

    if is_telegram_synthetic_email(by_user_id.email):
        user = merge_users(db, by_username, by_user_id)
        db.commit()
        db.refresh(user)
        return user

    if is_telegram_synthetic_email(by_username.email):
        user = merge_users(db, by_user_id, by_username)
        db.commit()
        db.refresh(user)
        return user

    raise TelegramLinkConflictError("Найдено несколько пользователей с одним Telegram username.")


def _merge_profile(target: Profile | None, source: Profile) -> None:
    for field in ("height_cm", "weight_kg", "age", "level", "active_program_id", "workouts_per_week"):
        value = getattr(source, field)
        if value is not None:
            setattr(target, field, value)


def _merge_goal(target: Goal | None, source: Goal) -> None:
    target.goal_type = source.goal_type
    target.target_value = source.target_value
    target.created_at = source.created_at or target.created_at


def _merge_onboarding(target: UserOnboarding | None, source: UserOnboarding) -> None:
    should_replace = (
        (source.is_completed and not target.is_completed)
        or (
            source.updated_at is not None
            and (
                target.updated_at is None
                or source.updated_at >= target.updated_at
            )
        )
    )
    if not should_replace:
        return

    for field in (
        "is_completed",
        "completed_at",
        "main_goal",
        "motivation",
        "desired_outcome",
        "focus_area",
        "gender",
        "current_body_shape",
        "target_body_shape",
        "age",
        "height_cm",
        "current_weight_kg",
        "target_weight_kg",
        "fitness_level",
        "activity_level",
        "goal_pace",
        "training_frequency",
        "calorie_tracking",
        "diet_type",
        "self_image",
        "reminders_enabled",
        "reminder_time_local",
        "onboarding_version",
        "interest_tags",
        "equipment_tags",
        "injury_areas",
        "training_days",
        "created_at",
        "updated_at",
    ):
        setattr(target, field, getattr(source, field))


def _merge_settings(target: UserSettings | None, source: UserSettings) -> None:
    defaults = {
        "theme_preference": "system",
        "language": "ru",
        "weight_unit": "kg",
        "height_unit": "cm",
        "timezone": "UTC",
    }
    for field, default in defaults.items():
        value = getattr(source, field)
        if value and (getattr(target, field) in (None, "", default) or value != default):
            setattr(target, field, value)


def _move_unique_items(db: Session, model, source_user_id: int, target_user_id: int, key_builder) -> None:
    target_rows = {
        key_builder(row): row
        for row in db.execute(select(model).where(model.user_id == target_user_id)).scalars().all()
    }
    source_rows = db.execute(select(model).where(model.user_id == source_user_id)).scalars().all()
    for row in source_rows:
        key = key_builder(row)
        existing = target_rows.get(key)
        if existing is None:
            row.user_id = target_user_id
            target_rows[key] = row
            continue

        source_created = getattr(row, "created_at", None)
        target_created = getattr(existing, "created_at", None)
        if source_created and (target_created is None or source_created > target_created):
            for field in ("weight_kg", "timezone", "created_at"):
                if hasattr(existing, field):
                    setattr(existing, field, getattr(row, field))
        db.delete(row)


def _merge_singletons(db: Session, target_user: User, source_user: User) -> None:
    target_profile = db.execute(select(Profile).where(Profile.user_id == target_user.id)).scalar_one_or_none()
    source_profile = db.execute(select(Profile).where(Profile.user_id == source_user.id)).scalar_one_or_none()
    if source_profile is not None:
        if target_profile is None:
            source_profile.user_id = target_user.id
        else:
            _merge_profile(target_profile, source_profile)
            db.delete(source_profile)

    target_goal = db.execute(select(Goal).where(Goal.user_id == target_user.id)).scalar_one_or_none()
    source_goal = db.execute(select(Goal).where(Goal.user_id == source_user.id)).scalar_one_or_none()
    if source_goal is not None:
        if target_goal is None:
            source_goal.user_id = target_user.id
        else:
            _merge_goal(target_goal, source_goal)
            db.delete(source_goal)

    target_onboarding = db.execute(select(UserOnboarding).where(UserOnboarding.user_id == target_user.id)).scalar_one_or_none()
    source_onboarding = db.execute(select(UserOnboarding).where(UserOnboarding.user_id == source_user.id)).scalar_one_or_none()
    if source_onboarding is not None:
        if target_onboarding is None:
            source_onboarding.user_id = target_user.id
        else:
            _merge_onboarding(target_onboarding, source_onboarding)
            db.delete(source_onboarding)

    target_settings = db.execute(select(UserSettings).where(UserSettings.user_id == target_user.id)).scalar_one_or_none()
    source_settings = db.execute(select(UserSettings).where(UserSettings.user_id == source_user.id)).scalar_one_or_none()
    if source_settings is not None:
        if target_settings is None:
            source_settings.user_id = target_user.id
        else:
            _merge_settings(target_settings, source_settings)
            db.delete(source_settings)


def merge_users(db: Session, target_user: User, source_user: User) -> User:
    if target_user.id == source_user.id:
        return target_user

    _merge_singletons(db, target_user, source_user)
    _move_unique_items(db, FavoriteItem, source_user.id, target_user.id, lambda row: (row.item_type, row.item_id))
    _move_unique_items(db, WeightEntry, source_user.id, target_user.id, lambda row: row.recorded_on_local_date)

    db.execute(update(Notification).where(Notification.user_id == source_user.id).values(user_id=target_user.id))
    db.execute(update(ReminderRule).where(ReminderRule.user_id == source_user.id).values(user_id=target_user.id))
    db.execute(update(WorkoutSession).where(WorkoutSession.user_id == source_user.id).values(user_id=target_user.id))
    db.execute(update(Program).where(Program.owner_user_id == source_user.id).values(owner_user_id=target_user.id))

    source_telegram_user_id = source_user.telegram_user_id
    source_telegram_username = source_user.telegram_username
    source_telegram_first_name = source_user.telegram_first_name
    source_telegram_linked_at = source_user.telegram_linked_at
    source_telegram_last_seen_at = source_user.telegram_last_seen_at

    if source_user.avatar_url and not target_user.avatar_url:
        target_user.avatar_url = source_user.avatar_url
    if source_user.name and not (target_user.name or "").strip():
        target_user.name = source_user.name

    source_user.telegram_user_id = None
    source_user.telegram_username = None
    source_user.telegram_first_name = None
    source_user.telegram_linked_at = None
    source_user.telegram_last_seen_at = None
    db.add(source_user)
    db.flush()

    if source_telegram_user_id and not target_user.telegram_user_id:
        target_user.telegram_user_id = source_telegram_user_id
    if source_telegram_username:
        target_user.telegram_username = source_telegram_username
    if source_telegram_first_name:
        target_user.telegram_first_name = source_telegram_first_name
    if source_telegram_linked_at and target_user.telegram_linked_at is None:
        target_user.telegram_linked_at = source_telegram_linked_at
    if source_telegram_last_seen_at:
        target_user.telegram_last_seen_at = source_telegram_last_seen_at

    db.add(target_user)
    db.flush()
    db.delete(source_user)
    db.flush()
    return target_user


def resolve_user_for_telegram_auth(
    db: Session,
    telegram_user_id: str,
    telegram_username: str | None,
    telegram_first_name: str | None,
    current_user: User | None = None,
) -> User:
    normalized_telegram_user_id = telegram_user_id.strip()
    normalized_telegram_username = normalize_telegram_username(telegram_username)
    fallback_name = (
        (telegram_first_name or normalized_telegram_username or f"Telegram {normalized_telegram_user_id}").strip()
    )
    synthetic_email = f"tg_{normalized_telegram_user_id}@telegram.local"
    linked_user = _resolve_existing_telegram_user(
        db,
        telegram_user_id=normalized_telegram_user_id,
        telegram_username=normalized_telegram_username,
    )

    if current_user is not None:
        current_username = normalize_telegram_username(current_user.telegram_username)
        if (
            current_user.telegram_user_id == normalized_telegram_user_id
            or (normalized_telegram_username and current_username == normalized_telegram_username)
        ):
            return update_user_telegram_link(
                db,
                current_user,
                telegram_user_id=normalized_telegram_user_id,
                telegram_username=normalized_telegram_username,
                telegram_first_name=telegram_first_name,
                fallback_name=fallback_name,
            )

        if current_user.telegram_user_id or current_username:
            if linked_user is not None:
                return update_user_telegram_link(
                    db,
                    linked_user,
                    telegram_user_id=normalized_telegram_user_id,
                    telegram_username=normalized_telegram_username,
                    telegram_first_name=telegram_first_name,
                    fallback_name=fallback_name,
                )
            raise TelegramLinkConflictError("Текущая сессия уже привязана к другому Telegram-аккаунту.")

        if linked_user is not None and linked_user.id != current_user.id:
            if is_telegram_synthetic_email(linked_user.email):
                user = merge_users(db, current_user, linked_user)
                db.commit()
                db.refresh(user)
                return update_user_telegram_link(
                    db,
                    user,
                    telegram_user_id=normalized_telegram_user_id,
                    telegram_username=normalized_telegram_username,
                    telegram_first_name=telegram_first_name,
                    fallback_name=fallback_name,
                )
            return update_user_telegram_link(
                db,
                linked_user,
                telegram_user_id=normalized_telegram_user_id,
                telegram_username=normalized_telegram_username,
                telegram_first_name=telegram_first_name,
                fallback_name=fallback_name,
            )

        return update_user_telegram_link(
            db,
            current_user,
            telegram_user_id=normalized_telegram_user_id,
            telegram_username=normalized_telegram_username,
            telegram_first_name=telegram_first_name,
            fallback_name=fallback_name,
        )

    user = linked_user
    if user is None:
        user = get_user_by_email(db, synthetic_email)
    if user is None:
        user = create_user(
            db,
            email=synthetic_email,
            password=secrets.token_urlsafe(24),
            name=fallback_name,
        )

    return update_user_telegram_link(
        db,
        user,
        telegram_user_id=normalized_telegram_user_id,
        telegram_username=normalized_telegram_username,
        telegram_first_name=telegram_first_name,
        fallback_name=fallback_name,
    )


def link_telegram_account(
    db: Session,
    user: User,
    telegram_user_id: str,
    telegram_username: str | None,
    telegram_first_name: str | None,
) -> User:
    normalized_telegram_user_id = telegram_user_id.strip()
    normalized_telegram_username = normalize_telegram_username(telegram_username)
    existing_user = _resolve_existing_telegram_user(
        db,
        telegram_user_id=normalized_telegram_user_id,
        telegram_username=normalized_telegram_username,
    )
    fallback_name = (telegram_first_name or normalized_telegram_username or f"Telegram {normalized_telegram_user_id}").strip()

    if existing_user is not None and existing_user.id != user.id:
        if not user.telegram_user_id and is_telegram_synthetic_email(existing_user.email):
            merged_user = merge_users(db, user, existing_user)
            db.commit()
            db.refresh(merged_user)
            return update_user_telegram_link(
                db,
                merged_user,
                telegram_user_id=normalized_telegram_user_id,
                telegram_username=normalized_telegram_username,
                telegram_first_name=telegram_first_name,
                fallback_name=fallback_name,
            )
        raise TelegramLinkConflictError("Этот Telegram-аккаунт уже привязан к другому пользователю.")

    return update_user_telegram_link(
        db,
        user,
        telegram_user_id=normalized_telegram_user_id,
        telegram_username=normalized_telegram_username,
        telegram_first_name=telegram_first_name,
        fallback_name=fallback_name,
    )


def get_or_create_user_for_telegram(
    db: Session,
    telegram_user_id: str,
    telegram_username: str | None,
    telegram_first_name: str | None,
) -> User:
    return resolve_user_for_telegram_auth(
        db,
        telegram_user_id=telegram_user_id,
        telegram_username=telegram_username,
        telegram_first_name=telegram_first_name,
        current_user=None,
    )
