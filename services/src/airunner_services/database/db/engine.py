"""Service-owned engine helpers for migrations and DB setup."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine, event

from airunner_services.runtimes.postgresql_runtime import (
    configure_postgresql_runtime,
    normalize_postgresql_url,
)


SQLITE_BUSY_TIMEOUT_MS = 5000


def _is_sqlite_url(db_url: object) -> bool:
    """Return whether one database URL targets SQLite."""
    return str(db_url).lower().startswith("sqlite")


def _configure_sqlite_connection(
    dbapi_connection,
    _connection_record,
) -> None:
    """Apply SQLite pragmas used for local concurrent access."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    finally:
        cursor.close()


def create_configured_engine(db_url: object, **kwargs):
    """Create one SQLAlchemy engine with AIRunner defaults applied."""
    configure_postgresql_runtime(db_url)
    db_url = normalize_postgresql_url(db_url)
    engine = create_engine(db_url, **kwargs)
    if _is_sqlite_url(db_url):
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


def create_metadata_engine(db_url: object, **kwargs):
    """Create an engine for metadata reads without mutating SQLite state.

    SQLite's journal-mode pragma needs a write lock. Callers that only inspect
    schema or migration metadata must remain readable while another process
    holds ``BEGIN IMMEDIATE``, so this factory retains PostgreSQL runtime
    preparation and URL normalization without installing the SQLite WAL hook.
    """
    configure_postgresql_runtime(db_url)
    db_url = normalize_postgresql_url(db_url)
    return create_engine(db_url, **kwargs)


def create_configured_engine_from_config(
    configuration: dict, prefix: str = "sqlalchemy.", **kwargs
):
    """Preserve SQLAlchemy configuration coercion and service DB defaults."""
    options = {
        key[len(prefix):]: value
        for key, value in configuration.items()
        if key.startswith(prefix)
    }
    options["_coerce_config"] = True
    options.update(kwargs)
    return create_configured_engine(options.pop("url"), **options)


def get_connection():
    """Return the active Alembic bind connection."""
    return op.get_bind()


def get_inspector():
    """Return one SQLAlchemy inspector for the active Alembic bind."""
    return sa.inspect(get_connection())


__all__ = [
    "SQLITE_BUSY_TIMEOUT_MS",
    "create_configured_engine",
    "create_metadata_engine",
    "create_configured_engine_from_config",
    "get_connection",
    "get_inspector",
]
