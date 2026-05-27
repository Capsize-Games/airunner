import os
import logging
import sys
from pathlib import Path

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

logger = logging.getLogger("alembic.env")

# Alembic configuration object, which provides access to the values within the
# .ini file in use.
config = context.config


def _bootstrap_checkout_imports() -> None:
    """Add split source roots when Alembic runs from a repo checkout."""
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if not (candidate / "pyproject.toml").exists():
            continue
        for source_root in reversed(
            (
                candidate / "src",
                candidate / "model" / "src",
                candidate / "services" / "src",
                candidate / "native" / "src",
            )
        ):
            source_root_str = str(source_root)
            if source_root.exists() and source_root_str not in sys.path:
                sys.path.insert(0, source_root_str)
        return


_bootstrap_checkout_imports()

def _default_db_url() -> str:
    """Return the default database URL for Alembic commands."""
    from airunner_model.settings import AIRUNNER_DB_URL as default_airunner_db_url

    return (
        os.environ.get("AIRUNNER_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or default_airunner_db_url
    )


# Ensure Alembic has a URL; callers may override via setup_database().
try:
    existing_url = config.get_main_option("sqlalchemy.url")
except Exception:
    existing_url = None
if not existing_url:
    config.set_main_option("sqlalchemy.url", _default_db_url())

# Configure Python logging (best-effort).
try:
    if getattr(config, "config_file_name", None) and os.path.exists(config.config_file_name):
        fileConfig(config.config_file_name)
except Exception:
    pass

# We don't use autogenerate in this repo's runtime flow; avoid heavy imports.
target_metadata = None
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=False,
        compare_server_default=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=False,
            compare_server_default=False,
        )

        with context.begin_transaction():
            context.run_migrations()
            connection.commit()


if context.is_offline_mode():
    logger.info("Running migrations offline...")
    run_migrations_offline()
else:
    logger.info("Running migrations online...")
    run_migrations_online()
