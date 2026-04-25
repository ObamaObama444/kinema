"""allow system exercise technique profiles

Revision ID: 0015_system_technique_profiles
Revises: 0014_daily_records_water_progress
Create Date: 2026-04-24 22:20:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015_system_technique_profiles"
down_revision: str | None = "0014_daily_records_water_progress"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {str(column.get("name")) for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _table_exists("exercise_technique_profiles"):
        return

    columns = _column_names("exercise_technique_profiles")
    if "is_system" not in columns:
        op.add_column(
            "exercise_technique_profiles",
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.execute("UPDATE exercise_technique_profiles SET is_system = FALSE WHERE is_system IS NULL")
        op.alter_column("exercise_technique_profiles", "is_system", server_default=None)

    op.alter_column(
        "exercise_technique_profiles",
        "owner_user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    if not _table_exists("exercise_technique_profiles"):
        return

    columns = _column_names("exercise_technique_profiles")
    if "is_system" in columns:
        op.drop_column("exercise_technique_profiles", "is_system")

    op.alter_column(
        "exercise_technique_profiles",
        "owner_user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
