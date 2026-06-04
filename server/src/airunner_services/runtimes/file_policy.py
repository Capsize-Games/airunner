"""Shared local filesystem validation helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Sequence


_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")


class PathPolicyError(ValueError):
    """Raised when one runtime path violates local path policy."""


def _coerce_path_text(path: str, label: str) -> str:
    """Return one validated text path value."""
    if not isinstance(path, str):
        raise PathPolicyError(f"{label} must be a string")
    value = path.strip()
    if not value:
        raise PathPolicyError(f"{label} is required")
    if "\x00" in value:
        raise PathPolicyError(f"{label} contains invalid characters")
    return value


def normalize_local_path(path: str, *, label: str = "Path") -> str:
    """Return one normalized local filesystem path."""
    value = _coerce_path_text(path, label)
    if _URI_SCHEME_RE.match(value):
        raise PathPolicyError(f"{label} must be a local filesystem path")
    resolved = Path(os.path.expandvars(value)).expanduser().resolve()
    return str(resolved)


def _normalized_suffixes(
    allowed_suffixes: Iterable[str] | None,
) -> set[str]:
    """Return one normalized suffix allow-list."""
    if allowed_suffixes is None:
        return set()
    return {str(suffix).lower() for suffix in allowed_suffixes}


def _validate_suffix(
    candidate: Path,
    allowed_suffixes: Iterable[str] | None,
    *,
    label: str,
) -> None:
    """Validate one file suffix against an optional allow-list."""
    suffixes = _normalized_suffixes(allowed_suffixes)
    if not suffixes:
        return
    if candidate.suffix.lower() in suffixes:
        return
    allowed = ", ".join(sorted(suffixes))
    raise PathPolicyError(f"{label} must use one of: {allowed}")


def _path_within_root(candidate: Path, root: Path) -> bool:
    """Return whether one candidate path is inside one root path."""
    try:
        return candidate.is_relative_to(root)
    except AttributeError:
        common_path = os.path.commonpath([str(candidate), str(root)])
        return common_path == str(root)


def _validate_roots(
    candidate: Path,
    allowed_roots: Sequence[str] | None,
    *,
    label: str,
) -> None:
    """Validate one path against the configured root allow-list."""
    if not allowed_roots:
        return
    normalized_roots = [
        Path(normalize_local_path(root, label=f"{label} root"))
        for root in allowed_roots
        if root
    ]
    if any(_path_within_root(candidate, root) for root in normalized_roots):
        return
    raise PathPolicyError(f"{label} must be inside an approved directory")


def resolve_existing_file(
    path: str,
    *,
    label: str = "File",
    allowed_suffixes: Iterable[str] | None = None,
    allowed_roots: Sequence[str] | None = None,
) -> str:
    """Return one validated existing file path."""
    candidate = Path(normalize_local_path(path, label=label))
    if not candidate.exists():
        raise PathPolicyError(f"{label} does not exist: {candidate}")
    if not candidate.is_file():
        raise PathPolicyError(f"{label} must be a file: {candidate}")
    _validate_suffix(candidate, allowed_suffixes, label=label)
    _validate_roots(candidate, allowed_roots, label=label)
    return str(candidate)


def resolve_existing_directory(
    path: str,
    *,
    label: str = "Directory",
    allowed_roots: Sequence[str] | None = None,
) -> str:
    """Return one validated existing directory path."""
    candidate = Path(normalize_local_path(path, label=label))
    if not candidate.exists():
        raise PathPolicyError(f"{label} does not exist: {candidate}")
    if not candidate.is_dir():
        raise PathPolicyError(f"{label} must be a directory: {candidate}")
    _validate_roots(candidate, allowed_roots, label=label)
    return str(candidate)


__all__ = [
    "PathPolicyError",
    "normalize_local_path",
    "resolve_existing_directory",
    "resolve_existing_file",
]