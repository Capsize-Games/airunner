"""Prompt-building helpers for the automatic harness wrapper."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.task_detector import (
    TaskAnalysis,
    TaskType,
)


def create_sub_prompt(
    agent: Any,
    original_prompt: str,
    feature: Any,
    analysis: TaskAnalysis,
) -> str:
    """Create one focused sub-prompt for a feature."""
    del agent
    if analysis.task_type == TaskType.MULTI_RESEARCH:
        return f"Research and provide information about: {feature.name}"
    return (
        f"As part of '{original_prompt}', complete this step: "
        f"{feature.description}"
    )
