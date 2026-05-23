"""Transitional API-facing bootstrap helpers for GUI callers."""

from __future__ import annotations

from typing import Any


def build_runtime_registry(*, app_instance: Any | None = None):
    """Build the default runtime registry via the service layer."""
    from airunner_services.runtimes.bootstrap import (
        build_runtime_registry as service_build_runtime_registry,
    )

    return service_build_runtime_registry(app_instance=app_instance)


def setup_database() -> None:
    """Run the canonical database setup via the service layer."""
    from airunner_services.database.setup import (
        setup_database as service_setup_database,
    )

    service_setup_database()


__all__ = ["build_runtime_registry", "setup_database"]