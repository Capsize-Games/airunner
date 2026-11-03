"""Static tests for the fixed-run CUDA wheel handoff verifier."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts.stage_cuda_wheel import (
    HandoffError,
    verify_artifact_directory,
)


def _spec(wheel_bytes: bytes) -> dict:
    return {
        "repository": "Example/airunner",
        "artifact": {
            "id": 123,
            "source_revision": "a" * 40,
        },
        "wheel": {
            "filename": "llama_cpp_python-0.3.21-py3-none-linux_x86_64.whl",
            "sha256": hashlib.sha256(wheel_bytes).hexdigest(),
            "size_bytes": len(wheel_bytes),
            "name": "llama_cpp_python",
            "version": "0.3.21",
            "requires_python": ">=3.8",
            "license": "MIT",
            "tag": "py3-none-linux_x86_64",
            "record_entries": 4,
            "required_runtime_dependencies": [
                "typing-extensions>=4.5.0",
                "numpy>=1.20.0",
                "diskcache>=5.6.1",
                "jinja2>=2.11.3",
            ],
        },
        "build": {
            "wrapper_commit": "b" * 40,
            "llama_cpp_commit": "c" * 40,
            "cuda_image": "nvidia/cuda:test@sha256:" + "d" * 64,
            "cuda_arch": "120a-real",
            "network_during_compile": "none",
            "model_or_gpu_execution": "none",
            "source_date_epoch": "1777269304",
            "cmake_archive_sha256": "e" * 64,
            "backend_wheels": {
                "pip-test-py3-none-any.whl": "1" * 64,
            },
        },
    }


def _wheel_bytes(*, bad_record: bool = False) -> bytes:
    files = {
        "llama_cpp/lib/libggml-cuda.so": b"test native library",
        "llama_cpp_python-0.3.21.dist-info/METADATA": (
            "Name: llama_cpp_python\n"
            "Version: 0.3.21\n"
            "Requires-Python: >=3.8\n"
            "License-Expression: MIT\n"
            "Requires-Dist: typing-extensions>=4.5.0\n"
            "Requires-Dist: numpy>=1.20.0\n"
            "Requires-Dist: diskcache>=5.6.1\n"
            "Requires-Dist: jinja2>=2.11.3\n"
        ).encode(),
        "llama_cpp_python-0.3.21.dist-info/WHEEL": (
            "Wheel-Version: 1.0\n"
            "Root-Is-Purelib: false\n"
            "Tag: py3-none-linux_x86_64\n"
        ).encode(),
    }
    record_name = "llama_cpp_python-0.3.21.dist-info/RECORD"
    rows = []
    for name, content in files.items():
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(content).digest()
        ).rstrip(b"=").decode()
        if bad_record and name.endswith("METADATA"):
            digest = "A" * len(digest)
        rows.append((name, f"sha256={digest}", str(len(content))))
    rows.append((record_name, "", ""))
    csv_text = io.StringIO()
    csv.writer(csv_text, lineterminator="\n").writerows(rows)
    files[record_name] = csv_text.getvalue().encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _build_manifest(spec: dict) -> str:
    build = spec["build"]
    wheel = spec["wheel"]
    lines = [
        f"wrapper_commit={build['wrapper_commit']}",
        f"llama_cpp_commit={build['llama_cpp_commit']}",
        f"cuda_image={build['cuda_image']}",
        f"cmake_archive_sha256={build['cmake_archive_sha256']}",
        f"cuda_arch={build['cuda_arch']}",
        "source_date_epoch=1777269304",
        f"{wheel['sha256']}  /tmp/wheel/{wheel['filename']}",
        f"{next(iter(build['backend_wheels'].values()))}  /tmp/backend/{next(iter(build['backend_wheels']))}",
        "network_during_compile=none",
        "model_or_gpu_execution=none",
    ]
    return "\n".join(lines) + "\n"


def _artifact(tmp_path: Path, *, bad_record: bool = False) -> tuple[Path, dict]:
    wheel_bytes = _wheel_bytes(bad_record=bad_record)
    spec = _spec(wheel_bytes)
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "BUILD-MANIFEST.txt").write_text(
        _build_manifest(spec), encoding="utf-8"
    )
    (artifact / spec["wheel"]["filename"]).write_bytes(wheel_bytes)
    return artifact, spec


def test_verified_handoff_checks_manifest_wheel_and_record(tmp_path):
    artifact, spec = _artifact(tmp_path)

    result = verify_artifact_directory(artifact, spec)

    assert result["artifact_id"] == 123
    assert result["wheel_sha256"] == spec["wheel"]["sha256"]
    assert result["record_entries"] == 4


def test_handoff_rejects_record_tampering(tmp_path):
    artifact, spec = _artifact(tmp_path, bad_record=True)

    with pytest.raises(HandoffError, match="RECORD integrity mismatch"):
        verify_artifact_directory(artifact, spec)


def test_handoff_rejects_mismatched_cuda_target(tmp_path):
    artifact, spec = _artifact(tmp_path)
    manifest = artifact / "BUILD-MANIFEST.txt"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "cuda_arch=120a-real", "cuda_arch=90"
        ),
        encoding="utf-8",
    )

    with pytest.raises(HandoffError, match="build manifest mismatch for cuda_arch"):
        verify_artifact_directory(artifact, spec)


def test_handoff_binds_the_reviewed_wrapper_patch_digest(tmp_path):
    artifact, spec = _artifact(tmp_path)
    spec["build"]["wrapper_patch_sha256"] = "f" * 64
    with (artifact / "BUILD-MANIFEST.txt").open("a") as stream:
        stream.write("wrapper_patch_sha256=" + "e" * 64 + "\n")
    with pytest.raises(HandoffError, match="wrapper_patch_sha256"):
        verify_artifact_directory(artifact, spec)


def test_handoff_rejects_diskcache_reintroduced_as_a_base_requirement(tmp_path):
    artifact, spec = _artifact(tmp_path)
    spec["wheel"]["required_runtime_dependencies"].remove("diskcache>=5.6.1")
    spec["wheel"]["isolated_dependency_names"] = ["diskcache"]
    spec["wheel"]["optional_runtime_dependencies"] = []
    with pytest.raises(HandoffError, match="activates an isolated optional dependency"):
        verify_artifact_directory(artifact, spec)


def test_handoff_rejects_extra_artifact_files(tmp_path):
    artifact, spec = _artifact(tmp_path)
    (artifact / "unexpected.txt").write_text("extra", encoding="utf-8")

    with pytest.raises(HandoffError, match="file set"):
        verify_artifact_directory(artifact, spec)


@pytest.mark.parametrize("bad_record", [False, True])
def test_staging_exposes_only_a_complete_verified_artifact(tmp_path, monkeypatch, bad_record):
    import scripts.stage_cuda_wheel as module

    artifact, spec = _artifact(tmp_path, bad_record=bad_record)
    spec["schema_version"] = 1
    handoff = tmp_path / "handoff.json"
    handoff.write_text(json.dumps(spec))
    destination = tmp_path / "staging" / "cuda-wheel"

    def download(archive_path, handoff):
        with zipfile.ZipFile(archive_path, "w") as archive:
            for path in artifact.iterdir():
                archive.write(path, path.name)

    monkeypatch.setattr(module, "_download_archive", download)
    if bad_record:
        with pytest.raises(HandoffError, match="RECORD integrity mismatch"):
            module.stage_cuda_wheel(destination, handoff)
        assert not destination.exists()
    else:
        result = module.stage_cuda_wheel(destination, handoff)
        assert result["wheel_sha256"] == spec["wheel"]["sha256"]
        assert {path.name for path in destination.iterdir()} == {path.name for path in artifact.iterdir()}
        assert module.stage_cuda_wheel(destination, handoff) == result
    assert not list(destination.parent.glob("airunner-cuda-wheel-*"))


def test_staging_preserves_only_the_hash_verified_archive_copy(tmp_path, monkeypatch):
    import scripts.stage_cuda_wheel as module

    artifact, spec = _artifact(tmp_path)
    spec["schema_version"] = 1
    destination = tmp_path / "staging" / "cuda-wheel"
    archive_copy = tmp_path / "preserved" / "source.zip"

    expected_archive = tmp_path / "expected.zip"
    with zipfile.ZipFile(expected_archive, "w") as archive:
        for path in artifact.iterdir():
            archive.write(path, path.name)
    spec["artifact"]["zip_sha256"] = hashlib.sha256(expected_archive.read_bytes()).hexdigest()
    handoff = tmp_path / "handoff.json"
    handoff.write_text(json.dumps(spec))

    def download(archive_path, _loaded_handoff):
        import shutil

        shutil.copyfile(expected_archive, archive_path)

    monkeypatch.setattr(module, "_download_archive", download)

    result = module.stage_cuda_wheel(destination, handoff, archive_copy)

    assert result["wheel_sha256"] == spec["wheel"]["sha256"]
    assert hashlib.sha256(archive_copy.read_bytes()).hexdigest() == spec["artifact"]["zip_sha256"]
    assert {path.name for path in destination.iterdir()} == {path.name for path in artifact.iterdir()}
    repeated_copy = tmp_path / "preserved-again" / "source.zip"
    repeated = module.stage_cuda_wheel(destination, handoff, repeated_copy)
    assert repeated == result
    assert hashlib.sha256(repeated_copy.read_bytes()).hexdigest() == spec["artifact"]["zip_sha256"]
    assert not list(destination.parent.glob("airunner-cuda-wheel-*"))
    assert not list(destination.parent.glob("airunner-cuda-wheel-archive-*"))
