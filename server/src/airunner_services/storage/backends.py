"""Pluggable storage backend abstraction.

Separates *where bytes live* (local filesystem in dev, object storage such
as S3 in prod) from *which tenant owns a record* (the per-tenant DB row).
Core code reads/writes assets through :func:`get_storage_backend`; the
production storage extension swaps in an S3 backend via
:func:`set_storage_backend` without touching call sites.

Keys are tenant-prefixed (see :func:`tenant_storage_key`) so every tenant's
objects are isolated under ``tenants/<schema>/...`` regardless of backend.
"""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageBackend(ABC):
    """Abstract object store: bytes in, bytes out, addressed by string key."""

    @abstractmethod
    def save(
        self,
        key: str,
        data: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> str:
        """Persist ``data`` under ``key`` and return the stored key."""

    @abstractmethod
    def open(self, key: str) -> bytes:
        """Return the bytes stored under ``key`` (raises if missing)."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an object exists at ``key``."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the object at ``key`` (no-op if missing)."""

    def url(self, key: str, *, expires: int = 3600) -> Optional[str]:
        """Return a fetchable URL for ``key`` if the backend supports one.

        Local storage returns ``None`` (bytes are served by the app);
        object stores return a presigned URL.
        """
        return None

    def local_path(self, key: str) -> Optional[str]:
        """Return an on-disk path for ``key`` if one exists, else ``None``.

        Lets callers that genuinely need a filesystem path (e.g. legacy
        document loaders) opt into a fast path on local storage while
        object-store backends fall back to ``open()``.
        """
        return None


class LocalStorageBackend(StorageBackend):
    """Filesystem-backed store rooted at a base directory.

    Keys are POSIX-style relative paths resolved under ``root``; absolute
    keys (legacy ``Document.path`` values that already hold a full path) are
    honored as-is so existing local data keeps working.
    """

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _resolve(self, key: str) -> Path:
        candidate = Path(key)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self._root / key).resolve()
        # Prevent traversal outside the root for relative keys.
        if not candidate.is_absolute():
            root_str = str(self._root)
            if not str(resolved).startswith(root_str):
                raise ValueError(f"Key escapes storage root: {key!r}")
        return resolved

    def save(
        self,
        key: str,
        data: bytes,
        *,
        content_type: Optional[str] = None,
    ) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return key

    def open(self, key: str) -> bytes:
        with open(self._resolve(key), "rb") as fh:
            return fh.read()

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).is_file()
        except ValueError:
            return False

    def delete(self, key: str) -> None:
        try:
            path = self._resolve(key)
        except ValueError:
            return
        if path.is_file():
            path.unlink()

    def local_path(self, key: str) -> Optional[str]:
        try:
            path = self._resolve(key)
        except ValueError:
            return None
        return str(path) if path.is_file() else None

    @staticmethod
    def copy_into(src_path: str, dst: Path) -> None:
        """Copy an external file into the store (helper for migrations)."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst)


# ── Registry ──────────────────────────────────────────────────────────────

_backend: Optional[StorageBackend] = None


def get_storage_backend() -> StorageBackend:
    """Return the active storage backend (local filesystem by default)."""
    global _backend
    if _backend is None:
        from airunner_services.settings import AIRUNNER_BASE_PATH

        root = AIRUNNER_BASE_PATH or os.path.expanduser("~/.local/share/airunner")
        _backend = LocalStorageBackend(root)
    return _backend


def set_storage_backend(backend: StorageBackend) -> None:
    """Replace the active storage backend (used by the storage extension)."""
    global _backend
    _backend = backend


def reset_storage_backend() -> None:
    """Clear the active backend so the default is rebuilt on next use."""
    global _backend
    _backend = None


# ── Tenant-scoped keys ──────────────────────────────────────────────────────

_SAFE_FALLBACK_SCHEMA = "tenant_anonymous"


def tenant_storage_key(*parts: str) -> str:
    """Build a tenant-prefixed object key: ``tenants/<schema>/<parts...>``.

    Uses the active tenant context, so callers in an authenticated request
    automatically scope objects to the right tenant.
    """
    from airunner_services.data.tenant import (
        get_tenant_key,
        tenant_schema_for_key,
    )

    schema = tenant_schema_for_key(get_tenant_key()) or _SAFE_FALLBACK_SCHEMA
    cleaned = [p.strip("/") for p in parts if p and p.strip("/")]
    return "/".join(["tenants", schema, *cleaned])


__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "get_storage_backend",
    "reset_storage_backend",
    "set_storage_backend",
    "tenant_storage_key",
]
