from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/stage_docker_release_inputs.py"
SPEC = importlib.util.spec_from_file_location("docker_input_stager_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
stager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stager)


def _fake_stage(_manifest: Path, _lock: Path, output: Path) -> dict:
    output.mkdir(parents=True)
    (output / "requirements.txt").write_text("fixture==1\n", encoding="utf-8")
    return {}


def test_preparation_contains_only_reviewed_contexts_and_receipt(tmp_path: Path) -> None:
    output = tmp_path / "prepared-inputs"
    output.mkdir()

    receipt = stager.prepare(output, stage_fn=_fake_stage)

    assert set(path.name for path in output.iterdir()) == {
        "runtime", "builder", "bootstrap", "release-source", "preparation-receipt.json"
    }
    assert receipt["status"].startswith("reviewed offline Docker build inputs")
    for section in ("runtime", "builder", "bootstrap"):
        assert (output / section / "requirements.txt").is_file()
        assert (output / section / "artifact-sources.json").is_file()
        assert (output / section / "selected-lock.txt").is_file()
    assert (output / "release-source/packaging/linux/services-bundle-spec.toml").is_file()
    assert (output / "release-source/scripts/collect_runtime_dependency_notices.py").is_file()
    assert (output / "release-source/package/constraints-linux-nvidia-cu129-linux-release.txt").is_file()
    assert not (output / "release-source/.git").exists()
    assert not (output / "release-source/.headlesscode").exists()
    copied = receipt["release_source_sha256"]
    assert copied["packaging/linux/services-bundle-spec.toml"]
    assert "release-planning/services/release-inputs.json" not in copied


def test_failed_staging_keeps_requested_empty_output_empty(tmp_path: Path) -> None:
    output = tmp_path / "prepared-inputs"
    output.mkdir()

    def fail_on_builder(_manifest: Path, _lock: Path, destination: Path) -> dict:
        destination.mkdir(parents=True)
        if destination.name == "builder":
            raise RuntimeError("fixture failure")
        return {}

    try:
        stager.prepare(output, stage_fn=fail_on_builder)
    except RuntimeError as error:
        assert str(error) == "fixture failure"
    else:
        raise AssertionError("fixture stage failure was not propagated")
    assert output.is_dir() and list(output.iterdir()) == []
    assert not list(tmp_path.glob(".prepared-inputs.prepared-*"))


def test_preparation_rejects_nonempty_or_in_checkout_destination(tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep", encoding="utf-8")
    for destination in (occupied, ROOT / "must-not-be-created"):
        try:
            stager.prepare(destination, stage_fn=_fake_stage)
        except stager.PreparationError:
            pass
        else:
            raise AssertionError(f"unsafe destination accepted: {destination}")
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "keep"
    assert not (ROOT / "must-not-be-created").exists()
