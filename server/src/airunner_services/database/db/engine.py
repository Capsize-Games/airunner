"""Service-owned engine helpers for migrations and DB setup."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine, event

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
    engine = create_engine(db_url, **kwargs)
    if _is_sqlite_url(db_url):
        event.listen(engine, "connect", _configure_sqlite_connection)
    return engine


def get_connection():
    """Return the active Alembic bind connection."""
    return op.get_bind()


def get_inspector():
    """Return one SQLAlchemy inspector for the active Alembic bind."""
    return sa.inspect(get_connection())


__all__ = [
    "SQLITE_BUSY_TIMEOUT_MS",
    "create_configured_engine",
    "get_connection",
    "get_inspector",
]
