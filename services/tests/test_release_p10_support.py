"""Synthetic fixtures for the P10 update-verification tests.

Throwaway Ed25519 keys are generated at test time; no private key
or production data appears here. Transports and installers are
in-memory fakes that record every call; the only real subprocess
is the P07 ``upgrade.sh`` handoff test, run against ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from airunner_services.downloads.update_check import (
    UpdateAvailable,
    UpdateNetworkError,
    check_for_updates,
)
from airunner_services.downloads.update_signature import (
    MANIFEST_FORMAT_ID,
)

KEY_ID = "test-only-update-1"
CURRENT_VERSION = "1.2.3"
NEXT_VERSION = "1.2.4"
ARTIFACT_NAME = "bundle-1.2.4.tar.gz"


def fresh_keys() -> tuple[Ed25519PrivateKey, dict[str, bytes]]:
    """Generate a throwaway keypair; return ``(private, store)``."""
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    return private, {KEY_ID: public}


def digest(data: bytes) -> str:
    """Return the lowercase hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def render_manifest(version: str, name: str, size: int, sha256: str) -> bytes:
    """Render deterministic canonical manifest JSON bytes."""
    payload = {
        "format": MANIFEST_FORMAT_ID,
        "version": version,
        "artifacts": [{"name": name, "size": size, "sha256": sha256}],
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def sign_manifest(
    private: Ed25519PrivateKey, key_id: str, data: bytes
) -> bytes:
    """Render a sidecar signature file for the exact ``data`` bytes."""
    signature = private.sign(data).hex()
    text = (
        f"# format: {MANIFEST_FORMAT_ID}\n"
        f"# key_id: {key_id}\n"
        f"# signature: {signature}\n"
    )
    return text.encode("utf-8")


@dataclass
class Case:
    """One signed manifest plus the artifact bytes it describes."""

    manifest: bytes
    signature: bytes
    artifact: bytes
    store: dict[str, bytes]


def make_case(
    artifact: bytes = b"synthetic-bundle-bytes-0123456789",
    version: str = NEXT_VERSION,
) -> Case:
    """Build a signed case describing exactly ``artifact``."""
    private, store = fresh_keys()
    manifest = render_manifest(
        version, ARTIFACT_NAME, len(artifact), digest(artifact)
    )
    signature = sign_manifest(private, KEY_ID, manifest)
    return Case(
        manifest=manifest,
        signature=signature,
        artifact=artifact,
        store=store,
    )


class FakeTransport:
    """Scriptable synthetic transport with a call log.

    ``chunks`` splits the artifact; ``fail_manifest`` raises from
    the manifest fetch; ``fail_after`` raises after N artifact
    chunks to simulate a mid-stream network failure.
    """

    def __init__(
        self,
        case: Case,
        *,
        chunks: int = 2,
        fail_manifest: Exception | None = None,
        fail_after: int | None = None,
    ) -> None:
        self._case = case
        self._chunks = chunks
        self._fail_manifest = fail_manifest
        self._fail_after = fail_after
        self.log: list[str] = []

    def fetch_manifest(self) -> tuple[bytes, bytes]:
        """Return the cased manifest bundle, or raise as scripted."""
        self.log.append("manifest")
        if self._fail_manifest is not None:
            raise self._fail_manifest
        return self._case.manifest, self._case.signature

    def fetch_artifact(self, name: str) -> Iterator[bytes]:
        """Yield the cased artifact in order, or fail mid-stream."""
        self.log.append(f"artifact:{name}")
        data = self._case.artifact
        size = max(1, len(data) // self._chunks)
        yielded = 0
        for index in range(0, len(data), size):
            if self._fail_after is not None and yielded >= self._fail_after:
                raise UpdateNetworkError("synthetic mid-stream failure")
            yielded += 1
            yield data[index : index + size]


def make_tarball(bundle: Path, tar_path: Path) -> Path:
    """Pack ``bundle`` as a gzip tarball; return ``tar_path``."""
    with tarfile.open(tar_path, "w:gz", compresslevel=1) as archive:
        for child in sorted(bundle.iterdir()):
            archive.add(child, arcname=child.name)
    return tar_path


Installer = Callable[[Path, Path], None]


def recording_installer() -> tuple[Installer, list[tuple[Path, Path]]]:
    """Return a ``(installer, calls)`` fixture pair."""
    calls: list[tuple[Path, Path]] = []

    def install(bundle: Path, prefix: Path) -> None:
        calls.append((bundle, prefix))

    return install, calls


def _check(
    case: Case,
    transport: FakeTransport | None = None,
    *,
    opt_in: bool = True,
    store: dict[str, bytes] | None = None,
) -> tuple[UpdateAvailable | None, FakeTransport]:
    """Run a check with explicit knobs; return ``(offer, transport)``."""
    owned = FakeTransport(case) if transport is None else transport
    offer = check_for_updates(
        owned,
        CURRENT_VERSION,
        opt_in=opt_in,
        trusted_keys=case.store if store is None else store,
    )
    return offer, owned


def cancel_after(allowed: int) -> Callable[[], bool]:
    """Return a cancel callback that fires after ``allowed`` polls."""
    state = 0

    def cancel() -> bool:
        nonlocal state
        state += 1
        return state > allowed

    return cancel


def tampered_manifest(case: Case) -> Case:
    """Return ``case`` with one flipped manifest byte."""
    raw = bytearray(case.manifest)
    raw[10] ^= 0xFF
    return Case(bytes(raw), case.signature, case.artifact, case.store)


def corrupted_case(case: Case, kind: str) -> Case:
    """Return ``case`` with a digest- or size-breaking artifact."""
    if kind == "digest":
        raw = bytearray(case.artifact)
        raw[0] ^= 0x01
        return Case(case.manifest, case.signature, bytes(raw), case.store)
    short = (case.manifest, case.signature, case.artifact[:5], case.store)
    return Case(*short)


def _mutated_bodies() -> list[dict[str, object]]:
    """Return manifest bodies that fail strict schema validation."""
    item = {"name": ARTIFACT_NAME, "size": 3, "sha256": digest(b"abc")}
    good = {
        "format": MANIFEST_FORMAT_ID,
        "version": NEXT_VERSION,
        "artifacts": [item],
    }
    return [
        {**good, "format": "airunner-update-manifest/99"},
        {**good, "version": "current"},
        {**good, "artifacts": []},
        {**good, "artifacts": [item, item]},
        {**good, "extra": 1},
    ]


def mutated_manifests() -> Iterator[tuple[bytes, bytes, dict[str, bytes]]]:
    """Yield signed ``(raw, sig, store)`` pairs that fail the schema."""
    private, store = fresh_keys()
    for body in _mutated_bodies():
        raw = json.dumps(body).encode("utf-8")
        yield raw, sign_manifest(private, KEY_ID, raw), store
