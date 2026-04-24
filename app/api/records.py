from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.deps import get_db
from app.core.progress import resolve_timezone_name
from app.crud.records import get_daily_record_goal, list_vital_measurements_for_day
from app.crud.settings import get_or_create_user_settings
from app.models.daily_record_goal import DailyRecordGoal
from app.models.user import User
from app.models.vital_measurement import VitalMeasurement
from app.schemas.records import (
    BloodPressureMeasurementCreateRequest,
    BloodPressurePointResponse,
    PulseMeasurementCreateRequest,
    PulsePointResponse,
    RecordsSummaryResponse,
    StepsGoalUpdateRequest,
    WaterIntakeUpdateRequest,
    WaterGoalUpdateRequest,
)

router = APIRouter(tags=["records"])

_PULSE_METRIC = "pulse"
_BLOOD_PRESSURE_METRIC = "blood_pressure"


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _resolve_today_context(db: Session, current_user: User) -> tuple[str, ZoneInfo, datetime, date]:
    current_settings = get_or_create_user_settings(db, current_user.id)
    timezone_name = resolve_timezone_name(current_settings.timezone)
    tz = ZoneInfo(timezone_name)
    now_utc = datetime.now(timezone.utc)
    today_local = now_utc.astimezone(tz).date()
    return timezone_name, tz, now_utc, today_local


def _build_records_summary(
    db: Session,
    current_user: User,
    tz: ZoneInfo,
    today_local: date,
) -> RecordsSummaryResponse:
    goals = get_daily_record_goal(db, current_user.id, today_local)
    pulse_entries = list_vital_measurements_for_day(db, current_user.id, today_local, _PULSE_METRIC)
    blood_pressure_entries = list_vital_measurements_for_day(db, current_user.id, today_local, _BLOOD_PRESSURE_METRIC)
    latest_pulse = pulse_entries[-1] if pulse_entries else None
    latest_blood_pressure = blood_pressure_entries[-1] if blood_pressure_entries else None

    def pulse_point(entry: VitalMeasurement) -> PulsePointResponse:
        recorded_at = _normalize_datetime(entry.recorded_at).astimezone(tz)
        return PulsePointResponse(
            id=entry.id,
            bpm=int(entry.pulse_bpm or 0),
            hour=recorded_at.hour,
            minute=recorded_at.minute,
            recorded_at=recorded_at,
        )

    def blood_pressure_point(entry: VitalMeasurement) -> BloodPressurePointResponse:
        recorded_at = _normalize_datetime(entry.recorded_at).astimezone(tz)
        return BloodPressurePointResponse(
            id=entry.id,
            systolic=int(entry.systolic_mmhg or 0),
            diastolic=int(entry.diastolic_mmhg or 0),
            hour=recorded_at.hour,
            minute=recorded_at.minute,
            recorded_at=recorded_at,
        )

    latest_pulse_bpm = int(latest_pulse.pulse_bpm) if latest_pulse and latest_pulse.pulse_bpm is not None else None
    pulse_points = [pulse_point(entry) for entry in pulse_entries[-12:]]

    return RecordsSummaryResponse(
        local_date=today_local,
        steps_goal=int(goals.steps_goal or 0) if goals else 0,
        water_goal_glasses=int(goals.water_goal_glasses or 0) if goals else 0,
        water_consumed_glasses=int(goals.water_consumed_glasses or 0) if goals else 0,
        latest_pulse_bpm=latest_pulse_bpm,
        latest_systolic=int(latest_blood_pressure.systolic_mmhg)
        if latest_blood_pressure and latest_blood_pressure.systolic_mmhg is not None
        else None,
        latest_diastolic=int(latest_blood_pressure.diastolic_mmhg)
        if latest_blood_pressure and latest_blood_pressure.diastolic_mmhg is not None
        else None,
        pulse_points=pulse_points,
        blood_pressure_points=[blood_pressure_point(entry) for entry in blood_pressure_entries[-12:]],
    )


