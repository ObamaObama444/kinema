"""add onboarding equipment tags

Revision ID: 0012_onboarding_equipment_tags
Revises: 0011_exercise_technique_profiles
Create Date: 2026-03-14 22:10:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012_onboarding_equipment_tags"
down_revision: str | None = "0011_exercise_technique_profiles"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def upgrade() -> None:
    if not _column_exists("user_onboarding", "equipment_tags"):
        op.add_column("user_onboarding", sa.Column("equipment_tags", sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists("user_onboarding", "equipment_tags"):
        op.drop_column("user_onboarding", "equipment_tags")
