"""Service-owned engine helpers for migrations and DB setup.

Reads the active database URL from the settings module —
PostgreSQL only (web-only deployment).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import create_engine


def create_configured_engine(db_url: object, **kwargs):
    """Create one SQLAlchemy engine with AIRunner defaults applied."""
    return create_engine(db_url, **kwargs)


def get_connection():
    """Return the active Alembic bind connection."""
    return op.get_bind()


def get_inspector():
    """Return one SQLAlchemy inspector for the active Alembic bind."""
    return sa.inspect(get_connection())


__all__ = [
    "create_configured_engine",
    "get_connection",
    "get_inspector",
]
