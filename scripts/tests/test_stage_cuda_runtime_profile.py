"""Adversarial tests for explicit, offline CUDA profile staging."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from scripts import stage_cuda_runtime_profile as stage


SOURCE_REPOSITORY = "Capsize-Games/airunner-native"
SOURCE_COMMIT = "1" * 40
SOURCE_TREE = "2" * 40
PRODUCER_COMMIT = "3" * 40
RECIPE_SHA256 = "4" * 64
ARTIFACT_ID = "test-only-synthetic-fixture"
WRAPPER = b"#!/bin/sh\nserver_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\nexport LD_LIBRARY_PATH=\"$server_dir/../lib\"\ncd /\nexec \"$server_dir/llama-server\" \"$@\"\n"
FILES = {
    "bin/llama-server-cuda": (WRAPPER, 0o755),
    "bin/llama-server": (b"synthetic server bytes; never executed\n", 0o755),
    "lib/libcandidate.so": (b"synthetic library bytes; never loaded\n", 0o644),
}


def _manifest(status: str = "verified") -> bytes:
    return json.dumps({
        "schema": stage.SCHEMA,
        "status": status,
        "profile": "cuda-sm120a",
        "artifact_id": ARTIFACT_ID,
        "platform": "linux-x86_64",
        "abi": "ubuntu-24.04",
        "compute_capability": "12.0",
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
        },
        "producer": {"commit": PRODUCER_COMMIT, "recipe_sha256": RECIPE_SHA256},
        "entrypoint": "bin/llama-server-cuda",
        "files": [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "mode": mode}
            for name, (data, mode) in sorted(FILES.items())
        ],
    }).encode()


def _manifest_with_changes(**changes) -> bytes:
    data = json.loads(_manifest())
    for path, values in changes.items():
        entry = next(row for row in data["files"] if row["path"] == path)
        entry.update(values)
    return json.dumps(data).encode()


def _tar(
    path: Path, *, manifest: bytes | None = None, extras=(), edits=None,
    payload_edits=None,
) -> str:
    edits = edits or {}
    payload_edits = payload_edits or {}
    with tarfile.open(path, "w:gz") as archive:
        root = tarfile.TarInfo(stage.ARCHIVE_ROOT)
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        archive.addfile(root)
        names = ["bin", "lib"]
        for directory in names:
            info = tarfile.TarInfo(f"{stage.ARCHIVE_ROOT}/{directory}")
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            archive.addfile(info)
        payloads = {name: data for name, (data, _mode) in FILES.items()}
        payloads.update(payload_edits)
        payloads[stage.MANIFEST_NAME] = manifest or _manifest()
        for name, data in payloads.items():
            info = tarfile.TarInfo(f"{stage.ARCHIVE_ROOT}/{name}")
            info.mode = edits.get(f"mode:{name}", FILES.get(name, (b"", 0o644))[1])
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        for kind, name, data in extras:
            info = tarfile.TarInfo(f"{stage.ARCHIVE_ROOT}/{name}")
            if kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = data
            elif kind == "directory":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
            elif kind == "file":
                info.mode = 0o644
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
                continue
            else:
                info.type = tarfile.FIFOTYPE
            archive.addfile(info)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(archive: Path, bundle: Path, digest: str, **overrides):
    identity = {
        "expected_sha256": digest,
        "artifact_id": ARTIFACT_ID,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "producer_commit": PRODUCER_COMMIT,
        "recipe_sha256": RECIPE_SHA256,
    }
    identity.update(overrides)
    return stage.stage_cuda_profile(archive, bundle, **identity)


def test_stages_synthetic_profile_atomically_and_preserves_cpu(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive)
    bundle = tmp_path / "bundle"
    (bundle / "bin").mkdir(parents=True)
    cpu = bundle / "bin/llama-server"
    cpu.write_bytes(b"existing CPU binary remains unchanged")

    report = stage.verify_cuda_profile_archive(
        archive,
        **{
            "expected_sha256": digest,
            "artifact_id": ARTIFACT_ID,
            "source_repository": SOURCE_REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "source_tree": SOURCE_TREE,
            "producer_commit": PRODUCER_COMMIT,
            "recipe_sha256": RECIPE_SHA256,
        },
    )
    assert report["archive_sha256"] == digest
    assert report["artifact_id"] == ARTIFACT_ID
    assert list(bundle.iterdir()) == [bundle / "bin"]

    target = _stage(archive, bundle, digest)

    assert target == bundle / stage.PROFILE_RELATIVE
    assert (target / "bin/llama-server-cuda").read_bytes() == WRAPPER
    assert (target / "bin/llama-server").read_bytes() == FILES["bin/llama-server"][0]
    assert cpu.read_bytes() == b"existing CPU binary remains unchanged"
    assert not list(bundle.rglob(".cuda-profile-stage-*"))
    assert target.stat().st_mode & 0o777 == 0o755
    from airunner_services.runtimes.native_backend_profiles import select_native_backend

    selected = select_native_backend(
        n_gpu_layers=-1,
        requested="cuda-sm120a",
        bundle_root=bundle,
        device_probe=lambda: "CUDA0",
    )
    assert selected.artifact_id == ARTIFACT_ID
    assert selected.executable == str(target / "bin/llama-server-cuda")
    assert selected.verified is True


@pytest.mark.parametrize("kind,name,data", [
    ("symlink", "bin/evil", "../../outside"),
    ("file", "extra/unlisted", b"extra"),
    ("fifo", "bin/pipe", b""),
])
def test_rejects_links_special_and_unlisted_paths(
    tmp_path: Path, kind: str, name: str, data
) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive, extras=[(kind, name, data)])
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError):
        _stage(archive, bundle, digest)
    assert not (bundle / stage.PROFILE_RELATIVE).exists()


def test_rejects_candidate_status_and_wrong_external_identity(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive, manifest=_manifest("candidate"))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError, match="verified"):
        _stage(archive, bundle, digest)

    digest = _tar(archive)
    with pytest.raises(stage.StageError, match="source identity"):
        _stage(archive, bundle, digest, source_commit="5" * 40)
    assert not (bundle / stage.PROFILE_RELATIVE).exists()


def test_rejects_file_hash_mode_and_wrong_archive_digest(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive, edits={"mode:bin/llama-server": 0o644})
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError, match="mode"):
        _stage(archive, bundle, digest)
    assert list(bundle.iterdir()) == []

    digest = _tar(archive)
    with pytest.raises(stage.StageError, match="SHA-256"):
        _stage(archive, bundle, "0" * 64)
    with pytest.raises(stage.StageError, match="producer identity"):
        _stage(archive, bundle, digest, producer_commit="5" * 40)
    assert not (bundle / stage.PROFILE_RELATIVE).exists()


def test_rejects_payload_hash_mismatch_before_creating_profile_parents(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(
        archive,
        payload_edits={"lib/libcandidate.so": b"different unreviewed bytes"},
    )
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError, match="hash"):
        _stage(archive, bundle, digest)
    assert not (bundle / "share").exists()


def test_rejects_wrapper_and_malformed_manifest_without_destination_writes(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "candidate.tar.gz"
    bad_wrapper = b"#!/bin/sh\nexec /unconfined/llama-server\n"
    bad_manifest = _manifest_with_changes(
        **{"bin/llama-server-cuda": {
            "sha256": hashlib.sha256(bad_wrapper).hexdigest(),
            "mode": 0o755,
        }}
    )
    digest = _tar(
        archive,
        manifest=bad_manifest,
        payload_edits={"bin/llama-server-cuda": bad_wrapper},
    )
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError, match="wrapper"):
        _stage(archive, bundle, digest)
    assert list(bundle.iterdir()) == []

    malformed = json.loads(_manifest())
    malformed["files"][0]["sha256"] = ["not", "a", "hash"]
    digest = _tar(archive, manifest=json.dumps(malformed).encode())
    with pytest.raises(stage.StageError, match="hash or mode"):
        _stage(archive, bundle, digest)
    assert list(bundle.iterdir()) == []


def test_rejects_extremely_nested_manifest_as_stage_error(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive, manifest=b"[" * 10_000 + b"0" + b"]" * 10_000)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    with pytest.raises(stage.StageError, match="invalid JSON"):
        _stage(archive, bundle, digest)
    assert list(bundle.iterdir()) == []


def test_rejects_existing_or_symlink_destination_without_touching_cpu(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive)
    bundle = tmp_path / "bundle"
    (bundle / "bin").mkdir(parents=True)
    cpu = bundle / "bin/llama-server"
    cpu.write_bytes(b"cpu")
    target = bundle / stage.PROFILE_RELATIVE
    target.parent.mkdir(parents=True)
    target.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    with pytest.raises(stage.StageError, match="already exists"):
        _stage(archive, bundle, digest)
    assert cpu.read_bytes() == b"cpu"
    assert target.is_symlink()


def test_rejects_symlinked_profile_ancestor_without_touching_cpu(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    digest = _tar(archive)
    bundle = tmp_path / "bundle"
    (bundle / "bin").mkdir(parents=True)
    cpu = bundle / "bin/llama-server"
    cpu.write_bytes(b"cpu")
    outside = tmp_path / "outside"
    outside.mkdir()
    (bundle / "share").symlink_to(outside, target_is_directory=True)
    with pytest.raises(stage.StageError, match="symlink"):
        _stage(archive, bundle, digest)
    assert cpu.read_bytes() == b"cpu"
    assert list(outside.iterdir()) == []


def test_rejects_archive_path_escape(tmp_path: Path) -> None:
    archive = tmp_path / "candidate.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("../escape")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(stage.StageError, match="unsafe"):
        _stage(archive, bundle, digest)
    assert not (tmp_path / "escape").exists()
