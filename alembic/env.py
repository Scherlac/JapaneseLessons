from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from jlesson.rcm.store import _Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = _Base.metadata


def _resolve_url() -> str:
    # Priority 1: -x db_path=<path> on the command line
    x_args = context.get_x_argument(as_dictionary=True)
    db_path = x_args.get("db_path")
    if db_path:
        return f"sqlite:///{db_path}"

    # Priority 2: JLESSON_RCM_DB environment variable
    env_db = os.environ.get("JLESSON_RCM_DB")
    if env_db:
        return f"sqlite:///{env_db}"

    # Priority 3: sqlalchemy.url from alembic.ini (fallback / CI placeholder)
    ini_url = config.get_main_option("sqlalchemy.url")
    if not ini_url:
        raise RuntimeError(
            "No database path configured. Set JLESSON_RCM_DB env var or pass"
            " -x db_path=<path> to alembic."
        )
    return ini_url


def run_migrations_offline() -> None:
    url = _resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()