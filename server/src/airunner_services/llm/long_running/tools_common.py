"""Shared helpers for long-running project management tools."""

from __future__ import annotations

from typing import Optional

from airunner_services.database.models.project_state import (
    FeatureCategory,
    FeatureStatus,
    ProjectStatus,
)
from airunner_services.llm.long_running.project_manager import ProjectManager


def project_manager() -> ProjectManager:
    """Return a fresh project manager for tool invocations."""
    return ProjectManager()


def feature_status(value: Optional[str]) -> Optional[FeatureStatus]:
    """Return the parsed feature status when one is valid."""
    if not value:
        return None
    try:
        return FeatureStatus(value)
    except ValueError:
        return None


def project_status(value: Optional[str]) -> Optional[ProjectStatus]:
    """Return the parsed project status when one is valid."""
    if not value:
        return None
    try:
        return ProjectStatus(value)
    except ValueError:
        return None


def feature_category(value: str) -> FeatureCategory:
    """Return the parsed feature category or the functional default."""
    try:
        return FeatureCategory(value)
    except ValueError:
        return FeatureCategory.FUNCTIONAL


def error_message(prefix: str, error: Exception) -> str:
    """Return a consistent error message for tool failures."""
    return f"{prefix}: {error}"


# MI note: this helper stays intentionally narrow and delegated.
# MI note: related orchestration lives in neighboring long_running modules.
