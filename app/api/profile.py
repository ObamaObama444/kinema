from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.deps import get_db
from app.core.progress import bmi_label, compute_bmi, resolve_timezone_name
from app.crud.goal import GoalAlreadyExistsError, create_goal, delete_goal_by_user_id, get_goal_by_user_id
from app.crud.notification import create_notification_safe
from app.crud.onboarding import get_effective_user_onboarding
from app.crud.profile import get_active_program_snapshot, get_or_create_profile, get_profile_by_user_id, upsert_profile
from app.crud.settings import get_or_create_user_settings
from app.crud.weight import get_latest_weight_entry, list_weight_entries
from app.crud.user import get_public_user_email, update_user_avatar, update_user_name
from app.models.user import User
from app.models.weight_entry import WeightEntry
from app.schemas.goal import GoalCreateRequest, GoalResponse
from app.schemas.settings import UserSettingsPatchRequest, UserSettingsResponse
from app.schemas.weight import WeightEntryCreateRequest, WeightEntryResponse, WeightHistorySummaryResponse
from app.schemas.profile import AccountResponse, AccountUpdateRequest, ProfileResponse, ProfileUpdateRequest
from app.schemas.program import ActiveProgramSummary

router = APIRouter(tags=["profile"])

MAX_AVATAR_SIZE_BYTES = 3 * 1024 * 1024
ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class DeleteGoalResponse(BaseModel):
    ok: bool


def _avatars_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static" / "media" / "avatars"


def _avatar_path_from_url(avatar_url: str | None) -> Path | None:
    if not avatar_url:
        return None

    prefix = "/static/media/avatars/"
    if not avatar_url.startswith(prefix):
        return None

    filename = avatar_url[len(prefix):].strip()
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return None

    return _avatars_dir() / filename


def _remove_avatar_file(file_path: Path | None) -> None:
    if file_path is None:
        return

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return


def _build_profile_response(db: Session, current_user: User) -> ProfileResponse:
    profile = get_profile_by_user_id(db, current_user.id)
    goal = get_goal_by_user_id(db, current_user.id)
    active_program_snapshot = get_active_program_snapshot(db, current_user.id, profile)
    public_email = get_public_user_email(current_user)

    if profile is None:
        return ProfileResponse(
            user_id=current_user.id,
            email=public_email,
            name=current_user.name,
            avatar_url=current_user.avatar_url,
            telegram_linked=bool(current_user.telegram_user_id),
            telegram_user_id=current_user.telegram_user_id,
            telegram_username=current_user.telegram_username,
            telegram_first_name=current_user.telegram_first_name,
            current_goal=GoalResponse.model_validate(goal) if goal else None,
            active_program=ActiveProgramSummary.model_validate(active_program_snapshot)
            if active_program_snapshot
            else None,
        )

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        email=public_email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        age=profile.age,
        level=profile.level,
        active_program_id=profile.active_program_id,
        workouts_per_week=profile.workouts_per_week,
        telegram_linked=bool(current_user.telegram_user_id),
        telegram_user_id=current_user.telegram_user_id,
        telegram_username=current_user.telegram_username,
        telegram_first_name=current_user.telegram_first_name,
        current_goal=GoalResponse.model_validate(goal) if goal else None,
        active_program=ActiveProgramSummary.model_validate(active_program_snapshot)
        if active_program_snapshot
        else None,
    )


def _build_settings_response(db: Session, current_user: User) -> UserSettingsResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    db.commit()
    db.refresh(current_settings)
    return UserSettingsResponse(
        theme_preference=current_settings.theme_preference,
        language=current_settings.language,
        weight_unit=current_settings.weight_unit,
        height_unit=current_settings.height_unit,
        timezone=current_settings.timezone,
        telegram_linked=bool(current_user.telegram_user_id),
        telegram_username=current_user.telegram_username,
        telegram_first_name=current_user.telegram_first_name,
        telegram_user_id=current_user.telegram_user_id,
        telegram_bot_username=settings.telegram_bot_username or None,
    )


def _build_account_response(user: User) -> AccountResponse:
    return AccountResponse(
        id=user.id,
        email=get_public_user_email(user),
        name=user.name,
        avatar_url=user.avatar_url,
    )


def _weight_delta_for_days(entries: list[WeightEntry], today_local, days: int) -> float:
    if not entries:
        return 0.0
    window_start = today_local - timedelta(days=max(0, days - 1))
    window_entries = [item for item in entries if item.recorded_on_local_date >= window_start]
    if not window_entries:
        return 0.0
    latest = float(entries[-1].weight_kg)
    baseline = float(window_entries[0].weight_kg)
    return round(latest - baseline, 1)


