"""add profile hub checkins and relax weight uniqueness

Revision ID: 0009_profile_hub_checkins_and_weight_cooldown
Revises: 0008_mobile_profile_data
Create Date: 2026-03-12 18:10:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_profile_hub_checkins_and_weight_cooldown"
down_revision: str | None = "0008_mobile_profile_data"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def _unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    constraints = sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def upgrade() -> None:
    if not _table_exists("workout_checkins"):
        op.create_table(
            "workout_checkins",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("local_date", sa.Date(), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "local_date", name="uq_workout_checkins_user_day"),
        )
    if _table_exists("workout_checkins") and not _index_exists("workout_checkins", "ix_workout_checkins_user_id"):
        op.create_index("ix_workout_checkins_user_id", "workout_checkins", ["user_id"], unique=False)

    if _table_exists("weight_entries") and _unique_constraint_exists("weight_entries", "uq_weight_entries_user_day"):
        with op.batch_alter_table("weight_entries", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_weight_entries_user_day", type_="unique")


def downgrade() -> None:
    if _table_exists("weight_entries") and not _unique_constraint_exists("weight_entries", "uq_weight_entries_user_day"):
        with op.batch_alter_table("weight_entries", recreate="always") as batch_op:
            batch_op.create_unique_constraint(
                "uq_weight_entries_user_day",
                ["user_id", "recorded_on_local_date"],
            )

    if _table_exists("workout_checkins") and _index_exists("workout_checkins", "ix_workout_checkins_user_id"):
        op.drop_index("ix_workout_checkins_user_id", table_name="workout_checkins")
    if _table_exists("workout_checkins"):
        op.drop_table("workout_checkins")