def _upsert_daily_goals(
    db: Session,
    *,
    current_user: User,
    timezone_name: str,
    today_local,
    steps_goal: int | None = None,
    water_goal_glasses: int | None = None,
    water_consumed_glasses: int | None = None,
) -> None:
    goals = get_daily_record_goal(db, current_user.id, today_local)
    if goals is None:
        goals = DailyRecordGoal(
            user_id=current_user.id,
            local_date=today_local,
            timezone=timezone_name,
        )

    goals.timezone = timezone_name
    if steps_goal is not None:
        goals.steps_goal = int(steps_goal)
    if water_goal_glasses is not None:
        goals.water_goal_glasses = int(water_goal_glasses)
        if goals.water_goal_glasses <= 0:
            goals.water_consumed_glasses = 0
        elif int(goals.water_consumed_glasses or 0) > goals.water_goal_glasses:
            goals.water_consumed_glasses = goals.water_goal_glasses
    if water_consumed_glasses is not None:
        max_value = max(0, int(goals.water_goal_glasses or 30))
        goals.water_consumed_glasses = min(int(water_consumed_glasses), max_value)

    db.add(goals)


@router.get("/api/records/summary", response_model=RecordsSummaryResponse)
def get_records_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    _, tz, _, today_local = _resolve_today_context(db, current_user)
    return _build_records_summary(db, current_user, tz, today_local)


@router.put("/api/records/steps-goal", response_model=RecordsSummaryResponse)
def update_steps_goal(
    payload: StepsGoalUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    timezone_name, tz, _, today_local = _resolve_today_context(db, current_user)
    try:
        _upsert_daily_goals(
            db,
            current_user=current_user,
            timezone_name=timezone_name,
            today_local=today_local,
            steps_goal=payload.value,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить цель по шагам.",
        ) from exc

    return _build_records_summary(db, current_user, tz, today_local)


@router.put("/api/records/water-goal", response_model=RecordsSummaryResponse)
def update_water_goal(
    payload: WaterGoalUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    timezone_name, tz, _, today_local = _resolve_today_context(db, current_user)
    try:
        _upsert_daily_goals(
            db,
            current_user=current_user,
            timezone_name=timezone_name,
            today_local=today_local,
            water_goal_glasses=payload.value,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить цель по воде.",
        ) from exc

    return _build_records_summary(db, current_user, tz, today_local)


@router.put("/api/records/water-intake", response_model=RecordsSummaryResponse)
def update_water_intake(
    payload: WaterIntakeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    timezone_name, tz, _, today_local = _resolve_today_context(db, current_user)
    try:
        _upsert_daily_goals(
            db,
            current_user=current_user,
            timezone_name=timezone_name,
            today_local=today_local,
            water_consumed_glasses=payload.value,
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить выпитую воду.",
        ) from exc

    return _build_records_summary(db, current_user, tz, today_local)


@router.post("/api/records/pulse", response_model=RecordsSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_pulse_measurement(
    payload: PulseMeasurementCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    timezone_name, tz, now_utc, today_local = _resolve_today_context(db, current_user)
    try:
        db.add(
            VitalMeasurement(
                user_id=current_user.id,
                local_date=today_local,
                metric_type=_PULSE_METRIC,
                pulse_bpm=payload.bpm,
                timezone=timezone_name,
                recorded_at=now_utc,
            )
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить пульс.",
        ) from exc

    return _build_records_summary(db, current_user, tz, today_local)


@router.post("/api/records/blood-pressure", response_model=RecordsSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_blood_pressure_measurement(
    payload: BloodPressureMeasurementCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordsSummaryResponse:
    if payload.diastolic >= payload.systolic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Диастолическое давление должно быть ниже систолического.",
        )

    timezone_name, tz, now_utc, today_local = _resolve_today_context(db, current_user)
    try:
        db.add(
            VitalMeasurement(
                user_id=current_user.id,
                local_date=today_local,
                metric_type=_BLOOD_PRESSURE_METRIC,
                systolic_mmhg=payload.systolic,
                diastolic_mmhg=payload.diastolic,
                timezone=timezone_name,
                recorded_at=now_utc,
            )
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось сохранить давление.",
        ) from exc

    return _build_records_summary(db, current_user, tz, today_local)
