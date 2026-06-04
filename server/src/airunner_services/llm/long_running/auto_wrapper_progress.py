"""Progress callback helpers for the automatic wrapper."""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def emit_progress(
    agent: Any,
    task_name: str,
    status: str,
    progress: float,
) -> None:
    """Emit one progress update when a callback is configured."""
    if agent._on_progress:
        try:
            agent._on_progress(task_name, status, progress)
        except Exception as error:
            logger.warning("Progress callback failed: %s", error)