"""Loads the hashed content-safety policy data and reports availability.

Versioned artifact schema (``airunner-policy-data/1``): non-executable
UTF-8 text with ``#``-comment integrity metadata plus sorted digests::

    # format: airunner-policy-data/1
    # normalization: v1
    # count: 3
    # sha256: <hex SHA-256 of the canonical digest block>
    <64 lowercase hex chars>  (repeated, sorted, unique)

``format`` is the compatibility version; ``normalization`` must match the
matcher's ``NORMALIZATION_VERSION``; ``count`` is the digest-line count;
``sha256`` covers the canonical block (sorted unique digests joined with
newlines, trailing newline; empty when there are none). Other ``#`` lines
and blanks are ignored; unknown metadata keys are ignored. Files without
a ``format`` line take the legacy path (malformed lines skipped).
Artifacts over ``MAX_ARTIFACT_BYTES`` / ``MAX_DIGESTS``, or versioned
lines over ``MAX_LINE_LENGTH``, are rejected.

Resolution: ``AIRUNNER_CONTENT_SAFETY_DATA`` first, then the packaged
``data/policy_terms.dat``. Unusable data yields an empty set plus one
content-free warning; :func:`parse_policy_artifact` raises instead.

Pass ``verify_signature=True`` to :func:`load_policy_hashes` to verify
a detached Ed25519 sidecar (``<artifact>.sig``) over the exact
artifact bytes before decoding or parsing (see
:mod:`airunner_services.content_safety.policy_signature`). Any
verification failure fails closed to the empty set; the selected
source is never bypassed by falling back to the other one.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import logging
import os
import re
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path

from .policy_signature import (
    MAX_SIGNATURE_BYTES,
    PolicySignatureError,
    read_signature_bytes,
    verify_policy_artifact,
)

logger = logging.getLogger(__name__)

POLICY_DATA_ENV_VAR = "AIRUNNER_CONTENT_SAFETY_DATA"
POLICY_DATA_PACKAGE = "airunner_services.content_safety"
POLICY_DATA_FILENAME = "data/policy_terms.dat"

ARTIFACT_VERSION = 1
ARTIFACT_FORMAT_ID = "airunner-policy-data/1"
# Must match matcher.NORMALIZATION_VERSION (duplicated to avoid a cycle).
NORMALIZATION_VERSION = "v1"

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_DIGESTS = 1_000_000
MAX_LINE_LENGTH = 256

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_META_RE = re.compile(r"^#\s*([a-z0-9_]+)\s*:\s*(\S+)\s*$")

_cache: frozenset[str] | None = None
_warned_empty = False


class PolicyDataError(ValueError):
    """A versioned policy artifact failed strict validation."""


def canonical_digest_block(digests: Iterable[str]) -> str:
    """Return the canonical digest block: sorted unique digests, folded."""
    return "".join(
        f"{digest}\n"
        for digest in sorted({item.strip().lower() for item in digests})
    )


def digest_block_sha256(digests: Iterable[str]) -> str:
    """Return the hex SHA-256 of the canonical digest block."""
    return hashlib.sha256(
        canonical_digest_block(digests).encode("utf-8")
    ).hexdigest()


def _warn_zero(detail: str) -> None:
    """Log a content-free warning that no hashes were loaded."""
    logger.warning(f"Content safety policy data {detail}; 0 hashes loaded")


def _bounded(data: bytes) -> bytes | None:
    """Return ``data`` within the size bound, else warn and return ``None``."""
    if len(data) > MAX_ARTIFACT_BYTES:
        _warn_zero("exceeds size bound")
        return None
    return data


def _read_env_bytes() -> bytes | None:
    """Return the env-var data file bytes, or ``None`` when unusable."""
    raw_path = os.environ.get(POLICY_DATA_ENV_VAR)
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_file():
        _warn_zero("path does not exist")
        return None
    try:
        return _bounded(path.read_bytes())
    except OSError:
        _warn_zero("could not be read")
        return None


def _read_packaged_bytes() -> bytes | None:
    """Return the packaged data file bytes, or ``None`` when unusable."""
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
        return _bounded(resource.read_bytes())
    except OSError:
        _warn_zero("could not be read")
        return None


def _read_env_signature() -> bytes | None:
    """Return the env-var artifact's sidecar bytes, else ``None``."""
    raw_path = os.environ.get(POLICY_DATA_ENV_VAR)
    if not raw_path:
        return None
    return read_signature_bytes(Path(raw_path))


def _read_packaged_signature() -> bytes | None:
    """Return the packaged sidecar bytes, or ``None`` when unusable."""
    try:
        resource = (
            importlib.resources.files(POLICY_DATA_PACKAGE)
            .joinpath("data")
            .joinpath("policy_terms.dat.sig")
        )
    except (ModuleNotFoundError, TypeError):
        return None
    try:
        if not resource.is_file():
            return None
        data = resource.read_bytes()
    except OSError:
        return None
    if not data or len(data) > MAX_SIGNATURE_BYTES:
        return None
    return data


