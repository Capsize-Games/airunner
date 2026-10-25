"""Git history helpers for the long-running project manager."""

from __future__ import annotations

import re
from typing import Any

from airunner_services.llm.long_running.project_manager_git_exec import _run_git
from airunner_services.llm.long_running.project_manager_git_repo import (
    _project_repo_path,
)

#: Bounds for the ``get_git_log`` entry count. The limit arrives from
#: model-generated arguments, so it is coerced to int and clamped:
#: a crafted string must not smuggle extra ``git log`` flags, and a
#: huge count must not dump unbounded history into the context.
DEFAULT_GIT_LOG_LIMIT = 10
MIN_GIT_LOG_LIMIT = 1
MAX_GIT_LOG_LIMIT = 100

#: Full or abbreviated commit SHAs only. ``git reset --hard`` runs with
#: the hash as an argv item (no shell), but an unvalidated ref still
#: resolves to anything (``HEAD@{...}``, ``--upload-pack=`` flags,
#: remote refs), so only hex hashes are accepted.
_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{4,64}$")


def coerce_git_log_limit(limit: Any) -> int:
    """Coerce one model-supplied log limit to a clamped int."""
    try:
        coerced = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_GIT_LOG_LIMIT
    return max(MIN_GIT_LOG_LIMIT, min(MAX_GIT_LOG_LIMIT, coerced))


def is_safe_commit_hash(commit_hash: Any) -> bool:
    """Return whether one ref is a plain hex commit hash."""
    return isinstance(commit_hash, str) and bool(
        _COMMIT_HASH_RE.match(commit_hash)
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
    if not is_safe_commit_hash(commit_hash):
        manager._logger.error(
            "Git revert refused: not a plain commit hash: %r",
            commit_hash,
        )
        return False
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
    limit: Any = DEFAULT_GIT_LOG_LIMIT,
) -> list[dict[str, str]]:
    """Return recent git commits for one project."""
    repo_path = _project_repo_path(manager, project_id)
    if repo_path is None:
        return []
    count = coerce_git_log_limit(limit)
    try:
        result = _run_git(
            ["git", "log", f"-{count}", "--pretty=format:%H|%s|%ai"],
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