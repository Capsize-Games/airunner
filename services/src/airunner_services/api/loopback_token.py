"""Per-user loopback authentication token for the local daemon API.

The daemon no longer trusts every loopback request blindly. A random token is
generated on first use and persisted with file mode 0600. Both the daemon
(API server) and the GUI daemon client read the same file, so the GUI can
authenticate itself to the local daemon while a second local process without
the token receives 401 on non-admin endpoints.

If the token cannot be persisted (read-only HOME, container quirk, etc.) a
process-local random token is used and a warning is emitted; the API then
fails closed for any request that does not present that process's token.
"""

from __future__ import annotations

import logging
import os
import secrets
import stat
from pathlib import Path

from airunner_common.settings import AIRUNNER_BASE_PATH


logger = logging.getLogger(__name__)

_LOOPBACK_TOKEN_MODE = 0o600
_WEAK_PERMISSION_MASK = 0o077
_cached_token: str | None = None
_cache_loaded = False


def loopback_token_path() -> Path:
    """Return the on-disk path of the per-user loopback token."""
    return Path(AIRUNNER_BASE_PATH) / "config" / "loopback_token"


def _has_weak_permissions(path: Path) -> bool:
    """Return whether one token file is readable beyond its owner."""
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return bool(mode & _WEAK_PERMISSION_MASK)


def _tighten_permissions(path: Path) -> bool:
    """Tighten one token file to 0600, returning whether it is private now."""
    try:
        os.chmod(path, _LOOPBACK_TOKEN_MODE)
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return (mode & _WEAK_PERMISSION_MASK) == 0


def load_loopback_token() -> str | None:
    """Return the persisted token or None when it is missing or untrusted.

    A symlink is never followed: it is reported and ignored so the
    caller replaces it. A group/world-readable file is tightened to
    0600; when that fails the token is refused instead of silently
    keeping weak permissions.
    """
    path = loopback_token_path()
    try:
        if path.is_symlink():
            logger.warning(
                "Ignoring loopback token symlink at %s; it will be replaced.",
                path,
            )
            return None
        token = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not token:
        return None
    if _has_weak_permissions(path) and not _tighten_permissions(path):
        logger.warning(
            "Ignoring group/world-readable loopback token at %s; "
            "permissions could not be tightened to 0600.",
            path,
        )
        return None
    return token


def get_or_create_loopback_token() -> str:
    """Return the per-user loopback token, creating it on first run."""
    global _cached_token, _cache_loaded  # noqa: PLW0603

    if _cache_loaded and _cached_token:
        return _cached_token

    path = loopback_token_path()
    try:
        if path.is_symlink():
            logger.warning(
                "Replacing loopback token symlink at %s with a new "
                "0600 token file.",
                path,
            )
            path.unlink()
        token = load_loopback_token()
        if not token:
            path.parent.mkdir(parents=True, exist_ok=True)
            token = secrets.token_urlsafe(32)
            nofollow = getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC | nofollow,
                _LOOPBACK_TOKEN_MODE,
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(token + "\n")
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            try:
                os.chmod(path, _LOOPBACK_TOKEN_MODE)
            except OSError:
                logger.warning(
                    "Unable to chmod loopback token file %s to 0600; "
                    "discarding it and using a process-local token.",
                    path,
                )
                try:
                    path.unlink()
                except OSError:
                    pass
                raise
        _cached_token = token
        _cache_loaded = True
        return token
    except OSError as exc:
        logger.warning(
            "Unable to persist loopback token to %s (%s); using a "
            "process-local token. The API will fail closed for any "
            "process that cannot read this token.",
            path,
            exc,
        )
        _cached_token = secrets.token_urlsafe(32)
        _cache_loaded = True
        return _cached_token


__all__ = [
    "get_or_create_loopback_token",
    "load_loopback_token",
    "loopback_token_path",
]
