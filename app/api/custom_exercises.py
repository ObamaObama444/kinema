from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.models.exercise import Exercise
from app.models.exercise_technique_profile import ExerciseTechniqueProfile
from app.models.user import User
from app.schemas.exercise import ExerciseCatalogItemResponse
from app.schemas.exercise_technique import (
    CalibrationProfileUpdateRequest,
    ExerciseTechniqueProfileResponse,
    ExerciseTechniquePublishResponse,
    GeneratedExerciseCompareRequest,
    GeneratedExerciseCompareResponse,
    GeneratedTechniqueFrameMetric,
)
from app.services.generated_technique import (
    build_catalog_tags,
    build_reference_model,
    compare_generated_rep,
    dump_json,
    load_json,
    motion_family_label,
    sanitize_calibration_profile,
    slugify_title,
    view_type_label,
)

router = APIRouter(tags=["custom_exercises"])

CUSTOM_EXERCISE_DIR = Path("data/custom_exercises")
MAX_REFERENCE_VIDEO_BYTES = 60 * 1024 * 1024
ALLOWED_VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".m4v"}
ALLOWED_VIDEO_CONTENT_TYPES = {
    "application/octet-stream",
    "binary/octet-stream",
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-m4v",
}
MIN_PUBLISH_SCORE = 75


def _ensure_profile_storage() -> Path:
    CUSTOM_EXERCISE_DIR.mkdir(parents=True, exist_ok=True)
    return CUSTOM_EXERCISE_DIR


def _parse_reference_frames(raw_payload: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw_payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось прочитать reference metrics.",
        ) from exc

    if not isinstance(parsed, list) or len(parsed) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для построения эталона нужно минимум 10 кадров с метриками.",
        )

    try:
        return [
            GeneratedTechniqueFrameMetric.model_validate(item).model_dump()
            for item in parsed
        ]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference metrics не прошли валидацию.",
        ) from exc


def _declared_video_size(video_meta: Any) -> int:
    if not isinstance(video_meta, dict):
        return 0
    try:
        return max(0, int(video_meta.get("size_bytes") or 0))
    except (TypeError, ValueError):
        return 0


def _validate_reference_video_upload(video_file: UploadFile, video_meta: Any) -> str:
    suffix = Path(str(video_file.filename or "reference.mp4")).suffix.lower() or ".mp4"
    if suffix not in ALLOWED_VIDEO_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только видео в форматах MP4, MOV или WEBM.",
        )

    content_type = str(video_file.content_type or "").strip().lower()
    if content_type and content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Загрузите корректный видеофайл с одним эталонным повтором.",
        )

    declared_size = _declared_video_size(video_meta)
    if declared_size > MAX_REFERENCE_VIDEO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Эталонное видео слишком большое. Допустимый размер до 60 МБ.",
        )

    return suffix


def _store_reference_video(video_file: UploadFile, target_path: Path) -> int:
    total_bytes = 0
    chunk_size = 1024 * 1024

    try:
        video_file.file.seek(0)
    except (AttributeError, OSError):
        pass

    try:
        with target_path.open("wb") as output:
            while True:
                chunk = video_file.file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_REFERENCE_VIDEO_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Эталонное видео слишком большое. Допустимый размер до 60 МБ.",
                    )
                output.write(chunk)
    except HTTPException:
        if target_path.exists():
            target_path.unlink()
        raise
    except OSError as exc:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить эталонное видео.",
        ) from exc

    if total_bytes <= 0:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл эталонного видео пустой.",
        )

    return total_bytes


def _cleanup_profile_storage(upload_dir: Path | None, stored_path: Path | None) -> None:
    if stored_path is not None and stored_path.exists():
        stored_path.unlink()
    if upload_dir is not None and upload_dir.exists():
        try:
            next(upload_dir.iterdir())
        except StopIteration:
            upload_dir.rmdir()


def _ensure_publish_ready(latest_test_summary_json: str | None) -> None:
    summary = load_json(latest_test_summary_json, {})
    if not isinstance(summary, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Последний тест эталона повреждён. Выполните тест с камеры заново.",
        )

    rep_score = int(summary.get("rep_score") or 0)
    if rep_score < MIN_PUBLISH_SCORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Для публикации нужен тест со score не ниже {MIN_PUBLISH_SCORE}.",
        )

    details = summary.get("details") if isinstance(summary.get("details"), dict) else {}
    caps_applied = details.get("caps_applied") if isinstance(details.get("caps_applied"), list) else []
    if any(str(item or "").strip() for item in caps_applied):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Последний тест всё ещё содержит критические отклонения. Уберите caps и повторите проверку.",
        )


