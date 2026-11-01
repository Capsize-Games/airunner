"""Adversarial archives cannot write outside the sidecar staging contract."""

from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
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
    checksums, tag_file = c01._write_test_sidecar_pin(
        archive.parent, archive
    )
    return c01._run_stage(
        "--tarball", str(archive), "--bundle", str(bundle),
        "--checksums", str(checksums), "--tag-file", str(tag_file),
        "--platform", "linux", "--",
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


def test_repository_pin_fails_closed_while_provenance_is_pending(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    before = (bundle / "bundle-manifest.json").read_bytes()
    proc = c01._run_stage(
        "--tarball", str(archive),
        "--checksums", str(c01._ROOT / ".github/native-sidecar-checksums.json"),
        "--tag-file", str(c01._ROOT / ".github/native-sidecar-version"),
        "--platform", "linux", "--bundle", str(bundle), "--",
        "llama-server", "whisper-server",
    )
    assert proc.returncode != 0
    assert "pending verification" in proc.stderr
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert list((bundle / "bin").iterdir()) == []


def test_pending_archive_pin_can_be_rejected_before_download():
    helper = c01._ROOT / "scripts" / "sidecar_archive.py"
    result = subprocess.run(
        [sys.executable, str(helper), "check-pin", "--checksums",
         str(c01._ROOT / ".github/native-sidecar-checksums.json"),
         "--tag-file", str(c01._ROOT / ".github/native-sidecar-version"),
         "--platform", "linux"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "pending verification" in result.stderr


def test_pending_source_review_rejects_before_clone_or_repository_access():
    helper = c01._ROOT / "scripts" / "sidecar_archive.py"
    result = subprocess.run(
        [sys.executable, str(helper), "check-source-pin", "--checksums",
         str(c01._ROOT / ".github/native-sidecar-checksums.json"),
         "--tag-file", str(c01._ROOT / ".github/native-sidecar-version")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "source review is pending" in result.stderr


def test_wrong_expected_digest_does_not_stage_any_payload(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    checksums, tag_file = c01._write_test_sidecar_pin(tmp_path, archive)
    metadata = json.loads(checksums.read_text())
    metadata["archives"]["linux"]["sha256"] = "0" * 64
    checksums.write_text(json.dumps(metadata))
    before = (bundle / "bundle-manifest.json").read_bytes()
    result = c01._run_stage(
        "--tarball", str(archive), "--bundle", str(bundle),
        "--checksums", str(checksums), "--tag-file", str(tag_file),
        "--platform", "linux", "--", "llama-server", "whisper-server",
    )
    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert list((bundle / "bin").iterdir()) == []


def test_same_binary_basename_in_two_directories_is_ambiguous(tmp_path):
    bundle, archive = c01._stage_fixture(tmp_path)
    _archive(archive, [
        _member("one/llama-server"), _member("two/llama-server"),
        _member("whisper-server"),
    ])
    before = (bundle / "bundle-manifest.json").read_bytes()
    result = _run(bundle, archive)
    assert result.returncode != 0
    assert "ambiguous" in result.stderr
    assert (bundle / "bundle-manifest.json").read_bytes() == before
    assert list((bundle / "bin").iterdir()) == []


def test_source_checkout_must_match_the_committed_source_pin(tmp_path):
    repo = tmp_path / "native"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"],
        check=True,
    )
    (repo / "source.txt").write_text("pinned source\n")
    subprocess.run(["git", "-C", str(repo), "add", "source.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    pin = tmp_path / "source-pin.json"
    pin.write_text(json.dumps({
        "tag": "v0.1.0",
        "source_commit": commit,
        "source_review_status": "reviewed",
    }))
    tag = tmp_path / "source-tag"
    tag.write_text("v0.1.0\n")
    helper = c01._ROOT / "scripts" / "sidecar_archive.py"

    def verify() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(helper), "verify-source", "--checksums", str(pin),
             "--tag-file", str(tag), "--repository", str(repo)],
            capture_output=True, text=True, check=False,
        )

    result = verify()
    assert result.returncode == 0, result.stderr
    (repo / "unexpected.txt").write_text("dirty\n")
    result = verify()
    assert result.returncode != 0
    assert "local changes" in result.stderr
