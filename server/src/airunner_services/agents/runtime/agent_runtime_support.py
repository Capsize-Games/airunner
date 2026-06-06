"""Shared helpers for persisted agent runtime records."""

from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

EnumType = TypeVar("EnumType")


def default_record_id() -> str:
    """Return a stable unique identifier for a runtime record."""
    return str(uuid4())


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 form."""
    return datetime.now(UTC).isoformat()


def copy_dict(value: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a shallow copy of a JSON-compatible mapping."""
    return dict(value or {})


def copy_list(value: list[str] | None = None) -> list[str]:
    """Return a shallow copy of a string list."""
    return list(value or [])


def enum_value(enum_cls: type[EnumType], value: Any) -> EnumType:
    """Coerce a string or enum member into the requested enum type."""
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)
