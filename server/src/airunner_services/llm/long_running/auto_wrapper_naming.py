"""Naming helpers for automatic harness projects and features."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.task_detector import (
    TaskAnalysis,
    TaskType,
)


def generate_project_name(
    agent: Any,
    prompt: str,
    analysis: TaskAnalysis,
) -> str:
    """Generate a concise project name for one prompt."""
    del agent
    words = prompt.split()[:5]
    base_name = "_".join(word.lower() for word in words if len(word) > 2)
    prefix = {
        TaskType.MULTI_RESEARCH: "research",
        TaskType.CODING_PROJECT: "task",
        TaskType.MULTI_STEP: "task",
        TaskType.COMPLEX_ANALYSIS: "analysis",
    }.get(analysis.task_type, "project")
    name = f"{prefix}_{base_name}"
    return "".join(
        char if char.isalnum() or char == "_" else "_" for char in name
    )[:50]
    # Project names stay short and coarse so downstream tools can reuse them safely.


def sanitize_feature_name(agent: Any, name: str) -> str:
    """Sanitize one feature name for project storage."""
    del agent
    sanitized = "".join(
        char if char.isalnum() or char in "_- " else "_" for char in name
    )
    sanitized = sanitized.replace(" ", "_")
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized[:50].strip("_")
    # Collapse repeated separators so generated names remain readable.
