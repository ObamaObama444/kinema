"""add user onboarding table

Revision ID: 0007_user_onboarding
Revises: 0006_notification_actions
Create Date: 2026-03-09 03:10:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_user_onboarding"
down_revision: str | None = "0006_notification_actions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if not _table_exists("user_onboarding"):
        op.create_table(
            "user_onboarding",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("is_completed", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("main_goal", sa.String(length=64), nullable=True),
            sa.Column("motivation", sa.String(length=64), nullable=True),
            sa.Column("desired_outcome", sa.String(length=64), nullable=True),
            sa.Column("focus_area", sa.String(length=64), nullable=True),
            sa.Column("gender", sa.String(length=32), nullable=True),
            sa.Column("current_body_shape", sa.Integer(), nullable=True),
            sa.Column("target_body_shape", sa.Integer(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("height_cm", sa.Integer(), nullable=True),
            sa.Column("current_weight_kg", sa.Float(), nullable=True),
            sa.Column("target_weight_kg", sa.Float(), nullable=True),
            sa.Column("fitness_level", sa.String(length=32), nullable=True),
            sa.Column("activity_level", sa.String(length=32), nullable=True),
            sa.Column("goal_pace", sa.String(length=32), nullable=True),
            sa.Column("training_frequency", sa.Integer(), nullable=True),
            sa.Column("calorie_tracking", sa.String(length=32), nullable=True),
            sa.Column("diet_type", sa.String(length=32), nullable=True),
            sa.Column("self_image", sa.String(length=32), nullable=True),
            sa.Column("reminders_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("reminder_time_local", sa.String(length=5), nullable=True),
            sa.Column("onboarding_version", sa.String(length=32), server_default=sa.text("'v1'"), nullable=False),
            sa.Column("interest_tags", sa.Text(), nullable=True),
            sa.Column("injury_areas", sa.Text(), nullable=True),
            sa.Column("training_days", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if _table_exists("user_onboarding") and not _index_exists("user_onboarding", "ix_user_onboarding_user_id"):
        op.create_index("ix_user_onboarding_user_id", "user_onboarding", ["user_id"], unique=True)


def downgrade() -> None:
    if _table_exists("user_onboarding") and _index_exists("user_onboarding", "ix_user_onboarding_user_id"):
        op.drop_index("ix_user_onboarding_user_id", table_name="user_onboarding")

    if _table_exists("user_onboarding"):
        op.drop_table("user_onboarding")
