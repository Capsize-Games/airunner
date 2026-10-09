"""Detached signature verification for update manifests (P10).

A signed manifest is the exact manifest JSON bytes plus a sidecar
signature file (``<manifest>.sig``), a non-executable UTF-8 text
file with ``#``-comment metadata::

    # format: airunner-update-manifest/1
    # key_id: <key-id>
    # signature: <128 lowercase hex chars>

The signature is Ed25519 over the exact manifest bytes, verified
with the ``cryptography`` library. The format id differs from the
policy signature format (S04) so a signature minted for one can
never validate the other. No custom cryptography and no online key
lookup are performed.

Trust store: :data:`TRUSTED_UPDATE_KEYS` maps key IDs to raw 32-byte
Ed25519 public keys. Private signing keys never ship; the public
repo carries an empty store and trusted release provisioning
installs the production keys. Callers may pass an explicit trust
store for tests.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

MANIFEST_FORMAT_ID = "airunner-update-manifest/1"
SIGNATURE_SUFFIX = ".sig"

MAX_SIGNATURE_BYTES = 4096
ED25519_PUBLIC_KEY_BYTES = 32

_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HEX_SIG_RE = re.compile(r"^[0-9a-f]{128}$")
_META_RE = re.compile(r"^#\s*([a-z0-9_]+)\s*:\s*(\S+)\s*$")

# Bundled public-key trust store: key ID -> raw Ed25519 public key.
# Empty in the public repo; populated by trusted release provisioning.
TRUSTED_UPDATE_KEYS: dict[str, bytes] = {}


class UpdateSignatureError(ValueError):
    """An update manifest signature failed strict verification."""


def _meta_entry(line: str) -> tuple[str, str] | None:
    """Return ``(key, value)`` for a ``# key: value`` line, else None."""
    match = _META_RE.match(line.strip())
    if match is None:
        return None
    return match.group(1), match.group(2)


def _collect_meta(text: str) -> dict[str, str]:
    """Collect ``# key: value`` metadata strictly; reject content."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            raise UpdateSignatureError("malformed signature file")
        entry = _meta_entry(stripped) if stripped else None
        if entry is None:
            continue
        key, value = entry
        if key in meta:
            raise UpdateSignatureError(f"duplicate metadata: {key}")
        meta[key] = value
    return meta


def _signature_fields(meta: dict[str, str]) -> tuple[str, bytes]:
    """Validate required fields; return ``(key_id, signature)``."""
    if meta.get("format") != MANIFEST_FORMAT_ID:
        raise UpdateSignatureError("unsupported signature format")
    key_id = meta.get("key_id", "")
    if not _KEY_ID_RE.match(key_id):
        raise UpdateSignatureError("malformed key id")
    raw_sig = meta.get("signature", "").lower()
    if not _HEX_SIG_RE.match(raw_sig):
        raise UpdateSignatureError("malformed signature value")
    return key_id, bytes.fromhex(raw_sig)


def parse_signature_file(data: bytes) -> tuple[str, bytes]:
    """Parse sidecar ``data`` strictly; return ``(key_id, sig)``."""
    if len(data) > MAX_SIGNATURE_BYTES:
        raise UpdateSignatureError("signature exceeds size bound")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UpdateSignatureError("signature is not UTF-8") from exc
    return _signature_fields(_collect_meta(text))


def _ed25519_verify(public_key: bytes, sig: bytes, data: bytes) -> None:
    """Verify an Ed25519 ``sig``; raise on any failure."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
    except ImportError as exc:
        raise UpdateSignatureError(
            "cryptographic library unavailable"
        ) from exc
    try:
        key = Ed25519PublicKey.from_public_bytes(public_key)
    except ValueError as exc:
        raise UpdateSignatureError("malformed public key") from exc
    try:
        key.verify(sig, data)
    except InvalidSignature as exc:
        raise UpdateSignatureError("signature verification failed") from exc


def _trusted_key(store: Mapping[str, bytes], key_id: str) -> bytes:
    """Return the trusted key bytes for ``key_id`` or raise."""
    public_key = store.get(key_id)
    if public_key is None:
        raise UpdateSignatureError("unknown signing key id")
    if not isinstance(public_key, bytes):
        raise UpdateSignatureError("malformed trusted public key")
    if len(public_key) != ED25519_PUBLIC_KEY_BYTES:
        raise UpdateSignatureError("malformed trusted public key")
    return public_key


def verify_detached_signature(
    data: bytes,
    signature_data: bytes,
    *,
    trusted_keys: Mapping[str, bytes] | None = None,
) -> str:
    """Verify ``signature_data`` over exact ``data``; return key ID.

    ``trusted_keys`` defaults to :data:`TRUSTED_UPDATE_KEYS`.
    """
    store = TRUSTED_UPDATE_KEYS if trusted_keys is None else trusted_keys
    key_id, signature = parse_signature_file(signature_data)
    public_key = _trusted_key(store, key_id)
    _ed25519_verify(public_key, signature, data)
    return key_id