def _profile_by_id(db: Session, profile_id: int) -> ExerciseTechniqueProfile | None:
    return db.execute(
        select(ExerciseTechniqueProfile).where(ExerciseTechniqueProfile.id == profile_id)
    ).scalar_one_or_none()


def _published_profile_by_exercise_id(db: Session, exercise_id: int) -> ExerciseTechniqueProfile | None:
    return db.execute(
        select(ExerciseTechniqueProfile).where(
            ExerciseTechniqueProfile.exercise_id == exercise_id,
            ExerciseTechniqueProfile.status == "published",
        )
    ).scalar_one_or_none()


def _can_access_profile(profile: ExerciseTechniqueProfile, current_user: User) -> bool:
    return profile.status == "published" or profile.owner_user_id == current_user.id


def _can_edit_profile(profile: ExerciseTechniqueProfile, current_user: User) -> bool:
    if profile.is_system:
        return False
    return profile.owner_user_id == current_user.id


def _serialize_profile(
    profile: ExerciseTechniqueProfile,
    *,
    current_user: User,
) -> ExerciseTechniqueProfileResponse:
    return ExerciseTechniqueProfileResponse(
        id=profile.id,
        exercise_id=profile.exercise.id,
        slug=profile.public_slug,
        title=profile.exercise.name,
        description=profile.exercise.description,
        status=profile.status,
        is_system=bool(profile.is_system),
        motion_family=profile.motion_family,
        motion_family_label=motion_family_label(profile.motion_family),
        view_type=profile.view_type,
        view_type_label=view_type_label(profile.view_type),
        source_video_name=profile.source_video_name,
        source_video_meta=load_json(profile.source_video_meta_json, {}),
        reference_model=load_json(profile.reference_model_json, {}),
        calibration_profile=load_json(profile.calibration_profile_json, {}),
        latest_test_summary=load_json(profile.latest_test_summary_json, None),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        published_at=profile.published_at,
        can_edit=_can_edit_profile(profile, current_user),
        launch_url=f"/app/catalog/custom/{profile.id}",
    )


def published_catalog_items(
    db: Session,
    *,
    current_user: User,
    favorite_ids: set[int],
) -> list[ExerciseCatalogItemResponse]:
    profiles = db.execute(
        select(ExerciseTechniqueProfile)
        .where(
            ExerciseTechniqueProfile.status == "published",
            ExerciseTechniqueProfile.is_system.is_(False),
        )
        .order_by(ExerciseTechniqueProfile.published_at.desc(), ExerciseTechniqueProfile.id.desc())
    ).scalars().all()

    items: list[ExerciseCatalogItemResponse] = []
    for profile in profiles:
        items.append(
            ExerciseCatalogItemResponse(
                id=profile.exercise.id,
                slug=profile.public_slug,
                title=profile.exercise.name,
                description=profile.exercise.description,
                tags=build_catalog_tags(profile),
                technique_available=True,
                is_favorite=profile.exercise.id in favorite_ids,
                technique_launch_url=f"/app/catalog/custom/{profile.id}",
            )
        )
    return items


def favorite_payload_for_exercise(
    db: Session,
    *,
    exercise: Exercise,
) -> dict[str, Any] | None:
    profile = _published_profile_by_exercise_id(db, exercise.id)
    if profile is None:
        return None
    return {
        "slug": profile.public_slug,
        "title": exercise.name,
        "description": exercise.description,
        "tags": build_catalog_tags(profile),
        "technique_available": True,
    }


