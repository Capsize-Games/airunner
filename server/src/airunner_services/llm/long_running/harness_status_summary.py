"""Summary builders for harness project-status responses."""

from __future__ import annotations

from typing import Any


def status_counts(features: list[Any]) -> dict[str, int]:
    """Return feature counts by status."""
    counts: dict[str, int] = {}
    for feature in features:
        status = feature.status.value if feature.status else "not_started"
        counts[status] = counts.get(status, 0) + 1
    return counts


def recent_progress(progress_log: list[Any]) -> list[dict[str, str]]:
    """Return recent progress entries as plain dictionaries."""
    return [
        {
            "timestamp": str(entry.timestamp),
            "action": entry.action,
            "outcome": entry.outcome,
        }
        for entry in progress_log
    ]
