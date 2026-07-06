"""Alembic environment — reads DATABASE_URL from app.core.config (which in
turn reads it from the environment / apps/api/.env), never from
alembic.ini, so the connection string is never checked into the repo.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.models import Base
from app.db.session import _with_psycopg_driver

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not set — required to run migrations. "
            "See apps/api/.env.example."
        )
    # Same normalization app/db/session.py's get_engine() applies — a bare
    # postgresql:// URL (e.g. pasted from Supabase's dashboard) otherwise
    # makes SQLAlchemy default to the psycopg2 dialect, which this project
    # doesn't install (see requirements.txt's psycopg[binary], v3).
    return _with_psycopg_driver(settings.database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
