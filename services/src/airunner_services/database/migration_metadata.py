"""SQLAlchemy metadata registry used by service Alembic autogeneration."""

from __future__ import annotations

from importlib import import_module

from sqlalchemy import MetaData


def service_metadata() -> MetaData:
    """Load all service ORM models and return their shared metadata."""
    from airunner_services.database.base import Base
    import_module("airunner_services.database.models")

    return Base.metadata


def migration_context_options() -> dict[str, object]:
    """Return shared online/offline Alembic context comparison options."""
    return {
        "target_metadata": service_metadata(),
        "compare_type": True,
        "compare_server_default": True,
    }