@router.post("/api/exercises/custom/drafts", response_model=ExerciseTechniqueProfileResponse)
def create_custom_exercise_draft(
    title: str = Form(...),
    description: str = Form(""),
    motion_family: str = Form(...),
    view_type: str = Form(...),
    reference_metrics_json: str = Form(...),
    video_meta_json: str = Form("{}"),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseTechniqueProfileResponse:
    cleaned_title = str(title or "").strip()
    cleaned_description = str(description or "").strip() or cleaned_title
    upload_dir: Path | None = None
    stored_path: Path | None = None
    if not cleaned_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название упражнения обязательно.",
        )

    reference_frames = _parse_reference_frames(reference_metrics_json)
    video_meta = load_json(video_meta_json, {})
    suffix = _validate_reference_video_upload(video_file, video_meta)
    try:
        reference_model, calibration_profile = build_reference_model(
            frame_metrics=reference_frames,
            motion_family=str(motion_family or "").strip().lower(),
            view_type=str(view_type or "").strip().lower(),
            video_meta=video_meta if isinstance(video_meta, dict) else {},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        exercise = Exercise(
            name=cleaned_title,
            description=cleaned_description,
            equipment="Пользовательское упражнение",
            primary_muscles=motion_family_label(motion_family),
            difficulty="custom",
        )
        db.add(exercise)
        db.flush()

        upload_dir = _ensure_profile_storage() / f"exercise_{exercise.id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = upload_dir / f"reference{suffix}"
        stored_size = _store_reference_video(video_file, stored_path)

        now = datetime.now(timezone.utc)
        actual_video_meta = dict(video_meta) if isinstance(video_meta, dict) else {}
        actual_video_meta["size_bytes"] = stored_size
        profile = ExerciseTechniqueProfile(
            exercise_id=exercise.id,
            owner_user_id=current_user.id,
            is_system=False,
            public_slug=f"custom-technique-{slugify_title(cleaned_title)}-{exercise.id}",
            status="draft",
            motion_family=str(motion_family or "").strip().lower(),
            view_type=str(view_type or "").strip().lower(),
            source_video_name=str(video_file.filename or "reference.mp4"),
            source_video_path=str(stored_path),
            source_video_meta_json=dump_json(actual_video_meta),
            reference_model_json=dump_json(reference_model),
            calibration_profile_json=dump_json(calibration_profile),
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.commit()
    except HTTPException:
        db.rollback()
        _cleanup_profile_storage(upload_dir, stored_path)
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        _cleanup_profile_storage(upload_dir, stored_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить черновик упражнения.",
        ) from exc

    db.refresh(profile)

    return _serialize_profile(profile, current_user=current_user)


@router.get("/api/exercises/custom/{profile_id}", response_model=ExerciseTechniqueProfileResponse)
def get_custom_exercise_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseTechniqueProfileResponse:
    profile = _profile_by_id(db, profile_id)
    if profile is None or not _can_access_profile(profile, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль упражнения не найден.",
        )
    return _serialize_profile(profile, current_user=current_user)


@router.post("/api/exercises/custom/{profile_id}/calibration", response_model=ExerciseTechniqueProfileResponse)
def update_custom_exercise_calibration(
    profile_id: int,
    payload: CalibrationProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseTechniqueProfileResponse:
    profile = _profile_by_id(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль упражнения не найден.")
    if not _can_edit_profile(profile, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для редактирования.")

    reference_model = load_json(profile.reference_model_json, {})
    calibration_profile = sanitize_calibration_profile(
        payload.calibration_profile,
        motion_family=profile.motion_family,
        reference_model=reference_model,
    )
    profile.calibration_profile_json = dump_json(calibration_profile)
    profile.updated_at = datetime.now(timezone.utc)
    if profile.status == "draft":
        profile.status = "testing"
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile, current_user=current_user)


@router.post("/api/exercises/custom/{profile_id}/compare", response_model=GeneratedExerciseCompareResponse)
def compare_custom_exercise_rep(
    profile_id: int,
    payload: GeneratedExerciseCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GeneratedExerciseCompareResponse:
    profile = _profile_by_id(db, profile_id)
    if profile is None or not _can_access_profile(profile, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль упражнения не найден.")

    try:
        result = compare_generated_rep(
            frame_metrics=[item.model_dump() for item in payload.frame_metrics],
            reference_model=load_json(profile.reference_model_json, {}),
            calibration_profile=load_json(profile.calibration_profile_json, {}),
            duration_ms=payload.duration_ms,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if _can_edit_profile(profile, current_user):
        profile.latest_test_summary_json = dump_json(result)
        profile.updated_at = datetime.now(timezone.utc)
        if profile.status == "draft":
            profile.status = "testing"
        db.add(profile)
        db.commit()

    return GeneratedExerciseCompareResponse(**result)


@router.post("/api/exercises/custom/{profile_id}/publish", response_model=ExerciseTechniquePublishResponse)
def publish_custom_exercise(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExerciseTechniquePublishResponse:
    profile = _profile_by_id(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль упражнения не найден.")
    if not _can_edit_profile(profile, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для публикации.")
    if not profile.latest_test_summary_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Перед публикацией выполните хотя бы один тест эталона через камеру.",
        )
    _ensure_publish_ready(profile.latest_test_summary_json)

    now = datetime.now(timezone.utc)
    profile.status = "published"
    profile.published_at = now
    profile.updated_at = now
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return ExerciseTechniquePublishResponse(
        ok=True,
        profile=_serialize_profile(profile, current_user=current_user),
    )
