"""Numeric bounds for legacy LLM compatibility routes."""

from __future__ import annotations

from typing import Any

MAX_PROMPT_CHARS = 16000


def _is_number(value: Any) -> bool:
    """Return whether a value is a real number (never a bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def in_range(value: Any, low: float, high: float) -> bool:
    """Return whether a numeric value falls inside one closed range."""
    return _is_number(value) and low <= float(value) <= high


def is_int_range(value: Any, low: int, high: int) -> bool:
    """Return whether a value is an int inside one closed range."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and low <= value <= high
    )


def clamp_temperature(value: Any, default: float = 0.7) -> float:
    """Coerce a caller temperature into the documented 0..2 range."""
    if in_range(value, 0.0, 2.0):
        return float(value)
    return default


def clamp_max_tokens(value: Any, default: int = 2048) -> int:
    """Coerce a caller token budget into the documented 1..max range."""
    from .llm_contracts import max_ws_output_tokens

    if is_int_range(value, 1, max_ws_output_tokens()):
        return int(value)
    return default


def clamp_repetition_penalty(
    value: Any, default: float = 1.15
) -> float:
    """Coerce a caller repetition penalty into the 0..2 range."""
    if in_range(value, 0.0, 2.0):
        return float(value)
    return default


__all__ = [
    "MAX_PROMPT_CHARS",
    "is_int_range",
    "in_range",
    "clamp_max_tokens",
    "clamp_repetition_penalty",
    "clamp_temperature",
]
