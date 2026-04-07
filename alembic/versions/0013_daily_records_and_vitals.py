"""add daily records and vitals

Revision ID: 0013_daily_records_and_vitals
Revises: 0012_onboarding_equipment_tags
Create Date: 2026-03-14 23:05:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013_daily_records_and_vitals"
down_revision: str | None = "0012_onboarding_equipment_tags"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("daily_record_goals"):
        op.create_table(
            "daily_record_goals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("local_date", sa.Date(), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False),
            sa.Column("steps_goal", sa.Integer(), nullable=True),
            sa.Column("water_goal_glasses", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "local_date", name="uq_daily_record_goals_user_date"),
        )
        op.create_index(op.f("ix_daily_record_goals_local_date"), "daily_record_goals", ["local_date"], unique=False)
        op.create_index(op.f("ix_daily_record_goals_user_id"), "daily_record_goals", ["user_id"], unique=False)

    if not _table_exists("vital_measurements"):
        op.create_table(
            "vital_measurements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("local_date", sa.Date(), nullable=False),
            sa.Column("metric_type", sa.String(length=24), nullable=False),
            sa.Column("pulse_bpm", sa.Integer(), nullable=True),
            sa.Column("systolic_mmhg", sa.Integer(), nullable=True),
            sa.Column("diastolic_mmhg", sa.Integer(), nullable=True),
            sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_vital_measurements_local_date"), "vital_measurements", ["local_date"], unique=False)
        op.create_index(op.f("ix_vital_measurements_metric_type"), "vital_measurements", ["metric_type"], unique=False)
        op.create_index(op.f("ix_vital_measurements_recorded_at"), "vital_measurements", ["recorded_at"], unique=False)
        op.create_index(op.f("ix_vital_measurements_user_id"), "vital_measurements", ["user_id"], unique=False)


def downgrade() -> None:
    if _table_exists("vital_measurements"):
        op.drop_index(op.f("ix_vital_measurements_user_id"), table_name="vital_measurements")
        op.drop_index(op.f("ix_vital_measurements_recorded_at"), table_name="vital_measurements")
        op.drop_index(op.f("ix_vital_measurements_metric_type"), table_name="vital_measurements")
        op.drop_index(op.f("ix_vital_measurements_local_date"), table_name="vital_measurements")
        op.drop_table("vital_measurements")

    if _table_exists("daily_record_goals"):
        op.drop_index(op.f("ix_daily_record_goals_user_id"), table_name="daily_record_goals")
        op.drop_index(op.f("ix_daily_record_goals_local_date"), table_name="daily_record_goals")
        op.drop_table("daily_record_goals")
