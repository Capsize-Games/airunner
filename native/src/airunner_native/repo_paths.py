"""Repository path helpers for native-owned source tooling."""

from __future__ import annotations

from pathlib import Path


def resolve_services_source_root(repo_root: Path) -> Path:
    """Return the services package source root for this checkout."""
    return repo_root / "services" / "src"


def resolve_native_source_root(repo_root: Path) -> Path:
    """Return the native package source root for this checkout."""
    return repo_root / "native" / "src"


def resolve_repo_root(anchor: Path | None = None) -> Path:
    """Return the AIRunner repository root for one source file."""
    start = (anchor or Path(__file__)).resolve()
    for candidate in start.parents:
        if _looks_like_repo_root(candidate):
            return candidate
    raise FileNotFoundError("Unable to resolve the AIRunner repository root")


def _looks_like_repo_root(candidate: Path) -> bool:
    """Return True when one directory looks like the repo root."""
    return (
        (candidate / "pyproject.toml").is_file()
        and (candidate / "services").is_dir()
        and (candidate / "native").is_dir()
    )


__all__ = [
    "resolve_services_source_root",
    "resolve_native_source_root",
    "resolve_repo_root",
]
