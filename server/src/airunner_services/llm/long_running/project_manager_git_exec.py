"""Git command execution helpers for the long-running project manager."""

from __future__ import annotations

import subprocess


def _run_git(
    args: list[str],
    repo_path: str,
    *,
    text: bool = False,
) -> subprocess.CompletedProcess:
    """Run one git command for the requested repository."""
    return subprocess.run(
        args,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=text,
    )