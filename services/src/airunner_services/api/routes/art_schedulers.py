"""Scheduler discovery for art API routes (issue #2228)."""

from airunner_common.contract_enums import Scheduler
from airunner_services.database.models.schedulers import Schedulers
from airunner_services.database.session import session_scope


def stored_scheduler_names() -> list[str]:
    """Return scheduler display names stored in the database.

    Scalars are extracted inside the session scope so a detached or
    missing database can never break the caller; failures yield [].
    """
    try:
        with session_scope() as session:
            rows = session.query(Schedulers.display_name).all()
            names = sorted({row[0] for row in rows if row[0]})
            return [str(name) for name in names]
    except Exception:
        return []


def contract_scheduler_names() -> list[str]:
    """Return the canonical scheduler display names."""
    return [item.value for item in Scheduler]


def list_scheduler_names() -> list[str]:
    """Return the valid scheduler names for art generation.

    The schedulers table is authoritative (the runtime matches the
    request's scheduler string against display_name); the contract
    enum is the fallback when the database is unavailable or empty.
    """
    return stored_scheduler_names() or contract_scheduler_names()
