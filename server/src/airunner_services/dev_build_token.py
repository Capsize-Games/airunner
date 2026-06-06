"""Service-owned dev-build token helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

_CACHE_TTL_SECONDS = 2.0
_cached_deadline = 0.0
_cached_token: Optional[str] = None


def current_dev_build_token() -> Optional[str]:
    """Return a short token that changes when local source files change."""
    global _cached_deadline, _cached_token
    if os.environ.get("DEV_ENV", "1") != "1":
        return None
    now = time.monotonic()
    if now < _cached_deadline:
        return _cached_token
    repo_root = _find_repo_root(Path(__file__).resolve())
    _cached_token = _scan_source_tree(repo_root)
    _cached_deadline = now + _CACHE_TTL_SECONDS
    return _cached_token


def _find_repo_root(start: Path) -> Path:
    """Return the nearest repository root for one source path."""
    current = start.parent if start.is_file() else start
    for _ in range(12):
        if (current / "pyproject.toml").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return start.parent


def _scan_source_tree(source_root: Path) -> Optional[str]:
    """Return a token for the newest relevant Python file in the repo."""
    newest_mtime = 0
    newest_relpath = ""
    for path in source_root.rglob("*.py"):
        if _skip_path(path):
            continue
        mtime = path.stat().st_mtime_ns
        if mtime <= newest_mtime:
            continue
        newest_mtime = mtime
        newest_relpath = str(path.relative_to(source_root))
    if newest_mtime == 0:
        return None
    return f"{newest_mtime}:{newest_relpath}"


def _skip_path(path: Path) -> bool:
    """Return True when one file should not affect daemon restart checks."""
    parts = set(path.parts)
    return bool(
        parts
        & {
            ".git",
            "__pycache__",
            "airunner.egg-info",
            "build",
            "dist",
            "node_modules",
            "tests",
            "venv",
            "vendor",
        }
    )


__all__ = ["current_dev_build_token"]
