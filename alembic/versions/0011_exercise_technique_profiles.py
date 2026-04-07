"""add generated exercise technique profiles

Revision ID: 0011_exercise_technique_profiles
Revises: 0010_technique_sessions
Create Date: 2026-03-14 01:30:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011_exercise_technique_profiles"
down_revision: str | None = "0010_technique_sessions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if not _table_exists("exercise_technique_profiles"):
        op.create_table(
            "exercise_technique_profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("owner_user_id", sa.Integer(), nullable=False),
            sa.Column("public_slug", sa.String(length=160), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("motion_family", sa.String(length=32), nullable=False),
            sa.Column("view_type", sa.String(length=32), nullable=False),
            sa.Column("source_video_name", sa.String(length=255), nullable=True),
            sa.Column("source_video_path", sa.Text(), nullable=True),
            sa.Column("source_video_meta_json", sa.Text(), nullable=True),
            sa.Column("reference_model_json", sa.Text(), nullable=False),
            sa.Column("calibration_profile_json", sa.Text(), nullable=False),
            sa.Column("latest_test_summary_json", sa.Text(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("exercise_id"),
            sa.UniqueConstraint("public_slug"),
        )

    if _table_exists("exercise_technique_profiles") and not _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_exercise_id"):
        op.create_index("ix_exercise_technique_profiles_exercise_id", "exercise_technique_profiles", ["exercise_id"], unique=False)
    if _table_exists("exercise_technique_profiles") and not _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_owner_user_id"):
        op.create_index("ix_exercise_technique_profiles_owner_user_id", "exercise_technique_profiles", ["owner_user_id"], unique=False)
    if _table_exists("exercise_technique_profiles") and not _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_public_slug"):
        op.create_index("ix_exercise_technique_profiles_public_slug", "exercise_technique_profiles", ["public_slug"], unique=True)


def downgrade() -> None:
    if _table_exists("exercise_technique_profiles") and _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_public_slug"):
        op.drop_index("ix_exercise_technique_profiles_public_slug", table_name="exercise_technique_profiles")
    if _table_exists("exercise_technique_profiles") and _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_owner_user_id"):
        op.drop_index("ix_exercise_technique_profiles_owner_user_id", table_name="exercise_technique_profiles")
    if _table_exists("exercise_technique_profiles") and _index_exists("exercise_technique_profiles", "ix_exercise_technique_profiles_exercise_id"):
        op.drop_index("ix_exercise_technique_profiles_exercise_id", table_name="exercise_technique_profiles")
    if _table_exists("exercise_technique_profiles"):
        op.drop_table("exercise_technique_profiles")