def _normalize_entry_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _weight_history_response(db: Session, current_user: User) -> WeightHistorySummaryResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    current_timezone = resolve_timezone_name(current_settings.timezone)
    tz = ZoneInfo(current_timezone)
    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    entries = list_weight_entries(db, current_user.id)
    latest_entry = get_latest_weight_entry(db, current_user.id)
    profile = get_or_create_profile(db, current_user.id)
    onboarding = get_effective_user_onboarding(db, current_user.id)
    latest_weight = entries[-1].weight_kg if entries else (float(profile.weight_kg) if profile.weight_kg is not None else None)
    initial_weight = entries[0].weight_kg if entries else latest_weight
    previous_weight = None
    latest_days_ago = None
    if len(entries) >= 2:
        previous_weight = entries[-2].weight_kg
        latest_days_ago = max(1, (today_local - entries[-2].recorded_on_local_date).days)
    bmi = compute_bmi(profile.height_cm, latest_weight)
    latest_entry_created_at = _normalize_entry_datetime(latest_entry.created_at if latest_entry else None)
    next_allowed_at = None
    hours_until_next_entry = None
    can_add_now = True
    if latest_entry_created_at is not None:
        next_allowed_at = latest_entry_created_at + timedelta(hours=5)
        can_add_now = now_utc >= next_allowed_at
        if not can_add_now:
            remaining = next_allowed_at - now_utc
            hours_until_next_entry = round(max(0.0, remaining.total_seconds() / 3600), 1)

    return WeightHistorySummaryResponse(
        entries=[
            WeightEntryResponse(
                id=item.id,
                weight_kg=round(item.weight_kg, 1),
                recorded_on_local_date=item.recorded_on_local_date,
                timezone=item.timezone,
                created_at=item.created_at,
            )
            for item in entries
        ],
        latest_weight_kg=round(latest_weight, 1) if latest_weight is not None else None,
        initial_weight_kg=round(initial_weight, 1) if initial_weight is not None else None,
        target_weight_kg=round(float(onboarding.target_weight_kg), 1) if onboarding and onboarding.target_weight_kg is not None else None,
        bmi=bmi,
        bmi_label=bmi_label(bmi, language=current_settings.language),
        can_add_now=can_add_now,
        next_allowed_at=next_allowed_at,
        latest_entry_created_at=latest_entry_created_at,
        hours_until_next_entry=hours_until_next_entry,
        latest_days_ago=latest_days_ago,
        previous_weight_kg=round(previous_weight, 1) if previous_weight is not None else None,
        last_seven_days_delta_kg=_weight_delta_for_days(entries, today_local, 7),
        last_thirty_days_delta_kg=_weight_delta_for_days(entries, today_local, 30),
    )


@router.get("/api/profile", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileResponse:
    return _build_profile_response(db, current_user)


@router.put("/api/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfileResponse:
    try:
        upsert_profile(
            db=db,
            user_id=current_user.id,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            age=payload.age,
            level=payload.level,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить профиль. Попробуйте позже.",
        ) from exc

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Профиль сохранён",
        message="Параметры профиля успешно обновлены.",
    )

    return _build_profile_response(db, current_user)


@router.get("/api/profile/settings", response_model=UserSettingsResponse)
def get_profile_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    return _build_settings_response(db, current_user)


@router.patch("/api/profile/settings", response_model=UserSettingsResponse)
def patch_profile_settings(
    payload: UserSettingsPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    if payload.theme_preference is not None:
        current_settings.theme_preference = payload.theme_preference
    if payload.language is not None:
        current_settings.language = payload.language
    if payload.weight_unit is not None:
        current_settings.weight_unit = payload.weight_unit
    if payload.height_unit is not None:
        current_settings.height_unit = payload.height_unit
    if payload.timezone is not None:
        current_settings.timezone = resolve_timezone_name(payload.timezone)
    try:
        db.add(current_settings)
        db.commit()
        db.refresh(current_settings)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить настройки.",
        ) from exc

    return _build_settings_response(db, current_user)


@router.get("/api/profile/weight-history", response_model=WeightHistorySummaryResponse)
def get_weight_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightHistorySummaryResponse:
    return _weight_history_response(db, current_user)


@router.post("/api/profile/weight-history", response_model=WeightHistorySummaryResponse, status_code=status.HTTP_201_CREATED)
def create_weight_history_entry(
    payload: WeightEntryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightHistorySummaryResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    current_timezone = resolve_timezone_name(current_settings.timezone)
    tz = ZoneInfo(current_timezone)
    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    latest_entry = get_latest_weight_entry(db, current_user.id)
    latest_entry_created_at = _normalize_entry_datetime(latest_entry.created_at if latest_entry else None)
    if latest_entry_created_at is not None and now_utc < latest_entry_created_at + timedelta(hours=5):
        next_allowed_at = latest_entry_created_at + timedelta(hours=5)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Вес можно обновлять не чаще чем раз в 5 часов. Следующее обновление доступно после {next_allowed_at.astimezone(tz).strftime('%H:%M')}.",
        )

    profile = get_or_create_profile(db, current_user.id)
    try:
        entry = WeightEntry(
            user_id=current_user.id,
            weight_kg=float(payload.weight_kg),
            recorded_on_local_date=today_local,
            timezone=current_timezone,
        )
        db.add(entry)
        profile.weight_kg = int(round(float(payload.weight_kg)))
        db.add(profile)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить вес.",
        ) from exc

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Вес обновлён",
        message=f"Новая запись веса: {float(payload.weight_kg):.1f} кг.",
    )
    return _weight_history_response(db, current_user)


