"""Git history helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any

from airunner_services.llm.long_running.project_manager_git_exec import _run_git
from airunner_services.llm.long_running.project_manager_git_repo import (
    _project_repo_path,
)


def _commit_rows(output: str) -> list[dict[str, str]]:
    """Parse git log output into structured commit rows."""
    commits: list[dict[str, str]] = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) == 3:
            commits.append(
                {
                    "hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                }
            )
    return commits


def git_revert_to_commit(
    manager: Any,
    project_id: int,
    commit_hash: str,
) -> bool:
    """Revert one project to a specific git commit."""
    repo_path = _project_repo_path(manager, project_id)
    if repo_path is None:
        return False
    try:
        _run_git(["git", "reset", "--hard", commit_hash], repo_path)
        manager._logger.info("Reverted to commit %s", commit_hash[:7])
        return True
    except Exception as error:
        manager._logger.error("Git revert failed: %s", error)
        return False


def get_git_log(
    manager: Any,
    project_id: int,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Return recent git commits for one project."""
    repo_path = _project_repo_path(manager, project_id)
    if repo_path is None:
        return []
    try:
        result = _run_git(
            ["git", "log", f"-{limit}", "--pretty=format:%H|%s|%ai"],
            repo_path,
            text=True,
        )
        return _commit_rows(result.stdout)
    except Exception as error:
        manager._logger.error("Git log failed: %s", error)
        return []


# Git history helpers stay separate from repository discovery and command
# execution.
# That split keeps parsing, logging, and repo-path concerns loosely coupled.
# Callers only consume structured rows or simple success booleans.