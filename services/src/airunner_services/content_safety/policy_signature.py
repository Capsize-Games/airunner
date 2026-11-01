"""Detached signature verification for policy artifacts (S04).

A signed artifact is the exact ``policy_terms.dat`` bytes plus a
sidecar signature file (``<artifact>.sig``), a non-executable UTF-8
text file with ``#``-comment metadata::

    # format: airunner-policy-signature/1
    # key_id: <key-id>
    # signature: <128 lowercase hex chars>

The signature is Ed25519 over the exact artifact bytes (headers and
digests included), verified with the ``cryptography`` library. No
custom cryptography and no online key lookup are performed.

Trust store: ``data/policy_trust_store.json`` maps key IDs to lowercase
hex-encoded Ed25519 public keys. The public repo carries an empty store;
trusted release staging (S06) writes only the key that verified the
staged artifact. Packaged/production mode reads that resource and fails
closed when it is missing, malformed, empty, or does not match. Private
signing keys never ship. The low-level verifier accepts an explicit trust
mapping for release staging and isolated cryptographic tests; the packaged
policy loader does not accept a trust-store override.
"""

from __future__ import annotations

import importlib.resources
import json
import re
from collections.abc import Mapping
from pathlib import Path

SIGNATURE_FORMAT_ID = "airunner-policy-signature/1"
SIGNATURE_SUFFIX = ".sig"
SIGNATURE_VERSION = 1

MAX_SIGNATURE_BYTES = 4096
ED25519_PUBLIC_KEY_BYTES = 32
MAX_TRUST_STORE_BYTES = 64 * 1024
TRUST_STORE_FILENAME = "policy_trust_store.json"

_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HEX_SIG_RE = re.compile(r"^[0-9a-f]{128}$")
_HEX_PUBLIC_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
_META_RE = re.compile(r"^#\s*([a-z0-9_]+)\s*:\s*(\S+)\s*$")


def load_bundled_trusted_keys() -> dict[str, bytes]:
    """Load validated public keys from the packaged trust-store resource.

    The public checkout carries an empty JSON object. Release staging
    replaces it with only the public key whose ID verified the staged
    artifact. Missing, malformed, oversized, or empty resources produce
    an empty mapping so signature verification fails closed.
    """
    try:
        resource = (
            importlib.resources.files(__package__)
            .joinpath("data")
            .joinpath(TRUST_STORE_FILENAME)
        )
        if not resource.is_file():
            return {}
        raw = resource.read_bytes()
    except (OSError, ModuleNotFoundError, TypeError):
        return {}
    if not raw or len(raw) > MAX_TRUST_STORE_BYTES:
        return {}

    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        values: dict[str, object] = {}
        for key, value in pairs:
            if key in values:
                raise ValueError("duplicate trust-store key")
            values[key] = value
        return values

    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        return {}
    if not isinstance(payload, dict):
        return {}

    trusted: dict[str, bytes] = {}
    for key_id, encoded_key in payload.items():
        if (
            not isinstance(key_id, str)
            or not _KEY_ID_RE.fullmatch(key_id)
            or not isinstance(encoded_key, str)
            or not _HEX_PUBLIC_KEY_RE.fullmatch(encoded_key)
        ):
            return {}
        public_key = bytes.fromhex(encoded_key)
        if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
            return {}
        trusted[key_id] = public_key
    return trusted


# Import-time snapshot retained for introspection. Verification loads the
# resource at call time; packaged policy loading cannot override that store.
TRUSTED_KEYS: dict[str, bytes] = load_bundled_trusted_keys()


class PolicySignatureError(ValueError):
    """A policy artifact signature failed strict verification."""


def signature_path_for(artifact: Path) -> Path:
    """Return the sidecar signature path for ``artifact``."""
    return Path(str(artifact) + SIGNATURE_SUFFIX)


def _meta_entry(line: str) -> tuple[str, str] | None:
    """Return ``(key, value)`` for a ``# key: value`` line, else ``None``."""
    match = _META_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def _collect_signature_meta(text: str) -> dict[str, str]:
    """Collect ``# key: value`` metadata strictly; reject content lines."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            entry = _meta_entry(stripped) if stripped else None
            if entry is None:
                continue
            key, value = entry
            if key in meta:
                raise PolicySignatureError(f"duplicate metadata: {key}")
            meta[key] = value
        else:
            raise PolicySignatureError("malformed signature file")
    return meta


def _signature_fields(meta: dict[str, str]) -> tuple[str, bytes]:
    """Validate required fields; return ``(key_id, signature)``."""
    if meta.get("format") != SIGNATURE_FORMAT_ID:
        raise PolicySignatureError("unsupported signature format")
    key_id = meta.get("key_id", "")
    if not _KEY_ID_RE.match(key_id):
        raise PolicySignatureError("malformed key id")
    raw_sig = meta.get("signature", "").lower()
    if not _HEX_SIG_RE.match(raw_sig):
        raise PolicySignatureError("malformed signature value")
    return key_id, bytes.fromhex(raw_sig)


def parse_signature_file(data: bytes) -> tuple[str, bytes]:
    """Parse ``data`` strictly; return ``(key_id, signature)``.

    Raise :class:`PolicySignatureError` on oversize input, schema
    mismatch, duplicate or missing metadata, malformed fields, or
    any non-comment content line.
    """
    if len(data) > MAX_SIGNATURE_BYTES:
        raise PolicySignatureError("signature exceeds size bound")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PolicySignatureError("signature is not UTF-8") from exc
    return _signature_fields(_collect_signature_meta(text))


def _ed25519_verify(public_key: bytes, signature: bytes, data: bytes) -> None:
    """Verify an Ed25519 ``signature``; raise on any failure."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError as exc:
        raise PolicySignatureError(
            "cryptographic library unavailable"
        ) from exc
    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
    except ValueError as exc:
        raise PolicySignatureError("malformed public key") from exc
    try:
        key.verify(signature, data)
    except InvalidSignature as exc:
        raise PolicySignatureError("signature verification failed") from exc


def verify_policy_artifact(
    data: bytes,
    signature_data: bytes,
    *,
    trusted_keys: Mapping[str, bytes] | None = None,
) -> str:
    """Verify ``signature_data`` over exact ``data``; return the key ID.

    Raise :class:`PolicySignatureError` on missing/unknown key ID,
    malformed trust-store entry, or a signature that does not match
    the exact bytes. ``trusted_keys`` defaults to the packaged trust resource.
    """
    store = (
        load_bundled_trusted_keys()
        if trusted_keys is None
        else trusted_keys
    )
    key_id, signature = parse_signature_file(signature_data)
    public_key = store.get(key_id)
    if public_key is None:
        raise PolicySignatureError("unknown signing key id")
    if not isinstance(public_key, bytes):
        raise PolicySignatureError("malformed trusted public key")
    if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
        raise PolicySignatureError("malformed trusted public key")
    _ed25519_verify(public_key, signature, data)
    return key_id


def read_signature_bytes(artifact: Path) -> bytes | None:
    """Return the sidecar signature bytes, or ``None`` when unusable."""
    try:
        data = signature_path_for(artifact).read_bytes()
    except OSError:
        return None
    if len(data) > MAX_SIGNATURE_BYTES or not data:
        return None
    return data
