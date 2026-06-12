"""Storage mode seam — local filesystem (dev) vs object storage (prod).

Development uses the local filesystem: directory watchers register
documents/images found on disk into the database, and assets are read
straight from ``AIRUNNER_BASE_PATH``.

Production replaces this with object storage (S3) and user uploads. The
storage extension calls :func:`set_filesystem_ingestion(False)` at load
time, which:

* disables the directory watchers (documents / models / images), and
* disables the on-request filesystem sync that registers local files.

Records (Document rows, image paths) are then created only through
authenticated upload endpoints, scoped to the caller's tenant.

This module is intentionally dependency-free so it can be imported from
any layer (routes, watchers, workers) without circular imports.
"""

from __future__ import annotations

import os

# Set by the storage extension at load time. None → fall back to env.
_filesystem_ingestion_override: bool | None = None


def set_filesystem_ingestion(enabled: bool) -> None:
    """Override whether filesystem ingestion (watchers + sync) is active.

    Called by the production storage extension to switch the app to
    upload-only / object-storage mode.
    """
    global _filesystem_ingestion_override
    _filesystem_ingestion_override = bool(enabled)


def reset_filesystem_ingestion() -> None:
    """Clear any override and fall back to environment configuration."""
    global _filesystem_ingestion_override
    _filesystem_ingestion_override = None


def filesystem_ingestion_enabled() -> bool:
    """Return whether the app should read/register assets from local disk.

    True for local dev (default). False when the storage extension or the
    ``AIRUNNER_DISABLE_FS_INGESTION`` env var disables it.
    """
    if _filesystem_ingestion_override is not None:
        return _filesystem_ingestion_override
    env = (os.environ.get("AIRUNNER_DISABLE_FS_INGESTION") or "").strip().lower()
    return env not in {"1", "true", "yes", "on"}


__all__ = [
    "filesystem_ingestion_enabled",
    "reset_filesystem_ingestion",
    "set_filesystem_ingestion",
]
