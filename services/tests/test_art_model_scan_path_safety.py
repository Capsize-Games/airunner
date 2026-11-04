"""Path-boundary regressions for local art model discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from airunner_services.api.routes.art_model_scan import (
    first_model_path,
    version_model_path,
)


def _checkpoint(root: Path, version: str, action: str = "txt2img") -> Path:
    action_dir = root / version / action
    action_dir.mkdir(parents=True)
    model = action_dir / "model.safetensors"
    model.write_bytes(b"fixture")
    return model


def test_version_and_action_must_be_single_safe_segments(
    tmp_path: Path,
) -> None:
    root = tmp_path / "configured-cache"
    outside = tmp_path / "outside"
    root.mkdir()
    outside_model = _checkpoint(outside, "installed")

    assert version_model_path(root, "../outside/installed", "txt2img") == ""
    assert version_model_path(root, "installed", "../outside") == ""
    assert version_model_path(root, str(outside_model.parent), "txt2img") == ""


@pytest.mark.parametrize(
    ("version", "action"),
    [("../outside", "txt2img"), ("installed", "../outside")],
)
def test_unsafe_segments_are_rejected_before_filesystem_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
    action: str,
) -> None:
    root = tmp_path / "cache"
    root.mkdir()

    def unexpected_probe(_path: Path, *_args: object, **_kwargs: object) -> object:
        raise AssertionError("unsafe path triggered a filesystem probe")

    monkeypatch.setattr(Path, "exists", unexpected_probe)
    monkeypatch.setattr(Path, "is_dir", unexpected_probe)
    monkeypatch.setattr(Path, "iterdir", unexpected_probe)
    assert version_model_path(root, version, action) == ""


def test_symlinked_version_or_action_cannot_escape_configured_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "custom-cache"
    outside = tmp_path / "outside"
    root.mkdir()
    outside_model = _checkpoint(outside, "installed")

    (root / "linked-version").symlink_to(outside / "installed", target_is_directory=True)
    assert version_model_path(root, "linked-version", "txt2img") == ""

    version_dir = root / "real-version"
    version_dir.mkdir()
    (version_dir / "txt2img").symlink_to(outside_model.parent, target_is_directory=True)
    assert version_model_path(root, "real-version", "txt2img") == ""
    assert first_model_path(root) == ""

    bundle_dir = root / "bundle-version" / "txt2img"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "model_index.json").symlink_to(outside / "installed" / "model_index.json")
    assert version_model_path(root, "bundle-version", "txt2img") == ""


def test_spaced_version_and_explicit_custom_cache_root_are_supported(
    tmp_path: Path,
) -> None:
    # This explicit cache is outside AIRunner's default model path by design.
    custom_root = tmp_path / "operator cache"
    model = _checkpoint(custom_root, "Z-Image Turbo v1")

    assert version_model_path(custom_root, "Z-Image Turbo v1", "txt2img") == str(model)
    assert first_model_path(custom_root) == str(model)
