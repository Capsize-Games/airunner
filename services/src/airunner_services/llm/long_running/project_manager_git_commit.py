"""Git commit helpers for the long-running project manager."""

from __future__ import annotations

from typing import Any, Optional

from airunner_services.llm.long_running.project_manager_git_exec import _run_git


def _stage_files(repo_path: str, files: list[str]) -> None:
    """Stage the requested files before commit."""
    args = ["git", "add", *files] if files else ["git", "add", "-A"]
    _run_git(args, repo_path)


def _head_commit(repo_path: str) -> str:
    """Return the current HEAD commit hash."""
    result = _run_git(["git", "rev-parse", "HEAD"], repo_path, text=True)
    return result.stdout.strip()


def _git_commit(
    manager: Any,
    repo_path: str,
    message: str,
    files: list[str],
) -> Optional[str]:
    """Create one git commit and return its hash."""
    try:
        _stage_files(repo_path, files)
        _run_git(["git", "commit", "-m", message], repo_path)
        return _head_commit(repo_path)
    except Exception as error:
        manager._logger.error("Git commit failed: %s", error)
        return None