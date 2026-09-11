"""Loads the hashed content-safety policy data and reports availability.

The policy data file is a UTF-8 text file with one lowercase hex SHA-256
digest per line. Blank lines and lines starting with ``#`` are ignored, as
are malformed lines (this never raises). The file is generated out of band
by ``scripts/build_policy_terms.py`` from a plaintext list the maintainer
keeps outside the repository; the public repository ships an empty set.

Resolution order:

1. ``AIRUNNER_CONTENT_SAFETY_DATA`` env var, when set (a path to a data
   file, absolute or relative).
2. The file packaged inside this module at ``data/policy_terms.dat``.

A missing, empty, or all-malformed data set is not an error: it yields an
empty set, logs a single content-free warning, and makes
:func:`is_available` return ``False`` so callers can fail open while the
application remains usable. No line content is ever logged.
"""

from __future__ import annotations

import importlib.resources
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

POLICY_DATA_ENV_VAR = "AIRUNNER_CONTENT_SAFETY_DATA"
POLICY_DATA_PACKAGE = "airunner_services.content_safety"
POLICY_DATA_FILENAME = "data/policy_terms.dat"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

_cache: frozenset[str] | None = None
_warned_empty = False


def _read_env_data() -> str | None:
    """Return the text of the env-var data file, or ``None`` when absent."""
    raw_path = os.environ.get(POLICY_DATA_ENV_VAR)
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_file():
        logger.warning(
            "Content safety policy data path does not exist; 0 hashes loaded"
        )
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning(
            "Content safety policy data could not be read; 0 hashes loaded"
        )
        return None


def _read_packaged_data() -> str | None:
    """Return the text of the packaged data file, or ``None`` when absent."""
    try:
        resource = (
            importlib.resources.files(POLICY_DATA_PACKAGE)
            .joinpath("data")
            .joinpath("policy_terms.dat")
        )
    except (ModuleNotFoundError, TypeError):
        return None
    try:
        if not resource.is_file():
            return None
        return resource.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning(
            "Content safety policy data could not be read; 0 hashes loaded"
        )
        return None


def _parse_hashes(text: str) -> frozenset[str]:
    """Parse hash lines, skipping blanks, comments and malformed lines."""
    hashes: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate = stripped.lower()
        if _HASH_RE.match(candidate):
            hashes.add(candidate)
        # Malformed lines are ignored; a corrupt file must not crash checks.
    return frozenset(hashes)


def load_policy_hashes(*, refresh: bool = False) -> frozenset[str]:
    """Return the loaded policy hash set (cached in a module-level frozenset).

    A missing, empty, or all-malformed data set yields an empty frozenset
    and logs a single content-free warning. Pass ``refresh=True`` to bypass
    the cache.
    """
    global _cache, _warned_empty
    if _cache is not None and not refresh:
        return _cache
    text = _read_env_data()
    if text is None:
        text = _read_packaged_data()
    _cache = _parse_hashes(text) if text else frozenset()
    if not _cache and not _warned_empty:
        _warned_empty = True
        logger.warning(
            "Content safety policy data unavailable or empty; 0 hashes "
            "loaded; checks pass until a policy set is generated"
        )
    return _cache


def is_available() -> bool:
    """Return ``True`` when a non-empty policy data set is loaded."""
    return bool(load_policy_hashes())


def reset_cache() -> None:
    """Clear the cached hash set and warning latch (test hook)."""
    global _cache, _warned_empty
    _cache = None
    _warned_empty = False
