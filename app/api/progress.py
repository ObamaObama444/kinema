from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.core.progress import build_progress_summary, resolve_timezone_name
from app.crud.settings import get_or_create_user_settings
from app.models.workout import WorkoutSession
from app.models.workout_checkin import WorkoutCheckin
from app.models.user import User
from app.schemas.progress import ProgressCheckinRequest, ProgressSummaryResponse

router = APIRouter(tags=["progress"])
_COMPLETED_SESSION_STATUSES = {"finished", "stopped"}


@router.get("/api/progress/summary", response_model=ProgressSummaryResponse)
def get_progress_summary(
    month: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressSummaryResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    try:
        payload = build_progress_summary(
            db,
            current_user,
            settings_language=current_settings.language,
            settings_timezone=current_settings.timezone,
            month_key=month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProgressSummaryResponse(**payload)


@router.post("/api/progress/checkins", response_model=ProgressSummaryResponse)
def toggle_progress_checkin(
    payload: ProgressCheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressSummaryResponse:
    current_settings = get_or_create_user_settings(db, current_user.id)
    timezone_name = resolve_timezone_name(current_settings.timezone)
    tz = ZoneInfo(timezone_name)
    today_local = datetime.now(timezone.utc).astimezone(tz).date()
    if payload.date > today_local:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отмечать тренировки в будущем.",
        )

    sessions = db.query(WorkoutSession).filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.status.in_(_COMPLETED_SESSION_STATUSES),
    ).all()
    has_session_completion = False
    for session in sessions:
        source_dt = session.ended_at or session.started_at
        if source_dt is None:
            continue
        local_date = source_dt.astimezone(tz).date() if source_dt.tzinfo else source_dt.replace(tzinfo=timezone.utc).astimezone(tz).date()
        if local_date == payload.date:
            has_session_completion = True
            break

    existing_checkin = db.query(WorkoutCheckin).filter(
        WorkoutCheckin.user_id == current_user.id,
        WorkoutCheckin.local_date == payload.date,
    ).one_or_none()

    if payload.completed:
        if not has_session_completion and existing_checkin is None:
            db.add(
                WorkoutCheckin(
                    user_id=current_user.id,
                    local_date=payload.date,
                    timezone=timezone_name,
                )
            )
            db.commit()
    else:
        if has_session_completion:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="День с реальной тренировкой нельзя снять вручную.",
            )
        if existing_checkin is not None:
            db.delete(existing_checkin)
            db.commit()

    result = build_progress_summary(
        db,
        current_user,
        settings_language=current_settings.language,
        settings_timezone=current_settings.timezone,
        month_key=payload.date.strftime("%Y-%m"),
    )
    return ProgressSummaryResponse(**result)