@router.patch("/api/profile/account", response_model=AccountResponse)
def update_account(
    payload: AccountUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    try:
        user = update_user_name(db, current_user, payload.name)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить данные аккаунта. Попробуйте позже.",
        ) from exc

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Аккаунт обновлён",
        message="Имя профиля успешно обновлено.",
    )

    return _build_account_response(user)


@router.post("/api/profile/avatar", response_model=AccountResponse)
def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    content_type = (avatar.content_type or "").lower().strip()
    if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только изображения JPEG, PNG и WEBP.",
        )

    file_suffix = Path(avatar.filename or "").suffix.lower()
    if file_suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        file_suffix = ALLOWED_AVATAR_CONTENT_TYPES[content_type]
    if file_suffix == ".jpeg":
        file_suffix = ".jpg"

    avatar_bytes = avatar.file.read(MAX_AVATAR_SIZE_BYTES + 1)
    avatar.file.close()

    if not avatar_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл изображения пустой.",
        )

    if len(avatar_bytes) > MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Размер аватара не должен превышать 3 МБ.",
        )

    avatars_dir = _avatars_dir()
    avatars_dir.mkdir(parents=True, exist_ok=True)

    filename = f"user_{current_user.id}_{uuid4().hex}{file_suffix}"
    stored_file_path = avatars_dir / filename
    stored_file_path.write_bytes(avatar_bytes)

    old_avatar_path = _avatar_path_from_url(current_user.avatar_url)

    try:
        user = update_user_avatar(db, current_user, f"/static/media/avatars/{filename}")
    except SQLAlchemyError as exc:
        db.rollback()
        _remove_avatar_file(stored_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить аватар. Попробуйте позже.",
        ) from exc

    if old_avatar_path and old_avatar_path != stored_file_path:
        _remove_avatar_file(old_avatar_path)

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Аватар обновлён",
        message="Новая фотография профиля успешно сохранена.",
    )

    return _build_account_response(user)


@router.delete("/api/profile/avatar", response_model=AccountResponse)
def remove_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    if current_user.avatar_url is None:
        return _build_account_response(current_user)

    old_avatar_path = _avatar_path_from_url(current_user.avatar_url)

    try:
        user = update_user_avatar(db, current_user, None)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить аватар. Попробуйте позже.",
        ) from exc

    _remove_avatar_file(old_avatar_path)

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Аватар удалён",
        message="Фото профиля удалено.",
    )

    return _build_account_response(user)


@router.post("/api/profile/goal", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_profile_goal(
    payload: GoalCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalResponse:
    try:
        goal = create_goal(
            db=db,
            user_id=current_user.id,
            goal_type=payload.goal_type,
            target_value=payload.target_value,
        )
    except GoalAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У вас уже есть цель. Сначала удалите текущую цель.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать цель. Попробуйте позже.",
        ) from exc

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Цель создана",
        message="Текущая цель в профиле успешно добавлена.",
    )

    return GoalResponse.model_validate(goal)


@router.delete("/api/profile/goal", response_model=DeleteGoalResponse)
def delete_profile_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteGoalResponse:
    try:
        deleted = delete_goal_by_user_id(db, current_user.id)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось удалить цель. Попробуйте позже.",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Текущая цель не найдена.",
        )

    create_notification_safe(
        db,
        user_id=current_user.id,
        title="Цель удалена",
        message="Текущая цель удалена из профиля.",
    )

    return DeleteGoalResponse(ok=True)
