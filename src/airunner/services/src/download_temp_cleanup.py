"""Service-owned helpers for removing stale model download temp directories."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import time


DEFAULT_STALE_DOWNLOAD_AGE_SECONDS = 24 * 60 * 60


def _latest_mtime(path: Path) -> float:
    """Return the most recent mtime for a directory tree."""
    latest = path.stat().st_mtime

    for root, dirnames, filenames in os.walk(path):
        root_path = Path(root)
        latest = max(latest, root_path.stat().st_mtime)

        for dirname in dirnames:
            dir_path = root_path / dirname
            latest = max(latest, dir_path.stat().st_mtime)

        for filename in filenames:
            file_path = root_path / filename
            latest = max(latest, file_path.stat().st_mtime)

    return latest


def cleanup_stale_download_dir(
    temp_dir: str | Path,
    max_age_seconds: int = DEFAULT_STALE_DOWNLOAD_AGE_SECONDS,
    logger=None,
) -> bool:
    """Delete a stale .downloading directory if it has not changed recently."""
    path = Path(temp_dir)

    if not path.exists() or not path.is_dir():
        return False

    age_seconds = time.time() - _latest_mtime(path)
    if age_seconds < max_age_seconds:
        return False

    try:
        shutil.rmtree(path)
    except Exception as exc:
        if logger:
            logger.warning(
                "Failed to remove stale download temp dir %s: %s",
                path,
                exc,
            )
        return False

    if logger:
        logger.info(
            "Removed stale download temp dir %s (age %.1f hours)",
            path,
            age_seconds / 3600.0,
        )
    return True


def cleanup_stale_download_dirs(
    root_dir: str | Path,
    max_age_seconds: int = DEFAULT_STALE_DOWNLOAD_AGE_SECONDS,
    logger=None,
) -> list[Path]:
    """Remove stale .downloading directories under a root path."""
    root_path = Path(root_dir)
    if not root_path.exists() or not root_path.is_dir():
        return []

    removed: list[Path] = []
    for temp_dir in root_path.rglob(".downloading"):
        if cleanup_stale_download_dir(
            temp_dir,
            max_age_seconds=max_age_seconds,
            logger=logger,
        ):
            removed.append(temp_dir)

    return removed


__all__ = [
    "DEFAULT_STALE_DOWNLOAD_AGE_SECONDS",
    "cleanup_stale_download_dir",
    "cleanup_stale_download_dirs",
]