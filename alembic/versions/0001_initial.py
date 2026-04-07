"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-07 12:30:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("users") and not _index_exists("users", "ix_users_email"):
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _table_exists("programs"):
        op.create_table(
            "programs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("level", sa.String(length=32), nullable=False),
            sa.Column("duration_weeks", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("exercises"):
        op.create_table(
            "exercises",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("equipment", sa.String(length=180), nullable=True),
            sa.Column("primary_muscles", sa.String(length=180), nullable=True),
            sa.Column("difficulty", sa.String(length=32), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _table_exists("profiles"):
        op.create_table(
            "profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("height_cm", sa.Integer(), nullable=True),
            sa.Column("weight_kg", sa.Integer(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("level", sa.String(length=32), nullable=True),
            sa.Column("limitations", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("profiles") and not _index_exists("profiles", "ix_profiles_user_id"):
        op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)

    if not _table_exists("goals"):
        op.create_table(
            "goals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("goal_type", sa.String(length=64), nullable=False),
            sa.Column("target_value", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("goals") and not _index_exists("goals", "ix_goals_user_id"):
        op.create_index("ix_goals_user_id", "goals", ["user_id"], unique=False)

    if not _table_exists("program_exercises"):
        op.create_table(
            "program_exercises",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("program_id", sa.Integer(), nullable=False),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("sets", sa.Integer(), nullable=False),
            sa.Column("reps", sa.Integer(), nullable=False),
            sa.Column("rest_sec", sa.Integer(), nullable=False),
            sa.Column("tempo", sa.String(length=40), nullable=False),
            sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("program_exercises") and not _index_exists("program_exercises", "ix_program_exercises_program_id"):
        op.create_index("ix_program_exercises_program_id", "program_exercises", ["program_id"], unique=False)
    if _table_exists("program_exercises") and not _index_exists("program_exercises", "ix_program_exercises_exercise_id"):
        op.create_index("ix_program_exercises_exercise_id", "program_exercises", ["exercise_id"], unique=False)

    if not _table_exists("workout_sessions"):
        op.create_table(
            "workout_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("program_id", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("workout_sessions") and not _index_exists("workout_sessions", "ix_workout_sessions_user_id"):
        op.create_index("ix_workout_sessions_user_id", "workout_sessions", ["user_id"], unique=False)
    if _table_exists("workout_sessions") and not _index_exists("workout_sessions", "ix_workout_sessions_program_id"):
        op.create_index("ix_workout_sessions_program_id", "workout_sessions", ["program_id"], unique=False)

    if not _table_exists("workout_set_logs"):
        op.create_table(
            "workout_set_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("set_number", sa.Integer(), nullable=False),
            sa.Column("reps_planned", sa.Integer(), nullable=False),
            sa.Column("reps_done", sa.Integer(), nullable=True),
            sa.Column("form_score_mock", sa.Integer(), nullable=True),  # MOCK
            sa.Column("notes_mock", sa.Text(), nullable=True),  # MOCK
            sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("workout_set_logs") and not _index_exists("workout_set_logs", "ix_workout_set_logs_session_id"):
        op.create_index("ix_workout_set_logs_session_id", "workout_set_logs", ["session_id"], unique=False)
    if _table_exists("workout_set_logs") and not _index_exists("workout_set_logs", "ix_workout_set_logs_exercise_id"):
        op.create_index("ix_workout_set_logs_exercise_id", "workout_set_logs", ["exercise_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workout_set_logs_exercise_id", table_name="workout_set_logs")
    op.drop_index("ix_workout_set_logs_session_id", table_name="workout_set_logs")
    op.drop_table("workout_set_logs")

    op.drop_index("ix_workout_sessions_program_id", table_name="workout_sessions")
    op.drop_index("ix_workout_sessions_user_id", table_name="workout_sessions")
    op.drop_table("workout_sessions")

    op.drop_index("ix_program_exercises_exercise_id", table_name="program_exercises")
    op.drop_index("ix_program_exercises_program_id", table_name="program_exercises")
    op.drop_table("program_exercises")

    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")

    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")

    op.drop_table("exercises")
    op.drop_table("programs")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
