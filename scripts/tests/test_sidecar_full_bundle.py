"""Safe extraction tests for the complete pinned native CPU sidecar bundle."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from scripts import sidecar_archive


FILES = {
    ".airunner-native-owned": (b"owned fixture\n", 0o644),
    "bin/llama-server": (b"synthetic llama bytes; not executed\n", 0o755),
    "bin/whisper-server": (b"synthetic whisper bytes; not executed\n", 0o755),
    "share/airunner/licenses/llama.cpp-LICENSE": (b"synthetic license text\n", 0o644),
    "share/airunner/licenses/whisper.cpp-LICENSE": (b"synthetic license text\n", 0o644),
    "share/airunner/runtime_manifest.env": (b"runtime_version=test\n", 0o644),
    "share/airunner/runtime_pins.env": (b"source_commit=" + b"a" * 40 + b"\n", 0o644),
    "share/airunner/source_provenance.env": (b"source_review=fixture\n", 0o644),
    "share/airunner/THIRD-PARTY-NOTICES.md": (b"fixture notices\n", 0o644),
}


def _archive(path: Path, *, extras=(), mode_override=None) -> str:
    with tarfile.open(path, "w:gz") as output:
        root = tarfile.TarInfo(".")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        output.addfile(root)
        directories = {
            parent.as_posix()
            for name in FILES
            for parent in Path(name).parents
            if parent.as_posix() != "."
        }
        for name in sorted(directories, key=lambda value: (value.count("/"), value)):
            entry = tarfile.TarInfo(f"./{name}")
            entry.type = tarfile.DIRTYPE
            entry.mode = 0o755
            output.addfile(entry)
        for name, (content, mode) in FILES.items():
            entry = tarfile.TarInfo(f"./{name}")
            entry.mode = mode_override.get(name, mode) if mode_override else mode
            entry.size = len(content)
            output.addfile(entry, io.BytesIO(content))
        for kind, name, value in extras:
            entry = tarfile.TarInfo(f"./{name}")
            if kind == "symlink":
                entry.type = tarfile.SYMTYPE
                entry.linkname = value
            elif kind == "file":
                entry.mode = 0o644
                entry.size = len(value)
                output.addfile(entry, io.BytesIO(value))
                continue
            else:
                entry.type = tarfile.FIFOTYPE
            output.addfile(entry)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pins(tmp_path: Path, digest: str) -> tuple[Path, Path]:
    checksums = tmp_path / "checksums.json"
    checksums.write_text(json.dumps({
        "tag": "v9.8.7",
        "source_commit": "a" * 40,
        "source_review_status": "reviewed",
        "provenance_status": "verified",
        "archives": {"linux": {
            "asset": "runtime-sidecars-linux.tar.gz",
            "sha256": digest,
        }},
    }), encoding="utf-8")
    tag_file = tmp_path / "tag"
    tag_file.write_text("v9.8.7\n", encoding="utf-8")
    return checksums, tag_file


def test_stages_complete_archive_and_preserves_notices_provenance(tmp_path: Path) -> None:
    archive = tmp_path / "runtime-sidecars.tar.gz"
    digest = _archive(archive)
    checksums, tag = _pins(tmp_path, digest)
    output = tmp_path / "runtime"

    result = sidecar_archive.stage_full_bundle(archive, output, checksums, tag, "linux")

    assert result == digest
    for name, (content, _mode) in FILES.items():
        assert (output / name).read_bytes() == content
    assert sorted(path.name for path in (output / "share/airunner/licenses").iterdir()) == [
        "llama.cpp-LICENSE", "whisper.cpp-LICENSE",
    ]
    assert not any(path.is_symlink() for path in output.rglob("*"))


@pytest.mark.parametrize("kind,name,value", [
    ("symlink", "bin/escape", "../../outside"),
    ("fifo", "bin/special", b""),
    ("file", "unexpected/root-file", b"extra"),
])
def test_rejects_unsafe_or_unexpected_archive_entries(
    tmp_path: Path, kind: str, name: str, value
) -> None:
    archive = tmp_path / "runtime-sidecars.tar.gz"
    digest = _archive(archive, extras=[(kind, name, value)])
    checksums, tag = _pins(tmp_path, digest)
    output = tmp_path / "runtime"
    with pytest.raises(sidecar_archive.SidecarArchiveError):
        sidecar_archive.stage_full_bundle(archive, output, checksums, tag, "linux")
    assert not output.exists()


def test_refuses_existing_destination_and_unpinned_archive(tmp_path: Path) -> None:
    archive = tmp_path / "runtime-sidecars.tar.gz"
    digest = _archive(archive)
    checksums, tag = _pins(tmp_path, digest)
    output = tmp_path / "runtime"
    output.mkdir()
    (output / "keep").write_bytes(b"keep")
    with pytest.raises(sidecar_archive.SidecarArchiveError, match="already exists"):
        sidecar_archive.stage_full_bundle(archive, output, checksums, tag, "linux")
    with pytest.raises(sidecar_archive.SidecarArchiveError, match="no sidecar archive record"):
        sidecar_archive.stage_full_bundle(archive, tmp_path / "fresh", checksums, tag, "windows")
    assert (output / "keep").read_bytes() == b"keep"
