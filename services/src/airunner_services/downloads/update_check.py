"""Explicit opt-in update check with verified download (P10).

Stage 1, :func:`check_for_updates`, fetches and verifies the signed
update manifest. It requires ``opt_in=True`` and refuses while
offline. Stage 2, :func:`download_update`, streams the bundle
artifact, enforcing the manifest size/digest and honoring
cancellation. Stage 3 (install handoff) lives in
:mod:`update_install` and runs only on a :class:`VerifiedUpdate`.

Network failure or cancellation at any stage raises without
altering the current install. Nothing runs at import or startup.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from airunner_services.downloads.update_manifest import (
    ManifestArtifact,
    UpdateManifest,
    UpdateManifestError,
    match_artifact,
    verify_manifest,
)

OFFLINE_ENV_VAR = "AIRUNNER_OFFLINE_MODE"


class UpdateCheckError(ValueError):
    """An update check, download, or install handoff failed."""


class UpdateOptInRequired(UpdateCheckError):
    """An update check was attempted without explicit opt-in."""


class UpdateOffline(UpdateCheckError):
    """An update check was denied while offline mode is on."""


class UpdateNetworkError(UpdateCheckError):
    """A transport fetch failed, stalled, or yielded bad chunks."""


class UpdateCancelled(UpdateCheckError):
    """An update download was cancelled before completing."""


class UpdateTransport(Protocol):
    """Byte source behind the update check.

    Production wiring (out of scope for P10) enforces URL policy
    here; tests inject synthetic fixtures. ``fetch_artifact``
    yields the artifact bytes in order, exactly once.
    """

    def fetch_manifest(self) -> tuple[bytes, bytes]:
        """Return ``(manifest_bytes, signature_bytes)``."""
        ...

    def fetch_artifact(self, name: str) -> Iterator[bytes]:
        """Yield artifact ``name`` in order, exactly once."""
        ...


@dataclass(frozen=True)
class UpdateAvailable:
    """A verified offer for a version newer than the current one."""

    version: str
    manifest: UpdateManifest
    transport: UpdateTransport


@dataclass(frozen=True)
class VerifiedUpdate:
    """A staged artifact whose size and digest verified."""

    version: str
    artifact: ManifestArtifact
    path: Path


def is_offline() -> bool:
    """Return whether offline mode denies the update check.

    Mirrors ``airunner_common.settings`` semantics (offline-first:
    only an explicit ``AIRUNNER_OFFLINE_MODE=0`` allows egress)
    without importing that heavy surface here. Read at call time
    so tests can flip it without reimporting this module.
    """
    return os.environ.get(OFFLINE_ENV_VAR, "1") == "1"


def _fetch_manifest(transport: UpdateTransport) -> tuple[bytes, bytes]:
    """Fetch the manifest bundle; wrap transport failures."""
    try:
        return transport.fetch_manifest()
    except UpdateCheckError:
        raise
    except Exception as exc:
        raise UpdateNetworkError(f"manifest fetch failed: {exc}") from exc


def _offer_for(
    manifest: UpdateManifest,
    transport: UpdateTransport,
    current_version: str,
) -> UpdateAvailable | None:
    """Return the update offer, or ``None`` when current."""
    if manifest.version == current_version:
        return None
    return UpdateAvailable(
        version=manifest.version,
        manifest=manifest,
        transport=transport,
    )


def check_for_updates(
    transport: UpdateTransport,
    current_version: str,
    *,
    opt_in: bool,
    trusted_keys: Mapping[str, bytes] | None = None,
) -> UpdateAvailable | None:
    """Fetch and verify the manifest; return the offer, if any.

    Raise unless opted in; refuse while offline; ``None`` if current.
    """
    if not opt_in:
        raise UpdateOptInRequired("update check needs opt-in")
    if is_offline():
        raise UpdateOffline("update check denied while offline")
    manifest_bytes, signature = _fetch_manifest(transport)
    manifest = verify_manifest(
        manifest_bytes, signature, trusted_keys=trusted_keys
    )
    return _offer_for(manifest, transport, current_version)


def _stage_paths(
    staging_dir: str | Path, artifact: ManifestArtifact
) -> tuple[Path, Path]:
    """Create the staging dir; return ``(staging, part)`` paths."""
    staging = Path(staging_dir)
    staging.mkdir(parents=True, exist_ok=True)
    return staging, staging / (artifact.name + ".part")


def _download_part(
    transport: UpdateTransport,
    artifact: ManifestArtifact,
    part: Path,
    cancel: Callable[[], bool] | None,
) -> None:
    """Stream and verify; remove the partial file on any failure."""
    try:
        size, hexdigest = _stream_to_file(transport, artifact, part, cancel)
        match_artifact(size, hexdigest, artifact)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def download_update(
    available: UpdateAvailable,
    staging_dir: str | Path,
    *,
    cancel: Callable[[], bool] | None = None,
) -> VerifiedUpdate:
    """Stream the offered bundle into ``staging_dir`` and verify it.

    Partial files are removed on any failure; the install is untouched.
    """
    artifact = available.manifest.artifacts[0]
    staging, part = _stage_paths(staging_dir, artifact)
    _download_part(available.transport, artifact, part, cancel)
    final = staging / artifact.name
    os.replace(part, final)
    return VerifiedUpdate(
        version=available.version, artifact=artifact, path=final
    )


def _checked_chunks(
    stream: Iterator[object],
    artifact: ManifestArtifact,
    cancel: Callable[[], bool] | None,
) -> Iterator[bytes]:
    """Yield validated chunks; enforce cancel and the size bound."""
    total = 0
    for chunk in stream:
        if cancel is not None and cancel():
            raise UpdateCancelled("download cancelled")
        if not isinstance(chunk, (bytes, bytearray)) or not chunk:
            raise UpdateNetworkError("transport yielded an empty chunk")
        raw = bytes(chunk)
        total += len(raw)
        if total > artifact.size:
            raise UpdateManifestError("artifact exceeds manifest size")
        yield raw


def _stream_to_file(
    transport: UpdateTransport,
    artifact: ManifestArtifact,
    part: Path,
    cancel: Callable[[], bool] | None,
) -> tuple[int, str]:
    """Stream artifact chunks to ``part``; return ``(size, sha256)``."""
    digest, total = hashlib.sha256(), 0
    try:
        stream = transport.fetch_artifact(artifact.name)
        with part.open("wb") as handle:
            for raw in _checked_chunks(stream, artifact, cancel):
                handle.write(raw)
                digest.update(raw)
                total += len(raw)
    except (UpdateCheckError, UpdateManifestError):
        raise
    except Exception as exc:
        raise UpdateNetworkError(f"artifact fetch failed: {exc}") from exc
    return total, digest.hexdigest()
