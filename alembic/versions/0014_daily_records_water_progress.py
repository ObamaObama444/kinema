"""add water progress to daily records

Revision ID: 0014_daily_records_water_progress
Revises: 0013_daily_records_and_vitals
Create Date: 2026-03-15 00:45:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_daily_records_water_progress"
down_revision: str | None = "0013_daily_records_and_vitals"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    try:
        columns = inspector.get_columns(table_name)
    except sa.exc.NoSuchTableError:
        return False
    return any(column.get("name") == column_name for column in columns)


def upgrade() -> None:
    if not _column_exists("daily_record_goals", "water_consumed_glasses"):
        op.add_column(
            "daily_record_goals",
            sa.Column("water_consumed_glasses", sa.Integer(), server_default="0", nullable=False),
        )


def downgrade() -> None:
    if _column_exists("daily_record_goals", "water_consumed_glasses"):
        op.drop_column("daily_record_goals", "water_consumed_glasses")
