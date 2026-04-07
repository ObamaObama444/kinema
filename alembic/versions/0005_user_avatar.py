"""add user avatar url

Revision ID: 0005_user_avatar
Revises: 0004_notifications
Create Date: 2026-02-16 20:35:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_user_avatar"
down_revision: str | None = "0004_notifications"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def upgrade() -> None:
    if not _table_exists("users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not _column_exists("users", "avatar_url"):
            batch_op.add_column(sa.Column("avatar_url", sa.String(length=255), nullable=True))


def downgrade() -> None:
    if not _table_exists("users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _column_exists("users", "avatar_url"):
            batch_op.drop_column("avatar_url")
