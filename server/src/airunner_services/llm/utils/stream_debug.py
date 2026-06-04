"""Opt-in terminal diagnostics for LLM stream chunks."""

from __future__ import annotations

import os
from typing import Any


_ENABLED_VALUES = {"1", "true", "yes", "on"}


def stream_debug_enabled() -> bool:
    """Return True when raw stream diagnostics should print to stdout."""
    return (
        os.environ.get("AIRUNNER_DEBUG_STREAM_CHUNKS", "")
        .strip()
        .lower()
        in _ENABLED_VALUES
    )


def print_stream_debug(scope: str, **fields: Any) -> None:
    """Print one raw stream diagnostic line when debugging is enabled."""
    if not stream_debug_enabled():
        return

    rendered_fields = " ".join(
        f"{key}={value!r}" for key, value in fields.items()
    )
    print(
        f"[AIRUNNER_STREAM_DEBUG][{scope}] {rendered_fields}",
        flush=True,
    )