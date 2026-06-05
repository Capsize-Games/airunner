"""Git repository helpers for the long-running project manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from airunner_services.llm.long_running.project_manager_git_exec import (
    _run_git,
)


def _project_repo_path(manager: Any, project_id: int) -> Optional[str]:
    """Return the git repo path for one project when available."""
    project = manager.get_project(project_id)
    if project is None or not project.git_repo_path:
        return None
    return project.git_repo_path


def _init_git_repo(manager: Any, path: Path) -> Optional[str]:
    """Initialize a git repository when it does not already exist."""
    try:
        if not (path / ".git").exists():
            _run_git(["git", "init"], str(path))
            manager._logger.info("Initialized git repo at %s", path)
        return str(path)
    except Exception as error:
        manager._logger.error("Failed to init git: %s", error)
        return None


# Repository-path helpers stay intentionally small so git-history and commit
# helpers can reuse them without re-reading project state.
# Initialization also remains best-effort to avoid blocking project creation.
# Path normalization lives here rather than in higher-level workflow code.
