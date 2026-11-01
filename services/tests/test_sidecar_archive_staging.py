"""Adversarial archives cannot write outside the sidecar staging contract."""

from __future__ import annotations

import io
import json
from pathlib import Path
import tarfile

import pytest
import test_release_c01_support as c01


def _member(name: str, kind: bytes = tarfile.REGTYPE) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.type = kind
    member.size = 3 if kind == tarfile.REGTYPE else 0
    member.linkname = "../../outside"
    return member


def _archive(path: Path, members: list[tarfile.TarInfo]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for member in members:
            archive.addfile(member, io.BytesIO(b"elf") if member.isfile() else None)


def _run(bundle: Path, archive: Path, *names: str):
    return c01._run_stage(
        "--tarball", str(archive), "--bundle", str(bundle), "--",
        *(names or ("llama-server", "whisper-server")),
    )


@pytest.mark.parametrize("bad_member", [
    _member("../../outside"),
    _member("/tmp/sidecar-outside"),
    _member("bin\\llama-server"),
    _member("linked", tarfile.SYMTYPE),
    _member("linked", tarfile.LNKTYPE),
    _member("device", tarfile.CHRTYPE),
    _member("pipe", tarfile.FIFOTYPE),
    _member("another/llama-server"),
    _member("bin/llama-server"),
])
def test_invalid_archive_leaves_candidate_unchanged(tmp_path, bad_member):
    bundle, archive = c01._stage_fixture(tmp_path)
    before = (bundle / "bundle-manifest.json").read_bytes()
    _archive(archive, [
        _member("bin/llama-server"), _member("bin/whisper-server"), bad_member,
    ])
    result = _run(bundle, archive)
    assert result.returncode != 0
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert list((bundle / "bin").iterdir()) == []
    assert not list(bundle.glob(".stage-sidecars-*"))
    assert not (tmp_path / "outside").exists()


def test_missing_second_binary_does_not_stage_the_first(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    _archive(archive, [_member("bin/llama-server")])
    assert _run(bundle, archive).returncode != 0
    assert list((bundle / "bin").iterdir()) == []


@pytest.mark.parametrize("destination", ["file", "symlink", "recorded", "bin-link"])
def test_existing_destination_is_preserved(tmp_path, destination):
    bundle, archive = c01._stage_fixture(tmp_path)
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"preserve")
    target = bundle / "bin" / "llama-server"
    if destination == "file":
        target.write_bytes(b"preserve")
    elif destination == "symlink":
        target.symlink_to(sentinel)
    elif destination == "bin-link":
        target.parent.rmdir()
        target.parent.symlink_to(tmp_path, target_is_directory=True)
    else:
        manifest_path = bundle / "bundle-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"].append({"path": "bin/llama-server", "sha256": "0" * 64})
        manifest_path.write_text(json.dumps(manifest))
    before = (bundle / "bundle-manifest.json").read_bytes()
    result = _run(bundle, archive)
    assert result.returncode != 0
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert sentinel.read_bytes() == b"preserve"
    if destination == "file":
        assert target.read_bytes() == b"preserve"
    assert not (target.parent / "whisper-server").exists()


def test_repeated_requested_binary_is_rejected(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    assert _run(bundle, archive, "llama-server", "llama-server").returncode != 0
    assert list((bundle / "bin").iterdir()) == []


def test_native_tar_dot_prefix_and_executable_mode_are_supported(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    _archive(archive, [
        _member(".", tarfile.DIRTYPE),
        _member("./bin", tarfile.DIRTYPE),
        _member("./bin/llama-server"),
        _member("./bin/whisper-server"),
    ])
    result = _run(bundle, archive)
    assert result.returncode == 0, result.stderr
    assert (bundle / "bin/llama-server").stat().st_mode & 0o777 == 0o755
    assert (bundle / "bin/whisper-server").read_bytes() == b"elf"
