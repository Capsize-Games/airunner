"""Helpers for resolving art API signal codes across runtime modes."""

from __future__ import annotations

from typing import Any

from airunner_services.utils.application.enum_resolver import (
    signal_code_member,
)


def get_art_signal_code(name: str) -> Any:
    """Return one art signal code by name using service-owned fallbacks."""
    return signal_code_member(name)


__all__ = ["get_art_signal_code"]
