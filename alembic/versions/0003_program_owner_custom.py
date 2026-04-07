"""add owner for custom programs

Revision ID: 0003_program_owner_custom
Revises: 0002_profile_goal_active_program
Create Date: 2026-02-12 18:45:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_program_owner_custom"
down_revision: str | None = "0002_profile_goal_active_program"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROGRAM_OWNER_COLUMN = "owner_user_id"
PROGRAM_OWNER_INDEX = "ix_programs_owner_user_id"
PROGRAM_OWNER_FK = "fk_programs_owner_user_id_users"


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def _fk_exists_by_name(table_name: str, fk_name: str) -> bool:
    fks = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    return any(fk.get("name") == fk_name for fk in fks)


def _fk_exists_by_columns(table_name: str, constrained: list[str], referred_table: str, referred: list[str]) -> bool:
    fks = sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    for fk in fks:
        if (
            fk.get("constrained_columns") == constrained
            and fk.get("referred_table") == referred_table
            and fk.get("referred_columns") == referred
        ):
            return True
    return False


def upgrade() -> None:
    if not _table_exists("programs"):
        return

    with op.batch_alter_table("programs", schema=None) as batch_op:
        if not _column_exists("programs", PROGRAM_OWNER_COLUMN):
            batch_op.add_column(sa.Column(PROGRAM_OWNER_COLUMN, sa.Integer(), nullable=True))
        if not _index_exists("programs", PROGRAM_OWNER_INDEX):
            batch_op.create_index(PROGRAM_OWNER_INDEX, [PROGRAM_OWNER_COLUMN], unique=False)

        has_fk = _fk_exists_by_name("programs", PROGRAM_OWNER_FK) or _fk_exists_by_columns(
            "programs",
            [PROGRAM_OWNER_COLUMN],
            "users",
            ["id"],
        )
        if not has_fk:
            batch_op.create_foreign_key(
                PROGRAM_OWNER_FK,
                "users",
                [PROGRAM_OWNER_COLUMN],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    if not _table_exists("programs"):
        return

    with op.batch_alter_table("programs", schema=None) as batch_op:
        if _fk_exists_by_name("programs", PROGRAM_OWNER_FK):
            batch_op.drop_constraint(PROGRAM_OWNER_FK, type_="foreignkey")
        if _index_exists("programs", PROGRAM_OWNER_INDEX):
            batch_op.drop_index(PROGRAM_OWNER_INDEX)
        if _column_exists("programs", PROGRAM_OWNER_COLUMN):
            batch_op.drop_column(PROGRAM_OWNER_COLUMN)
