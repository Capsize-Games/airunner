"""Synthetic safety tests for the eSpeak native payload stager."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

import pytest

from scripts.stage_espeak_native_payload import (
    RECEIPT_NAME,
    StagingError,
    stage_espeak_payload,
    verify_staged_espeak,
)


ARCHIVE_NAME = "espeak-ng-1.52.0-4870adf.tar.gz"
PATCH_NAME = "0001-offline-no-playback.patch"
LICENSE_CONTENT = {
    "COPYING": b"license-gpl\n",
    "COPYING.APACHE": b"license-apache\n",
    "COPYING.BSD2": b"license-bsd\n",
    "COPYING.UCD": b"license-ucd\n",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blob_id(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_payload(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    package = repo / "packaging/espeak"
    scripts = repo / "scripts"
    package.mkdir(parents=True)
    scripts.mkdir(parents=True)

    archive = b"small synthetic locked archive"
    patch = b"small synthetic patch\n"
    _write(package / "BUILD.md", b"synthetic build provenance\n")
    _write(scripts / "build_espeak_native_payload.py", b"build script\n")
    _write(scripts / "intake_espeak_source.py", b"intake script\n")
    _write(package / PATCH_NAME, patch)
    target = {
        "platform": "Ubuntu 24.04 x86_64",
        "cmake_targets": ["espeak-ng-bin", "data"],
        "sonic": "disabled; native eSpeak rate control retained",
        "playback": "disabled",
        "mbrola": "disabled",
        "pcaudio": "disabled",
        "async": "disabled",
        "klatt": "enabled",
        "compat_symlinks": "disabled",
    }
    lock = {
        "schema_version": 1,
        "upstream": {"commit": "1" * 40, "tree": "2" * 40},
        "source_archive": {
            "filename": ARCHIVE_NAME,
            "sha256": hashlib.sha256(archive).hexdigest(),
            "size_bytes": len(archive),
        },
        "patches": [{"filename": PATCH_NAME, "sha256": hashlib.sha256(patch).hexdigest()}],
        "license_git_blob_ids": {
            name: _blob_id(content) for name, content in LICENSE_CONTENT.items()
        },
        "target": target,
    }
    lock_path = package / "source-lock.json"
    lock_bytes = (json.dumps(lock, sort_keys=True, indent=2) + "\n").encode()
    lock_path.write_bytes(lock_bytes)

    payload = tmp_path / "payload"
    _write(payload / "bin/espeak-ng", b"synthetic executable\n")
    os.chmod(payload / "bin/espeak-ng", 0o755)
    for name in (
        "phondata",
        "phondata-manifest",
        "phonindex",
        "phontab",
        "intonations",
        "en_dict",
    ):
        _write(payload / f"share/espeak-ng-data/{name}", f"{name}\n".encode())
    _write(payload / f"source/{ARCHIVE_NAME}", archive)
    _write(payload / f"source/{PATCH_NAME}", patch)
    provenance = {
        "source/BUILD.md": package / "BUILD.md",
        "source/build_espeak_native_payload.py": scripts / "build_espeak_native_payload.py",
        "source/intake_espeak_source.py": scripts / "intake_espeak_source.py",
        "source/source-lock.json": lock_path,
    }
    for relative, source in provenance.items():
        _write(payload / relative, source.read_bytes())
    for name, content in LICENSE_CONTENT.items():
        _write(payload / f"licenses/espeak-ng/{name}", content)

    files = {
        path.relative_to(payload).as_posix(): _sha256(path)
        for path in payload.rglob("*")
        if path.is_file()
    }
    receipt = {
        "source_commit": lock["upstream"]["commit"],
        "source_tree": lock["upstream"]["tree"],
        "source_archive_sha256": lock["source_archive"]["sha256"],
        "patch_sha256": lock["patches"][0]["sha256"],
        "target": target,
        "files_sha256": files,
    }
    _write(
        payload / RECEIPT_NAME,
        (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode(),
    )
    return payload, repo, lock_path


def _receipt(payload: Path) -> dict:
    return json.loads((payload / RECEIPT_NAME).read_text(encoding="utf-8"))


def _rewrite_receipt(payload: Path, value: dict) -> None:
    _write(
        payload / RECEIPT_NAME,
        (json.dumps(value, sort_keys=True, indent=2) + "\n").encode(),
    )


def test_stages_complete_tree_preserves_bundle_and_is_idempotent(tmp_path):
    payload, repo, lock = _make_payload(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write(bundle / "keep.txt", b"unrelated bundle content")
    _write(bundle / "share/espeak-ng-data/unrelated.dict", b"keep me")

    manifest_path = stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)

    assert (bundle / "keep.txt").read_bytes() == b"unrelated bundle content"
    assert (bundle / "share/espeak-ng-data/unrelated.dict").read_bytes() == b"keep me"
    assert (bundle / "bin/espeak-ng").read_bytes() == b"synthetic executable\n"
    assert stat.S_IMODE((bundle / "bin/espeak-ng").stat().st_mode) & 0o111
    assert (bundle / "share/espeak-ng-data/phontab").is_file()
    assert (bundle / "licenses/espeak-ng/COPYING").is_file()
    assert (bundle / "share/airunner/espeak-ng-native/source/source-lock.json").is_file()
    assert (bundle / "share/airunner/espeak-ng-native/build-receipt.json").is_file()
    assert manifest["component"] == "espeak-ng-native"
    assert all("path" in item and "sha256" in item for item in manifest["files"])
    assert manifest_path.relative_to(bundle).as_posix() == (
        "share/airunner/espeak-ng-native/component-manifest.json"
    )

    stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert manifest_path.read_bytes() == manifest_bytes
    assert (bundle / "keep.txt").read_bytes() == b"unrelated bundle content"
    assert verify_staged_espeak(bundle) == []


@pytest.mark.parametrize("defect", ["missing-data", "tampered-data", "bad-mode", "missing-license", "symlink"])
def test_staged_verifier_detects_broken_component(tmp_path, defect):
    payload, repo, lock = _make_payload(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    data = bundle / "share/espeak-ng-data/phontab"
    if defect == "missing-data":
        data.unlink()
    elif defect == "tampered-data":
        data.write_bytes(b"changed")
    elif defect == "bad-mode":
        (bundle / "bin/espeak-ng").chmod(0o644)
    elif defect == "missing-license":
        (bundle / "licenses/espeak-ng/COPYING").unlink()
    else:
        data.unlink()
        data.symlink_to(payload / "share/espeak-ng-data/phontab")
    assert verify_staged_espeak(bundle)


def test_missing_component_is_allowed_only_when_optional(tmp_path):
    assert verify_staged_espeak(tmp_path)
    assert verify_staged_espeak(tmp_path, required=False) == []


@pytest.mark.parametrize("mode", [0o644, 0o4755, 0o2755])
def test_existing_binary_with_unsafe_mode_fails_before_staging(tmp_path, mode):
    payload, repo, lock = _make_payload(tmp_path)
    bundle = tmp_path / "bundle"
    binary = bundle / "bin/espeak-ng"
    _write(binary, (payload / "bin/espeak-ng").read_bytes())
    binary.chmod(mode)

    with pytest.raises(StagingError, match="executable|setuid or setgid"):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert not (bundle / "share").exists()
    assert stat.S_IMODE(binary.stat().st_mode) == mode


@pytest.mark.parametrize("tamper", ["listed-bytes", "unlisted-extra", "traversal"])
def test_payload_tampering_fails_before_bundle_mutation(tmp_path, tamper):
    payload, repo, lock = _make_payload(tmp_path)
    if tamper == "listed-bytes":
        (payload / "bin/espeak-ng").write_bytes(b"altered")
    elif tamper == "unlisted-extra":
        _write(payload / "share/espeak-ng-data/extra", b"extra")
    else:
        receipt = _receipt(payload)
        digest = receipt["files_sha256"].pop("share/espeak-ng-data/en_dict")
        receipt["files_sha256"]["../outside"] = digest
        _rewrite_receipt(payload, receipt)
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert list(bundle.iterdir()) == []


@pytest.mark.parametrize("relative", ["licenses/espeak-ng/COPYING", "source/BUILD.md"])
def test_missing_license_or_provenance_fails_without_partial_stage(tmp_path, relative):
    payload, repo, lock = _make_payload(tmp_path)
    (payload / relative).unlink()
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert list(bundle.iterdir()) == []


def test_malformed_oversized_and_wrong_identity_receipts_are_rejected(tmp_path):
    payload, repo, lock = _make_payload(tmp_path / "first")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (payload / RECEIPT_NAME).write_bytes(b"{" + b" " * (1024 * 1024))
    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(bundle.iterdir()) == []

    payload, repo, lock = _make_payload(tmp_path / "duplicate")
    (payload / RECEIPT_NAME).write_text('{"files_sha256": {}, "files_sha256": {}}')
    with pytest.raises(StagingError, match="duplicate"):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(bundle.iterdir()) == []

    payload, repo, lock = _make_payload(tmp_path / "wrong-identity")
    receipt = _receipt(payload)
    receipt["source_commit"] = "f" * 40
    _rewrite_receipt(payload, receipt)
    with pytest.raises(StagingError, match="source_commit"):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(bundle.iterdir()) == []


@pytest.mark.parametrize(
    "relative",
    [
        "share/espeak-ng-data/phondata",
        "share/espeak-ng-data/intonations",
        "source/espeak-ng-1.52.0-4870adf.tar.gz",
        "source/0001-offline-no-playback.patch",
        "licenses/espeak-ng/COPYING.APACHE",
    ],
)
def test_required_runtime_and_provenance_files_cannot_be_missing(tmp_path, relative):
    payload, repo, lock = _make_payload(tmp_path)
    (payload / relative).unlink()
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert list(bundle.iterdir()) == []


def test_payload_and_destination_symlinks_are_rejected(tmp_path):
    payload, repo, lock = _make_payload(tmp_path / "payload-case")
    outside = tmp_path / "outside"
    outside.mkdir()
    (payload / "share/espeak-ng-data/escaped").symlink_to(outside / "victim")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(bundle.iterdir()) == []

    payload, repo, lock = _make_payload(tmp_path / "destination-case")
    bundle = tmp_path / "bundle-dest"
    bundle.mkdir()
    external_share = tmp_path / "external-share"
    external_share.mkdir()
    (bundle / "share").symlink_to(external_share, target_is_directory=True)
    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(external_share.iterdir()) == []

    payload, repo, lock = _make_payload(tmp_path / "nested-destination-case")
    bundle = tmp_path / "bundle-nested"
    bundle.mkdir()
    external_bin = tmp_path / "external-bin"
    external_bin.mkdir()
    (bundle / "bin").symlink_to(external_bin, target_is_directory=True)
    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)
    assert list(external_bin.iterdir()) == []


def test_source_provenance_symlink_is_rejected(tmp_path):
    payload, repo, lock = _make_payload(tmp_path)
    source = payload / "source/BUILD.md"
    content = source.read_bytes()
    source.unlink()
    target = tmp_path / "outside-build.md"
    target.write_bytes(content)
    source.symlink_to(target)
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(StagingError):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert list(bundle.iterdir()) == []


def test_setuid_payload_file_is_rejected_before_bundle_mutation(tmp_path):
    payload, repo, lock = _make_payload(tmp_path)
    executable = payload / "bin/espeak-ng"
    os.chmod(executable, stat.S_IMODE(executable.stat().st_mode) | stat.S_ISUID)
    assert executable.stat().st_mode & stat.S_ISUID
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    with pytest.raises(StagingError, match="setuid or setgid"):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert list(bundle.iterdir()) == []


def test_conflicting_existing_file_is_rejected_before_any_other_write(tmp_path):
    payload, repo, lock = _make_payload(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _write(bundle / "bin/espeak-ng", b"different existing executable")
    (bundle / "bin/espeak-ng").chmod(0o755)

    with pytest.raises(StagingError, match="conflicting file"):
        stage_espeak_payload(payload, bundle, lock_path=lock, repo_root=repo)

    assert set(path.relative_to(bundle).as_posix() for path in bundle.rglob("*")) == {
        "bin",
        "bin/espeak-ng",
    }
