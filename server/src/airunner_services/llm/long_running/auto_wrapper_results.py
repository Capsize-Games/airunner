"""Prompt, progress, and result helpers for the automatic wrapper."""

from __future__ import annotations

import logging
from typing import Any

from airunner_services.database.models.project_state import ProjectState
from airunner_services.llm.long_running.task_detector import TaskAnalysis

logger = logging.getLogger(__name__)


def aggregate_results(
    agent: Any,
    results: list[dict[str, Any]],
    analysis: TaskAnalysis,
    project: ProjectState,
) -> dict[str, Any]:
    """Aggregate feature results into one public response."""
    if not results:
        return {"response": "No results generated.", "project_id": project.id}
    return {
        "response": _summary(project, len(results))
        + _combined_responses(results),
        "project_id": project.id,
        "task_count": len(results),
        "task_type": analysis.task_type.value,
    }
    # Aggregation stays separate from prompt building so execution can remain linear.


def _summary(project: ProjectState, result_count: int) -> str:
    """Return the aggregated summary header."""
    return (
        f"**Completed {result_count} tasks** "
        f"(Project: {project.name}, ID: {project.id})\n\n"
    )
    # The header gives the merged response a stable project-scoped introduction.


def _combined_responses(results: list[dict[str, Any]]) -> str:
    """Return one combined response body from feature results."""
    responses: list[str] = []
    for index, result in enumerate(results):
        response = result.get("response", "")
        if response:
            responses.append(f"## Part {index + 1}\n\n{response}")
    return "\n\n---\n\n".join(responses)
    # Each feature result becomes a numbered section in the final response.
