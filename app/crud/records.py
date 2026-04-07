from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_record_goal import DailyRecordGoal
from app.models.vital_measurement import VitalMeasurement


def get_daily_record_goal(db: Session, user_id: int, local_date: date) -> DailyRecordGoal | None:
    stmt = select(DailyRecordGoal).where(
        DailyRecordGoal.user_id == user_id,
        DailyRecordGoal.local_date == local_date,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_vital_measurements_for_day(
    db: Session,
    user_id: int,
    local_date: date,
    metric_type: str,
) -> list[VitalMeasurement]:
    stmt = (
        select(VitalMeasurement)
        .where(
            VitalMeasurement.user_id == user_id,
            VitalMeasurement.local_date == local_date,
            VitalMeasurement.metric_type == metric_type,
        )
        .order_by(VitalMeasurement.recorded_at.asc(), VitalMeasurement.id.asc())
    )
    return list(db.execute(stmt).scalars().all())
