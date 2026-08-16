"""Dev-only source tree token used to detect stale local daemons."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional


_CACHE_TTL_SECONDS = 60.0
_cached_deadline = 0.0
_cached_token: Optional[str] = None

# Only scan meaningful source roots instead of the whole repo, which keeps
# the scan fast and excludes docs, packaging and build artifacts.
_SOURCE_SUBDIRS = ("src", "services/src", "native/src")
_CACHE_DIR_NAME = "build"
_CACHE_FILE_NAME = "dev_build_token.cache"


def current_dev_build_token() -> Optional[str]:
    """Return a short token that changes when local source files change."""
    global _cached_deadline, _cached_token
    if os.environ.get("DEV_ENV", "1") != "1":
        return None
    now = time.monotonic()
    if now < _cached_deadline:
        return _cached_token
    repo_root = _find_repo_root(Path(__file__).resolve())
    # Reuse a disk cache written by any process (e.g. the daemon) so a fresh
    # shell Python process in run_services.sh does not rescan the tree.
    _cached_token = _read_disk_cache(repo_root)
    if _cached_token is None:
        _cached_token = _scan_source_tree(repo_root)
        _write_disk_cache(repo_root, _cached_token)
    _cached_deadline = now + _CACHE_TTL_SECONDS
    return _cached_token


def _scan_source_tree(repo_root: Path) -> Optional[str]:
    """Return a token for the newest relevant Python file in the repo."""
    newest_mtime = 0
    newest_relpath = ""
    for source_subdir in _SOURCE_SUBDIRS:
        source_root = repo_root / source_subdir
        if not source_root.is_dir():
            continue
        for path in source_root.rglob("*.py"):
            if _skip_path(path):
                continue
            mtime = path.stat().st_mtime_ns
            if mtime <= newest_mtime:
                continue
            newest_mtime = mtime
            newest_relpath = str(path.relative_to(repo_root))
    if newest_mtime == 0:
        return None
    return f"{newest_mtime}:{newest_relpath}"


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


def _skip_path(path: Path) -> bool:
    """Return True when one file should not affect daemon restart checks."""
    skip_parts = {
        ".git",
        "__pycache__",
        "airunner.egg-info",
        "build",
        "dist",
        "node_modules",
        "tests",
        "vendor",
    }
    for part in path.parts:
        if part in skip_parts or part.startswith("venv"):
            return True
    return False


def _disk_cache_path(repo_root: Path) -> Path:
    """Return the on-disk cache path shared across processes."""
    return repo_root / _CACHE_DIR_NAME / _CACHE_FILE_NAME


def _read_disk_cache(repo_root: Path) -> Optional[str]:
    """Return the cached token when it is fresh, otherwise None."""
    cache_path = _disk_cache_path(repo_root)
    try:
        if time.time() - cache_path.stat().st_mtime > _CACHE_TTL_SECONDS:
            return None
        token = cache_path.read_text(encoding="utf-8").strip()
        return token or None
    except OSError:
        return None


def _write_disk_cache(repo_root: Path, token: Optional[str]) -> None:
    """Persist the token under build/ for reuse by other processes."""
    if token is None:
        return
    cache_path = _disk_cache_path(repo_root)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(token, encoding="utf-8")
    except OSError:
        return
