"""Tests for Linux candidate tar packaging and final checksums."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import linux_candidate_artifact as candidate  # noqa: E402

_SHA = "abcdef0123456789abcdef0123456789abcdef01"
_VERSION = "6.1.5"


def _candidate_tree(root: Path) -> tuple[Path, bytes]:
    bundle = root / "airunner-daemon"
    bundle.mkdir()
    executable = bundle / "airunner-daemon"
    executable.write_bytes(b"synthetic executable")
    executable.chmod(0o755)
    payload = bundle / "payload.bin"
    payload.write_bytes(b"synthetic payload")
    (bundle / "payload-link").symlink_to("payload.bin")
    manifest = {
        "bundle": "airunner-services-linux-v1",
        "tool": "pyinstaller",
        "entry": "airunner-daemon",
        "base": _SHA,
        "files": [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in (
                ("airunner-daemon", executable.read_bytes()),
                ("payload-link", payload.read_bytes()),
                ("payload.bin", payload.read_bytes()),
            )
        ],
    }
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    (bundle / "bundle-manifest.json").write_bytes(manifest_bytes)
    return bundle, manifest_bytes


def test_candidate_archive_roundtrip_preserves_manifest_modes_and_symlinks(
    tmp_path: Path,
) -> None:
    """Archive bytes retain the verified identity and executable mode."""
    bundle, expected_manifest = _candidate_tree(tmp_path)
    archive_path = candidate.create_archive(
        bundle, tmp_path / "out", _VERSION, _SHA
    )
    assert archive_path.name == candidate.archive_filename(_VERSION, _SHA)
    candidate.verify_archive(archive_path, _VERSION, _SHA)

    extracted = tmp_path / "extract"
    with tarfile.open(archive_path, "r:gz") as archive:
        root_name = archive_path.name.removesuffix(".tar.gz")
        archived_manifest = archive.extractfile(
            archive.getmember(f"{root_name}/bundle-manifest.json")
        )
        assert archived_manifest is not None
        assert archived_manifest.read() == expected_manifest
        assert archive.getmember(f"{root_name}/airunner-daemon").mode & 0o111
        assert archive.getmember(f"{root_name}/payload-link").issym()
        archive.extractall(extracted, filter="data")
    restored = extracted / archive_path.name.removesuffix(".tar.gz")
    assert (restored / "bundle-manifest.json").read_bytes() == expected_manifest
    assert (restored / "airunner-daemon").stat().st_mode & 0o111
    assert (restored / "payload-link").read_bytes() == b"synthetic payload"


def test_candidate_archive_rejects_source_or_manifest_mismatch(
    tmp_path: Path,
) -> None:
    bundle, _ = _candidate_tree(tmp_path)
    with pytest.raises(candidate.CandidateArtifactError, match="source SHA"):
        candidate.create_archive(bundle, tmp_path / "out", _VERSION, "1" * 40)
    (bundle / "payload.bin").write_bytes(b"changed after manifest")
    with pytest.raises(candidate.CandidateArtifactError, match="hash mismatch"):
        candidate.create_archive(bundle, tmp_path / "out", _VERSION, _SHA)


def test_candidate_archive_rejects_escaping_symlink_and_special_file(
    tmp_path: Path,
) -> None:
    bundle, _ = _candidate_tree(tmp_path)
    (bundle / "escape").symlink_to("../../outside")
    with pytest.raises(candidate.CandidateArtifactError, match="symlink"):
        candidate.create_archive(bundle, tmp_path / "out", _VERSION, _SHA)

    (bundle / "escape").unlink()
    fifo = bundle / "named-pipe"
    os.mkfifo(fifo)
    with pytest.raises(candidate.CandidateArtifactError, match="special file"):
        candidate.create_archive(bundle, tmp_path / "out", _VERSION, _SHA)


def _archive_with_root(tmp_path: Path, kind: bytes, mode: int, duplicate: bool) -> Path:
    bundle, _ = _candidate_tree(tmp_path)
    original = candidate.create_archive(bundle, tmp_path / "out", _VERSION, _SHA)
    destination = tmp_path / "with-root" / original.name
    destination.parent.mkdir()
    root = tarfile.TarInfo(original.name.removesuffix(".tar.gz"))
    root.type = kind
    root.mode = mode
    root.linkname = "../../outside"
    with tarfile.open(original, "r:gz") as source:
        with tarfile.open(destination, "w:gz") as target:
            target.addfile(root)
            if duplicate:
                target.addfile(root)
            for member in source:
                data = source.extractfile(member) if member.isfile() else None
                try:
                    target.addfile(member, data)
                finally:
                    if data is not None:
                        data.close()
    return destination


@pytest.mark.parametrize(("kind", "mode", "duplicate"), [
    (tarfile.SYMTYPE, 0o755, False),
    (tarfile.LNKTYPE, 0o755, False),
    (tarfile.REGTYPE, 0o755, False),
    (tarfile.CHRTYPE, 0o755, False),
    (tarfile.DIRTYPE, 0o4755, False),
    (tarfile.DIRTYPE, 0o755, True),
])
def test_candidate_archive_rejects_unsafe_or_duplicate_root(
    tmp_path: Path, kind: bytes, mode: int, duplicate: bool,
) -> None:
    archive = _archive_with_root(tmp_path, kind, mode, duplicate)
    with pytest.raises(candidate.CandidateArtifactError, match="unsafe root"):
        candidate.verify_archive(archive, _VERSION, _SHA)


def test_candidate_archive_accepts_explicit_regular_root_directory(tmp_path: Path) -> None:
    archive = _archive_with_root(tmp_path, tarfile.DIRTYPE, 0o755, False)
    candidate.verify_archive(archive, _VERSION, _SHA)


def test_release_checksums_use_exact_bytes_and_reject_basename_collisions(
    tmp_path: Path,
) -> None:
    first_dir, second_dir = tmp_path / "a", tmp_path / "b"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "service.whl"
    first.write_bytes(b"wheel bytes")
    sidecar = second_dir / "runtime.tar.gz"
    sidecar.write_bytes(b"sidecar bytes")
    output = tmp_path / "SHA256SUMS"
    candidate.write_checksums([first, sidecar], output)
    assert output.read_text(encoding="ascii") == (
        f"{hashlib.sha256(b'sidecar bytes').hexdigest()}  runtime.tar.gz\n"
        f"{hashlib.sha256(b'wheel bytes').hexdigest()}  service.whl\n"
    )

    duplicate = second_dir / first.name
    duplicate.write_bytes(b"different asset")
    with pytest.raises(candidate.CandidateArtifactError, match="collision"):
        candidate.write_checksums([first, duplicate], output)
