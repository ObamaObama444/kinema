"""add mobile profile data tables and telegram link fields

Revision ID: 0008_mobile_profile_data
Revises: 0007_user_onboarding
Create Date: 2026-03-09 12:20:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008_mobile_profile_data"
down_revision: str | None = "0007_user_onboarding"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index.get("name") == index_name for index in indexes)


def upgrade() -> None:
    if not _table_exists("favorite_items"):
        op.create_table(
            "favorite_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("item_type", sa.String(length=32), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_favorite_items_user_item"),
        )
    if _table_exists("favorite_items") and not _index_exists("favorite_items", "ix_favorite_items_user_id"):
        op.create_index("ix_favorite_items_user_id", "favorite_items", ["user_id"], unique=False)

    if not _table_exists("weight_entries"):
        op.create_table(
            "weight_entries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("weight_kg", sa.Float(), nullable=False),
            sa.Column("recorded_on_local_date", sa.Date(), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "recorded_on_local_date", name="uq_weight_entries_user_day"),
        )
    if _table_exists("weight_entries") and not _index_exists("weight_entries", "ix_weight_entries_user_id"):
        op.create_index("ix_weight_entries_user_id", "weight_entries", ["user_id"], unique=False)

    if not _table_exists("user_settings"):
        op.create_table(
            "user_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("theme_preference", sa.String(length=16), server_default=sa.text("'system'"), nullable=False),
            sa.Column("language", sa.String(length=8), server_default=sa.text("'ru'"), nullable=False),
            sa.Column("weight_unit", sa.String(length=8), server_default=sa.text("'kg'"), nullable=False),
            sa.Column("height_unit", sa.String(length=8), server_default=sa.text("'cm'"), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("user_settings") and not _index_exists("user_settings", "ix_user_settings_user_id"):
        op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"], unique=True)

    if not _table_exists("reminder_rules"):
        op.create_table(
            "reminder_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("title", sa.String(length=140), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("time_local", sa.String(length=5), nullable=False),
            sa.Column("days_json", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("timezone", sa.String(length=64), server_default=sa.text("'UTC'"), nullable=False),
            sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if _table_exists("reminder_rules") and not _index_exists("reminder_rules", "ix_reminder_rules_user_id"):
        op.create_index("ix_reminder_rules_user_id", "reminder_rules", ["user_id"], unique=False)

    if _table_exists("users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if not _column_exists("users", "avatar_url"):
                batch_op.add_column(sa.Column("avatar_url", sa.String(length=255), nullable=True))
            if not _column_exists("users", "telegram_user_id"):
                batch_op.add_column(sa.Column("telegram_user_id", sa.String(length=64), nullable=True))
            if not _column_exists("users", "telegram_username"):
                batch_op.add_column(sa.Column("telegram_username", sa.String(length=120), nullable=True))
            if not _column_exists("users", "telegram_first_name"):
                batch_op.add_column(sa.Column("telegram_first_name", sa.String(length=120), nullable=True))
            if not _column_exists("users", "telegram_linked_at"):
                batch_op.add_column(sa.Column("telegram_linked_at", sa.DateTime(timezone=True), nullable=True))
            if not _column_exists("users", "telegram_last_seen_at"):
                batch_op.add_column(sa.Column("telegram_last_seen_at", sa.DateTime(timezone=True), nullable=True))
        if not _index_exists("users", "ix_users_telegram_user_id"):
            op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=True)


def downgrade() -> None:
    if _table_exists("users") and _index_exists("users", "ix_users_telegram_user_id"):
        op.drop_index("ix_users_telegram_user_id", table_name="users")

    if _table_exists("users"):
        with op.batch_alter_table("users", schema=None) as batch_op:
            if _column_exists("users", "telegram_last_seen_at"):
                batch_op.drop_column("telegram_last_seen_at")
            if _column_exists("users", "telegram_linked_at"):
                batch_op.drop_column("telegram_linked_at")
            if _column_exists("users", "telegram_first_name"):
                batch_op.drop_column("telegram_first_name")
            if _column_exists("users", "telegram_username"):
                batch_op.drop_column("telegram_username")
            if _column_exists("users", "telegram_user_id"):
                batch_op.drop_column("telegram_user_id")

    if _table_exists("reminder_rules") and _index_exists("reminder_rules", "ix_reminder_rules_user_id"):
        op.drop_index("ix_reminder_rules_user_id", table_name="reminder_rules")
    if _table_exists("reminder_rules"):
        op.drop_table("reminder_rules")

    if _table_exists("user_settings") and _index_exists("user_settings", "ix_user_settings_user_id"):
        op.drop_index("ix_user_settings_user_id", table_name="user_settings")
    if _table_exists("user_settings"):
        op.drop_table("user_settings")

    if _table_exists("weight_entries") and _index_exists("weight_entries", "ix_weight_entries_user_id"):
        op.drop_index("ix_weight_entries_user_id", table_name="weight_entries")
    if _table_exists("weight_entries"):
        op.drop_table("weight_entries")

    if _table_exists("favorite_items") and _index_exists("favorite_items", "ix_favorite_items_user_id"):
        op.drop_index("ix_favorite_items_user_id", table_name="favorite_items")
    if _table_exists("favorite_items"):
        op.drop_table("favorite_items")
