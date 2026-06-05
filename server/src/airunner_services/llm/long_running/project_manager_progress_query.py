"""Progress query helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any

from airunner_services.database.models.project_state import ProgressEntry
from airunner_services.database.session import session_scope


def get_progress_log(
    manager: Any,
    project_id: int,
    limit: int = 20,
) -> list[ProgressEntry]:
    """Return recent progress entries for one project."""
    with session_scope() as db:
        entries = (
            db.query(ProgressEntry)
            .filter(ProgressEntry.project_id == project_id)
            .order_by(ProgressEntry.timestamp.desc())
            .limit(limit)
            .all()
        )
        return manager._detach_all(db, entries)


def get_progress_as_text(
    manager: Any,
    project_id: int,
    limit: int = 20,
) -> str:
    """Return the progress log as human-readable text."""
    entries = manager.get_progress_log(project_id, limit)
    if not entries:
        return "No progress recorded yet."
    lines = ["# Progress Log", ""]
    for entry in reversed(entries):
        lines.append(entry.to_log_string())
        lines.append("")
    return "\n".join(lines)


# Query helpers keep persistence and text rendering on one narrow surface for
# progress consumers.
# The list and text forms share the same ordering rules to avoid drift.
# Higher-level tools can choose either representation without extra queries.
