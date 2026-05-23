"""Runtime-local filesystem validation helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable


_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class PathPolicyError(ValueError):
    """Raised when one runtime path violates local path policy."""


def normalize_local_path(path: str, *, label: str = "Path") -> str:
    """Return one normalized local filesystem path."""
    if not isinstance(path, str):
        raise PathPolicyError(f"{label} must be a string")
    value = path.strip()
    if not value:
        raise PathPolicyError(f"{label} is required")
    if "\x00" in value:
        raise PathPolicyError(f"{label} contains invalid characters")
    if _URI_SCHEME_RE.match(value):
        raise PathPolicyError(f"{label} must be a local filesystem path")
    resolved = Path(os.path.expandvars(value)).expanduser().resolve()
    return str(resolved)


def resolve_existing_file(
    path: str,
    *,
    label: str = "File",
    allowed_suffixes: Iterable[str] | None = None,
) -> str:
    """Return one validated existing file path."""
    candidate = Path(normalize_local_path(path, label=label))
    if not candidate.exists():
        raise PathPolicyError(f"{label} does not exist: {candidate}")
    if not candidate.is_file():
        raise PathPolicyError(f"{label} must be a file: {candidate}")
    if allowed_suffixes is None:
        return str(candidate)
    normalized_suffixes = {str(suffix).lower() for suffix in allowed_suffixes}
    if candidate.suffix.lower() in normalized_suffixes:
        return str(candidate)
    allowed = ", ".join(sorted(normalized_suffixes))
    raise PathPolicyError(f"{label} must use one of: {allowed}")


__all__ = [
    "PathPolicyError",
    "normalize_local_path",
    "resolve_existing_file",
]