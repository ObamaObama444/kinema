"""profile and goal constraints update

Revision ID: 0002_profile_goal_active_program
Revises: 0001_initial
Create Date: 2026-02-07 13:15:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_profile_goal_active_program"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


GOAL_UNIQUE_INDEX = "ux_goals_user_id"
GOAL_OLD_INDEX = "ix_goals_user_id"
PROFILE_PROGRAM_INDEX = "ix_profiles_active_program_id"
PROFILE_PROGRAM_FK = "fk_profiles_active_program_id_programs"


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


def _deduplicate_goals() -> None:
    if not _table_exists("goals"):
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, user_id
            FROM goals
            ORDER BY user_id, created_at DESC, id DESC
            """
        )
    ).mappings()

    seen_user_ids: set[int] = set()
    duplicate_ids: list[int] = []

    for row in rows:
        user_id = int(row["user_id"])
        goal_id = int(row["id"])

        if user_id in seen_user_ids:
            duplicate_ids.append(goal_id)
            continue

        seen_user_ids.add(user_id)

    if duplicate_ids:
        bind.execute(
            sa.text("DELETE FROM goals WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": duplicate_ids},
        )


def upgrade() -> None:
    _deduplicate_goals()

    if _table_exists("goals"):
        with op.batch_alter_table("goals", schema=None) as batch_op:
            if _index_exists("goals", GOAL_OLD_INDEX):
                batch_op.drop_index(GOAL_OLD_INDEX)
            if not _index_exists("goals", GOAL_UNIQUE_INDEX):
                batch_op.create_index(GOAL_UNIQUE_INDEX, ["user_id"], unique=True)

    if _table_exists("profiles"):
        with op.batch_alter_table("profiles", schema=None) as batch_op:
            if not _column_exists("profiles", "active_program_id"):
                batch_op.add_column(sa.Column("active_program_id", sa.Integer(), nullable=True))
            if not _column_exists("profiles", "workouts_per_week"):
                batch_op.add_column(sa.Column("workouts_per_week", sa.Integer(), nullable=True))
            if not _index_exists("profiles", PROFILE_PROGRAM_INDEX):
                batch_op.create_index(PROFILE_PROGRAM_INDEX, ["active_program_id"], unique=False)
            has_profile_program_fk = _fk_exists_by_name("profiles", PROFILE_PROGRAM_FK) or _fk_exists_by_columns(
                "profiles",
                ["active_program_id"],
                "programs",
                ["id"],
            )
            if not has_profile_program_fk:
                batch_op.create_foreign_key(
                    PROFILE_PROGRAM_FK,
                    "programs",
                    ["active_program_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
            if _column_exists("profiles", "limitations"):
                batch_op.drop_column("limitations")


def downgrade() -> None:
    if _table_exists("profiles"):
        with op.batch_alter_table("profiles", schema=None) as batch_op:
            if not _column_exists("profiles", "limitations"):
                batch_op.add_column(sa.Column("limitations", sa.Text(), nullable=True))
            if _fk_exists_by_name("profiles", PROFILE_PROGRAM_FK):
                batch_op.drop_constraint(PROFILE_PROGRAM_FK, type_="foreignkey")
            if _index_exists("profiles", PROFILE_PROGRAM_INDEX):
                batch_op.drop_index(PROFILE_PROGRAM_INDEX)
            if _column_exists("profiles", "workouts_per_week"):
                batch_op.drop_column("workouts_per_week")
            if _column_exists("profiles", "active_program_id"):
                batch_op.drop_column("active_program_id")

    if _table_exists("goals"):
        with op.batch_alter_table("goals", schema=None) as batch_op:
            if _index_exists("goals", GOAL_UNIQUE_INDEX):
                batch_op.drop_index(GOAL_UNIQUE_INDEX)
            if not _index_exists("goals", GOAL_OLD_INDEX):
                batch_op.create_index(GOAL_OLD_INDEX, ["user_id"], unique=False)
