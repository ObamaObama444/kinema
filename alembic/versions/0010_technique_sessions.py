"""add technique sessions table

Revision ID: 0010_technique_sessions
Revises: 0009_profile_hub_checkins_and_weight_cooldown
Create Date: 2026-03-13 10:45:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_technique_sessions"
down_revision: str | None = "0009_profile_hub_checkins_and_weight_cooldown"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if not _table_exists("technique_sessions"):
        op.create_table(
            "technique_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reps_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("avg_score", sa.Float(), nullable=True),
            sa.Column("log_path", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists("technique_sessions") and not _index_exists("technique_sessions", "ix_technique_sessions_user_id"):
        op.create_index("ix_technique_sessions_user_id", "technique_sessions", ["user_id"], unique=False)
    if _table_exists("technique_sessions") and not _index_exists("technique_sessions", "ix_technique_sessions_exercise_id"):
        op.create_index("ix_technique_sessions_exercise_id", "technique_sessions", ["exercise_id"], unique=False)


def downgrade() -> None:
    if _table_exists("technique_sessions") and _index_exists("technique_sessions", "ix_technique_sessions_exercise_id"):
        op.drop_index("ix_technique_sessions_exercise_id", table_name="technique_sessions")
    if _table_exists("technique_sessions") and _index_exists("technique_sessions", "ix_technique_sessions_user_id"):
        op.drop_index("ix_technique_sessions_user_id", table_name="technique_sessions")
    if _table_exists("technique_sessions"):
        op.drop_table("technique_sessions")
