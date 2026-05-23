"""Repository path helpers for native-owned source tooling."""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root(anchor: Path | None = None) -> Path:
    """Return the AIRunner repository root for one source file."""
    start = (anchor or Path(__file__)).resolve()
    for candidate in start.parents:
        if _looks_like_repo_root(candidate):
            return candidate
    raise FileNotFoundError("Unable to resolve the AIRunner repository root")


def _looks_like_repo_root(candidate: Path) -> bool:
    """Return True when one directory looks like the repo root."""
    gui_root = candidate / "gui" / "src" / "airunner"
    return all(
        (
            (candidate / "pyproject.toml").exists(),
            (candidate / "native" / "embedded_python").exists(),
            gui_root.exists(),
        )
    )