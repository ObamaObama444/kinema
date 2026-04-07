from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.program import Program
from app.models.workout import WorkoutSession

_COMPLETED_SESSION_STATUSES = {"finished", "stopped"}


def get_profile_by_user_id(db: Session, user_id: int) -> Profile | None:
    stmt = select(Profile).where(Profile.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_or_create_profile(db: Session, user_id: int) -> Profile:
    profile = get_profile_by_user_id(db, user_id)
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def upsert_profile(
    db: Session,
    user_id: int,
    height_cm: int | None,
    weight_kg: int | None,
    age: int | None,
    level: str | None,
) -> Profile:
    profile = get_or_create_profile(db, user_id)

    profile.height_cm = height_cm
    profile.weight_kg = weight_kg
    profile.age = age
    profile.level = level

    db.commit()
    db.refresh(profile)
    return profile


def set_active_program(
    db: Session,
    user_id: int,
    program_id: int,
    workouts_per_week: int,
) -> Profile:
    if workouts_per_week < 1 or workouts_per_week > 3:
        raise ValueError("Частота тренировок должна быть от 1 до 3 раз в неделю.")

    profile = get_or_create_profile(db, user_id)
    profile.active_program_id = program_id
    profile.workouts_per_week = workouts_per_week

    db.commit()
    db.refresh(profile)
    return profile


def get_active_program_snapshot(
    db: Session,
    user_id: int,
    profile: Profile | None,
) -> dict[str, int | str] | None:
    if profile is None or profile.active_program_id is None:
        return None

    program = db.execute(
        select(Program).where(Program.id == profile.active_program_id)
    ).scalar_one_or_none()
    if program is None:
        return None
    if program.owner_user_id is not None and program.owner_user_id != user_id:
        return None

    workouts_per_week = profile.workouts_per_week or 1
    total_sessions = max(program.duration_weeks * workouts_per_week, 1)

    completed_sessions = int(
        db.execute(
            select(func.count(WorkoutSession.id)).where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.program_id == program.id,
                WorkoutSession.status.in_(_COMPLETED_SESSION_STATUSES),
            )
        ).scalar_one()
    )

    progress_percent = min(100, int((completed_sessions * 100) / total_sessions))

    return {
        "program_id": program.id,
        "title": program.title,
        "duration_weeks": program.duration_weeks,
        "workouts_per_week": workouts_per_week,
        "completed_sessions": completed_sessions,
        "total_sessions": total_sessions,
        "progress_percent": progress_percent,
    }
