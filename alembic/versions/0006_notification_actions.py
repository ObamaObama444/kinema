"""add notification action metadata

Revision ID: 0006_notification_actions
Revises: 0005_user_avatar
Create Date: 2026-02-17 00:45:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_notification_actions"
down_revision: str | None = "0005_user_avatar"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def upgrade() -> None:
    if not _table_exists("notifications"):
        return

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        if not _column_exists("notifications", "action_type"):
            batch_op.add_column(sa.Column("action_type", sa.String(length=64), nullable=True))
        if not _column_exists("notifications", "action_label"):
            batch_op.add_column(sa.Column("action_label", sa.String(length=140), nullable=True))
        if not _column_exists("notifications", "action_payload"):
            batch_op.add_column(sa.Column("action_payload", sa.Text(), nullable=True))


def downgrade() -> None:
    if not _table_exists("notifications"):
        return

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        if _column_exists("notifications", "action_payload"):
            batch_op.drop_column("action_payload")
        if _column_exists("notifications", "action_label"):
            batch_op.drop_column("action_label")
        if _column_exists("notifications", "action_type"):
            batch_op.drop_column("action_type")