def _verified_text(
    data: bytes,
    signature: bytes | None,
    trusted_keys: Mapping[str, bytes] | None,
) -> str | None:
    """Verify ``signature`` over ``data``, then decode; else ``None``."""
    if signature is None:
        _warn_zero("signature is missing")
        return None
    try:
        verify_policy_artifact(
            data, signature, trusted_keys=trusted_keys
        )
    except PolicySignatureError:
        _warn_zero("signature verification failed")
        return None
    return _decode(data)


def _load_verified_text(
    trusted_keys: Mapping[str, bytes] | None,
) -> str | None:
    """Return verified artifact text; fail closed without fallback."""
    data = _read_env_bytes()
    if data is not None:
        return _verified_text(
            data, _read_env_signature(), trusted_keys
        )
    data = _read_packaged_bytes()
    if data is not None:
        return _verified_text(
            data, _read_packaged_signature(), trusted_keys
        )
    return None


def _meta_entry(line: str) -> tuple[str, str] | None:
    """Return ``(key, value)`` for a ``# key: value`` line, else ``None``."""
    match = _META_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def _content_lines(lines: list[str]) -> Iterator[str]:
    """Yield stripped non-blank, non-comment lines."""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            yield stripped


def _parse_legacy(lines: list[str]) -> frozenset[str]:
    """Parse unversioned digest lines, skipping anything malformed."""
    hashes: set[str] = set()
    for raw in _content_lines(lines):
        candidate = raw.lower()
        if len(candidate) <= MAX_LINE_LENGTH and _HASH_RE.match(candidate):
            hashes.add(candidate)
        if len(hashes) > MAX_DIGESTS:
            raise PolicyDataError("digest count exceeds bound")
    return frozenset(hashes)


def _collect_versioned_digests(lines: list[str]) -> list[str]:
    """Collect digest lines strictly; reject malformed or over-long lines."""
    digests: list[str] = []
    for raw in _content_lines(lines):
        candidate = raw.lower()
        if len(candidate) > MAX_LINE_LENGTH:
            raise PolicyDataError("line exceeds length bound")
        if not _HASH_RE.match(candidate):
            raise PolicyDataError("malformed digest line")
        digests.append(candidate)
    return digests


def _parse_versioned(lines: list[str], meta: dict[str, str]) -> frozenset[str]:
    """Strictly validate a versioned artifact and return its digests."""
    if meta.get("format") != ARTIFACT_FORMAT_ID:
        raise PolicyDataError("unsupported artifact format")
    if meta.get("normalization") != NORMALIZATION_VERSION:
        raise PolicyDataError("unsupported normalization version")
    raw_count = meta.get("count", "")
    if not raw_count.isdigit():
        raise PolicyDataError("malformed digest count")
    digests = _collect_versioned_digests(lines)
    count = int(raw_count)
    if count > MAX_DIGESTS or count != len(digests):
        raise PolicyDataError("digest count mismatch")
    if len(set(digests)) != len(digests) or digests != sorted(digests):
        raise PolicyDataError("digests must be sorted and unique")
    if digest_block_sha256(digests) != meta.get("sha256", "").lower():
        raise PolicyDataError("digest integrity mismatch")
    return frozenset(digests)


def parse_policy_artifact(text: str) -> frozenset[str]:
    """Parse artifact ``text`` strictly; raise :class:`PolicyDataError`."""
    if len(text) > MAX_ARTIFACT_BYTES:
        raise PolicyDataError("artifact exceeds size bound")
    lines = text.splitlines()
    meta: dict[str, str] = {}
    for line in lines:
        entry = _meta_entry(line)
        if entry is None:
            continue
        key, value = entry
        if key in meta:
            raise PolicyDataError(f"duplicate metadata: {key}")
        meta[key] = value
    if "format" not in meta:
        return _parse_legacy(lines)
    return _parse_versioned(lines, meta)


def _decode(data: bytes | None) -> str | None:
    """Decode artifact bytes, warning content-free on failure."""
    if data is None:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        _warn_zero("could not be read")
        return None


def load_policy_hashes(
    *,
    refresh: bool = False,
    verify_signature: bool = False,
    trusted_keys: Mapping[str, bytes] | None = None,
) -> frozenset[str]:
    """Return the cached policy hash set; unusable data yields empty.

    With ``verify_signature``, the sidecar signature is verified
    over the exact artifact bytes before decoding or parsing, and
    any failure fails closed to the empty set. ``trusted_keys``
    overrides the bundled store (test hook); ``None`` uses it.
    """
    global _cache, _warned_empty
    if _cache is not None and not refresh:
        return _cache
    if verify_signature:
        text = _load_verified_text(trusted_keys)
    else:
        text = _decode(_read_env_bytes())
        if text is None:
            text = _decode(_read_packaged_bytes())
    try:
        _cache = parse_policy_artifact(text) if text else frozenset()
    except PolicyDataError:
        _cache = frozenset()
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
