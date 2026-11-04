"""Assembly keeps CUDA optional unless an explicit spec requires it."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import assemble_linux_bundle as assemble  # noqa: E402
from stage_cuda_runtime_profile import StageError  # noqa: E402


def _args(**overrides):
    values = {
        "cuda_profile_archive": None,
        "cuda_profile_sha256": None,
        "cuda_profile_artifact_id": None,
        "cuda_profile_source_repository": None,
        "cuda_profile_source_commit": None,
        "cuda_profile_source_tree": None,
        "cuda_profile_producer_commit": None,
        "cuda_profile_recipe_sha256": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_default_profile_remains_cpu_bundle_without_cuda_input() -> None:
    assert assemble._cuda_profile_inputs(
        _args(), {"native_cuda_profile": {"required": False}}
    ) is None


def test_required_profile_fails_before_freeze_when_inputs_are_absent() -> None:
    with pytest.raises(StageError, match="requires CUDA profile inputs"):
        assemble._cuda_profile_inputs(
            _args(), {"native_cuda_profile": {"required": True}}
        )


def test_partial_pin_set_fails_closed() -> None:
    with pytest.raises(StageError, match="every external identity"):
        assemble._cuda_profile_inputs(
            _args(cuda_profile_archive="candidate.tar.gz"),
            {"native_cuda_profile": {"required": False}},
        )


def _write_bad_manifest_archive(path: Path) -> str:
    with tarfile.open(path, "w:gz") as archive:
        root = tarfile.TarInfo("airunner-native-runtime-cuda-sm120a")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        archive.addfile(root)
        manifest = tarfile.TarInfo(
            "airunner-native-runtime-cuda-sm120a/profile-manifest.json"
        )
        manifest.mode = 0o644
        manifest.size = len(b"{not-json")
        archive.addfile(manifest, io.BytesIO(b"{not-json"))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _main_args(archive: Path, digest: str) -> list[str]:
    return [
        "--base", "testrev",
        "--cuda-profile-archive", str(archive),
        "--cuda-profile-sha256", digest,
        "--cuda-profile-artifact-id", "test-only-synthetic-fixture",
        "--cuda-profile-source-repository", "Capsize-Games/airunner-native",
        "--cuda-profile-source-commit", "1" * 40,
        "--cuda-profile-source-tree", "2" * 40,
        "--cuda-profile-producer-commit", "3" * 40,
        "--cuda-profile-recipe-sha256", "4" * 64,
    ]


@pytest.mark.parametrize("bad_archive", ["checksum", "manifest"])
def test_bad_explicit_profile_fails_before_pyinstaller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_archive: str
) -> None:
    archive = tmp_path / "bad-profile.tar.gz"
    actual_digest = _write_bad_manifest_archive(archive)
    expected_digest = "0" * 64 if bad_archive == "checksum" else actual_digest
    spec = {
        "native_cuda_profile": {"required": False},
        "native_speech": {"required": False},
        "postgresql_runtime": {"mode": "disabled"},
        "warn_allowlist": {},
    }
    inspector = SimpleNamespace(
        load_spec=lambda _path: spec,
        spec_errors=lambda _spec: [],
    )
    monkeypatch.setattr(assemble, "_load_inspect_module", lambda: inspector)
    monkeypatch.setattr(
        assemble, "_output_paths", lambda _args, _spec: (tmp_path / "work", tmp_path / "dist")
    )
    monkeypatch.setattr(assemble, "resolve_base_rev", lambda _root, _base: "testrev")
    monkeypatch.setattr(
        assemble, "_freeze_cmd", lambda *_args: (tmp_path / "entry.py", ["pyinstaller"])
    )
    monkeypatch.setattr(
        assemble,
        "_freeze_tree",
        lambda *_args: pytest.fail("PyInstaller must not run for an invalid profile"),
    )

    result = assemble.main(_main_args(archive, expected_digest))

    assert result == 2
    assert not (tmp_path / "work").exists()
    assert not (tmp_path / "dist").exists()
