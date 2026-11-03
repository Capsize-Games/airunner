"""CPU plus independently pinned CUDA payload integration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from scripts import stage_native_runtime_payload as payload
from scripts.tests.test_sidecar_full_bundle import _archive as _cpu_archive
from scripts.tests.test_sidecar_full_bundle import _pins as _cpu_pins
from scripts.tests.test_stage_cuda_runtime_profile import _tar as _cuda_archive
from scripts.tests.test_stage_cuda_runtime_profile import (
    ARTIFACT_ID,
    PRODUCER_COMMIT,
    RECIPE_SHA256,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    SOURCE_TREE,
)


def _cuda_pin(path: Path, archive_sha256: str) -> Path:
    record = {
        "schema": payload.PIN_SCHEMA,
        "status": "verified",
        "release_repository": payload.NATIVE_REPOSITORY,
        "tag": "v1.2.3",
        "asset": payload.CUDA_ASSET,
        "archive_sha256": archive_sha256,
        "artifact_id": ARTIFACT_ID,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "tree": SOURCE_TREE,
        },
        "producer": {
            "commit": PRODUCER_COMMIT,
            "recipe_sha256": RECIPE_SHA256,
        },
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    cpu = tmp_path / "cpu.tar.gz"
    cpu_digest = _cpu_archive(cpu)
    checksums, tag = _cpu_pins(tmp_path, cpu_digest)
    cuda = tmp_path / "cuda.tar.gz"
    cuda_digest = _cuda_archive(cuda)
    pin = _cuda_pin(tmp_path / "cuda-pin.json", cuda_digest)
    return cpu, checksums, tag, cuda, pin


def test_stages_both_profiles_and_writes_reproducible_receipt(tmp_path: Path) -> None:
    cpu, checksums, tag, cuda, pin = _inputs(tmp_path)
    output = tmp_path / "native-runtime" / "payload"
    output.parent.mkdir()

    receipt = payload.stage_payload(
        cpu_archive=cpu,
        output_dir=output,
        cuda_profile_archive=cuda,
        cuda_profile_pin=pin,
        require_cuda_profile=True,
        checksums=checksums,
        tag_file=tag,
    )

    assert receipt["status"] == "verified"
    assert receipt["cpu"]["archive_sha256"] == hashlib.sha256(cpu.read_bytes()).hexdigest()
    assert receipt["cuda_profile"]["artifact_id"] == ARTIFACT_ID
    assert (output / "bin/llama-server").is_file()
    assert (output / "bin/whisper-server").is_file()
    assert (output / "share/airunner/THIRD-PARTY-NOTICES.md").is_file()
    profile = output / "share/airunner/native-runtimes/cuda-sm120a"
    assert (profile / "bin/llama-server-cuda").is_file()
    assert (profile / "profile-manifest.json").is_file()
    checksum = subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS"],
        cwd=output,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert "OK" in checksum.stdout


def test_full_profile_requirement_fails_before_cpu_archive_access(tmp_path: Path) -> None:
    output = tmp_path / "native-runtime"
    with pytest.raises(payload.PayloadStageError, match="requires a published verified CUDA"):
        payload.stage_payload(
            cpu_archive=tmp_path / "missing-cpu.tar.gz",
            output_dir=output,
            require_cuda_profile=True,
        )
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_fetch_rejects_missing_cuda_pin_before_any_network_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_download(*_args: object, **_kwargs: object) -> None:
        pytest.fail("asset download started before the required CUDA pin was checked")

    monkeypatch.setattr(payload, "_download", unexpected_download)
    with pytest.raises(payload.PayloadStageError, match="no CUDA profile is published yet"):
        payload.fetch_and_stage(
            output_dir=tmp_path / "native-runtime",
            cuda_profile_pin=tmp_path / "missing-pin.json",
            require_cuda_profile=True,
            replace_existing=False,
            clean_existing=False,
        )
    assert not (tmp_path / "native-runtime").exists()
    assert list(tmp_path.iterdir()) == []


def test_rejects_symlinked_output_parent_before_staging(tmp_path: Path) -> None:
    cpu, checksums, tag, _cuda, _pin = _inputs(tmp_path)
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    link_parent = tmp_path / "linked-parent"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    output = link_parent / "native-runtime"

    with pytest.raises(payload.PayloadStageError, match="output parent must be a real directory"):
        payload.stage_payload(
            cpu_archive=cpu,
            output_dir=output,
            checksums=checksums,
            tag_file=tag,
        )

    assert not (real_parent / "native-runtime").exists()
    assert list(real_parent.iterdir()) == []


def test_rejects_candidate_pin_before_staging_anything(tmp_path: Path) -> None:
    cpu, checksums, tag, cuda, pin = _inputs(tmp_path)
    record = json.loads(pin.read_text(encoding="utf-8"))
    record["status"] = "candidate"
    pin.write_text(json.dumps(record), encoding="utf-8")
    output = tmp_path / "native-runtime"
    with pytest.raises(payload.PayloadStageError, match="verified published asset"):
        payload.stage_payload(
            cpu_archive=cpu,
            output_dir=output,
            cuda_profile_archive=cuda,
            cuda_profile_pin=pin,
            require_cuda_profile=True,
            checksums=checksums,
            tag_file=tag,
        )
    assert not output.exists()


def test_rejects_wrong_cuda_source_repository_before_staging(tmp_path: Path) -> None:
    cpu, checksums, tag, cuda, pin = _inputs(tmp_path)
    record = json.loads(pin.read_text(encoding="utf-8"))
    record["source"]["repository"] = payload.NATIVE_REPOSITORY
    pin.write_text(json.dumps(record), encoding="utf-8")
    output = tmp_path / "native-runtime"

    with pytest.raises(payload.PayloadStageError, match="source or producer identity"):
        payload.stage_payload(
            cpu_archive=cpu,
            output_dir=output,
            cuda_profile_archive=cuda,
            cuda_profile_pin=pin,
            require_cuda_profile=True,
            checksums=checksums,
            tag_file=tag,
        )

    assert not output.exists()


def test_cpu_refresh_does_not_silently_remove_existing_cuda_profile(tmp_path: Path) -> None:
    cpu, checksums, tag, cuda, pin = _inputs(tmp_path)
    output = tmp_path / "native-runtime"
    payload.stage_payload(
        cpu_archive=cpu,
        output_dir=output,
        cuda_profile_archive=cuda,
        cuda_profile_pin=pin,
        require_cuda_profile=True,
        checksums=checksums,
        tag_file=tag,
    )
    old_profile = output / "share/airunner/native-runtimes/cuda-sm120a/profile-manifest.json"
    old_profile_bytes = old_profile.read_bytes()

    with pytest.raises(payload.PayloadStageError, match="existing CUDA profile would be removed"):
        payload.stage_payload(
            cpu_archive=cpu,
            output_dir=output,
            replace_existing=True,
            checksums=checksums,
            tag_file=tag,
        )

    assert old_profile.read_bytes() == old_profile_bytes
    assert (output / "bin/llama-server").is_file()


def test_explicit_clean_removes_only_owned_generated_payload(tmp_path: Path) -> None:
    cpu, checksums, tag, cuda, pin = _inputs(tmp_path)
    output = tmp_path / "native-runtime"
    payload.stage_payload(
        cpu_archive=cpu,
        output_dir=output,
        cuda_profile_archive=cuda,
        cuda_profile_pin=pin,
        require_cuda_profile=True,
        checksums=checksums,
        tag_file=tag,
    )
    payload.stage_payload(
        cpu_archive=cpu,
        output_dir=output,
        replace_existing=True,
        clean_existing=True,
        checksums=checksums,
        tag_file=tag,
    )
    assert (output / "bin/llama-server").is_file()
    assert not (output / "share/airunner/native-runtimes/cuda-sm120a").exists()
