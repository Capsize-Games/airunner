"""Repository path helpers for native-owned source tooling."""

from __future__ import annotations

from pathlib import Path


def resolve_gui_project_root(repo_root: Path) -> Path:
    """Return the current GUI package project root for this checkout."""
    candidates = (repo_root / "gui", repo_root)
    for candidate in candidates:
        if _looks_like_gui_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        f"Unable to resolve the AIRunner GUI project root under {repo_root}"
    )


def resolve_gui_source_root(repo_root: Path) -> Path:
    """Return the current GUI source root for this checkout."""
    return resolve_gui_project_root(repo_root) / "src"


def resolve_repo_root(anchor: Path | None = None) -> Path:
    """Return the AIRunner repository root for one source file."""
    start = (anchor or Path(__file__)).resolve()
    for candidate in start.parents:
        if _looks_like_repo_root(candidate):
            return candidate
    raise FileNotFoundError("Unable to resolve the AIRunner repository root")


def _looks_like_repo_root(candidate: Path) -> bool:
    """Return True when one directory looks like the repo root."""
    if not (candidate / "pyproject.toml").exists():
        return False
    if not (candidate / "native" / "embedded_python").exists():
        return False
    return any(
        _looks_like_gui_project_root(project_root)
        for project_root in (candidate / "gui", candidate)
    )


def _looks_like_gui_project_root(candidate: Path) -> bool:
    """Return whether one directory looks like the GUI package root."""
    return all(
        (
            (candidate / "setup.py").exists(),
            (candidate / "src" / "airunner").exists(),
        )
    )


__all__ = [
    "resolve_gui_project_root",
    "resolve_gui_source_root",
    "resolve_repo_root",
]