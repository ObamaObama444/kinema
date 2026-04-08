from __future__ import annotations

from logging.config import fileConfig

from alembic import context
import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata
ALEMBIC_VERSION_TABLE = "alembic_version"
ALEMBIC_VERSION_COLUMN_LENGTH = 255


def _ensure_alembic_version_table_capacity(connection: sa.Connection) -> None:
    if connection.dialect.name != "postgresql":
        return

    inspector = sa.inspect(connection)
    if not inspector.has_table(ALEMBIC_VERSION_TABLE):
        connection.execute(
            sa.text(
                f"""
                CREATE TABLE {ALEMBIC_VERSION_TABLE} (
                    version_num VARCHAR({ALEMBIC_VERSION_COLUMN_LENGTH}) NOT NULL PRIMARY KEY
                )
                """
            )
        )
        connection.commit()
        return

    columns = inspector.get_columns(ALEMBIC_VERSION_TABLE)
    version_column = next((column for column in columns if column.get("name") == "version_num"), None)
    current_length = getattr(version_column.get("type") if version_column else None, "length", None)
    if current_length is not None and current_length < ALEMBIC_VERSION_COLUMN_LENGTH:
        connection.execute(
            sa.text(
                f"""
                ALTER TABLE {ALEMBIC_VERSION_TABLE}
                ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_COLUMN_LENGTH})
                """
            )
        )
        connection.commit()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_alembic_version_table_capacity(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
