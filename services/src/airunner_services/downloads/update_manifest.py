"""Update manifest schema and artifact digests (release P10).

Manifest schema (v1, strict)::

    {"format": "airunner-update-manifest/1",
     "version": "1.2.4",
     "artifacts": [{"name": "bundle-1.2.4.tar.gz",
                    "size": 1234,
                    "sha256": "<64 lowercase hex>"}]}

Version ``1`` carries exactly one bundle tarball artifact.
Signatures are verified by :mod:`update_signature` before the
schema is parsed; every failure surfaces as
:class:`UpdateManifestError`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeGuard

from airunner_services.downloads.update_signature import (
    MANIFEST_FORMAT_ID,
    TRUSTED_UPDATE_KEYS,
    UpdateSignatureError,
    verify_detached_signature,
)

BUNDLE_SUFFIX = ".tar.gz"

MAX_MANIFEST_BYTES = 65536
MAX_ARTIFACT_BYTES = 8 * 1024**3

_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


class UpdateManifestError(ValueError):
    """An update manifest or artifact failed strict verification."""


@dataclass(frozen=True)
class ManifestArtifact:
    """One bundle artifact named by a verified manifest."""

    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class UpdateManifest:
    """A verified update manifest; v1 holds one bundle artifact."""

    version: str
    artifacts: tuple[ManifestArtifact, ...]


def _strict_keys(payload: object, label: str) -> dict[str, object]:
    """Return ``payload`` as a str-keyed dict or raise."""
    if not isinstance(payload, dict):
        raise UpdateManifestError(f"{label} is not an object")
    for key in payload:
        if not isinstance(key, str):
            raise UpdateManifestError(f"{label} has a non-string key")
    return payload


def _valid_artifact_name(name: object) -> TypeGuard[str]:
    """Return whether ``name`` is a safe v1 bundle tarball name."""
    return (
        isinstance(name, str)
        and 0 < len(name) <= 128
        and name.endswith(BUNDLE_SUFFIX)
        and "/" not in name
        and "\\" not in name
        and ".." not in name
    )


def _valid_version(version: object) -> TypeGuard[str]:
    """Mirror ``valid_version`` from packaging/linux/release-lib.sh."""
    return (
        isinstance(version, str)
        and version not in ("", "current", ".", "..")
        and _VERSION_RE.match(version) is not None
    )


def _artifact_from_json(index: int, payload: object) -> ManifestArtifact:
    """Validate one artifact entry; raise on schema mismatch."""
    entry = _strict_keys(payload, f"artifacts[{index}]")
    if set(entry) != {"name", "size", "sha256"}:
        raise UpdateManifestError(f"artifacts[{index}] schema mismatch")
    name, size, sha256 = entry["name"], entry["size"], entry["sha256"]
    if not _valid_artifact_name(name):
        raise UpdateManifestError(f"artifacts[{index}] bad name")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or not 1 <= size <= MAX_ARTIFACT_BYTES
    ):
        raise UpdateManifestError(f"artifacts[{index}] bad size")
    if not isinstance(sha256, str) or not _HEX_DIGEST_RE.match(sha256):
        raise UpdateManifestError(f"artifacts[{index}] bad sha256")
    return ManifestArtifact(name=name, size=size, sha256=sha256)


def parse_manifest(data: bytes) -> UpdateManifest:
    """Parse and schema-check manifest ``data`` without verifying."""
    if len(data) > MAX_MANIFEST_BYTES:
        raise UpdateManifestError("manifest exceeds size bound")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise UpdateManifestError("manifest is not JSON") from exc
    root = _strict_keys(payload, "manifest")
    if set(root) != {"format", "version", "artifacts"}:
        raise UpdateManifestError("manifest schema mismatch")
    if root["format"] != MANIFEST_FORMAT_ID:
        raise UpdateManifestError("unsupported manifest format")
    if not _valid_version(root["version"]):
        raise UpdateManifestError("manifest has a bad version")
    raw_items = root["artifacts"]
    if not isinstance(raw_items, list) or len(raw_items) != 1:
        raise UpdateManifestError("v1 manifest holds one artifact")
    artifact = _artifact_from_json(0, raw_items[0])
    return UpdateManifest(version=root["version"], artifacts=(artifact,))


def verify_manifest(
    data: bytes,
    signature_data: bytes,
    *,
    trusted_keys: Mapping[str, bytes] | None = None,
) -> UpdateManifest:
    """Verify the signature over exact ``data``; parse on success.

    Every signature or schema failure raises
    :class:`UpdateManifestError`. ``trusted_keys`` defaults to the
    bundled :data:`TRUSTED_UPDATE_KEYS` store.
    """
    store = TRUSTED_UPDATE_KEYS if trusted_keys is None else trusted_keys
    try:
        verify_detached_signature(data, signature_data, trusted_keys=store)
    except UpdateSignatureError as exc:
        raise UpdateManifestError(str(exc)) from exc
    return parse_manifest(data)


def match_artifact(size: int, sha256: str, artifact: ManifestArtifact) -> None:
    """Raise unless ``size``/``sha256`` equal the manifest claim."""
    if size != artifact.size:
        raise UpdateManifestError(
            f"artifact size mismatch: got {size}, want {artifact.size}"
        )
    if sha256 != artifact.sha256:
        raise UpdateManifestError("artifact digest mismatch")


def verify_artifact_bytes(data: bytes, artifact: ManifestArtifact) -> None:
    """Raise unless ``data`` matches the manifest size and digest."""
    match_artifact(len(data), hashlib.sha256(data).hexdigest(), artifact)
