"""Unit tests for the Z-Image bundle helper extractions.

_resolve_bundle_probe, _missing_bundle_files, and
_trigger_zimage_download were extracted to keep
ensure_zimage_files_available within the long-function threshold.
These tests pin the probe resolution, the missing-file filtering,
and the download-trigger failure modes.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from airunner_services.art.managers.zimage.mixins import (
    zimage_bundle_helper as bundle_mod,
)
from airunner_services.art.managers.zimage.mixins.zimage_bundle_helper import (
    ZImageBundleHelper,
)


def _make_helper(owner=None):
    helper = ZImageBundleHelper.__new__(ZImageBundleHelper)
    helper._owner = owner or MagicMock()
    helper.resolve_zimage_companion_dir = MagicMock(return_value=None)
    return helper


def test_probe_prefers_companion_dir(tmp_path):
    helper = _make_helper()
    companion = tmp_path / "companion"
    companion.mkdir()
    helper.resolve_zimage_companion_dir.return_value = companion
    model_path = tmp_path / "model.safetensors"
    search_dir, probe = helper._resolve_bundle_probe(model_path, "pretrained_directory")
    assert search_dir == companion
    assert probe == companion


def test_probe_file_model_uses_parent(tmp_path):
    helper = _make_helper()
    model_path = tmp_path / "model.safetensors"
    model_path.write_bytes(b"x")
    search_dir, probe = helper._resolve_bundle_probe(model_path, "pretrained_directory")
    assert search_dir == tmp_path
    assert probe == tmp_path / "model.safetensors"


def test_missing_files_excludes_selected_file(tmp_path, monkeypatch):
    helper = _make_helper()
    model_path = tmp_path / "model.safetensors"
    model_path.write_bytes(b"x")
    monkeypatch.setattr(
        bundle_mod,
        "get_missing_files_for_mode",
        lambda probe, mode: ["model.safetensors", "other.safetensors"],
    )
    missing = helper._missing_bundle_files(tmp_path, "m", model_path)
    assert missing == ["other.safetensors"]


def test_missing_files_keeps_selected_when_probing_elsewhere(tmp_path, monkeypatch):
    helper = _make_helper()
    model_path = tmp_path / "model.safetensors"
    model_path.write_bytes(b"x")
    monkeypatch.setattr(
        bundle_mod,
        "get_missing_files_for_mode",
        lambda probe, mode: ["model.safetensors"],
    )
    missing = helper._missing_bundle_files(tmp_path / "probe", "m", model_path)
    # probe differs from model_path and model exists... exclusion applies
    assert missing == []


def test_trigger_without_repo_raises(tmp_path, monkeypatch):
    helper = _make_helper()
    monkeypatch.setattr(
        bundle_mod.ModelFileChecker,
        "get_repo_id_for_version",
        staticmethod(lambda *a, **k: None),
    )
    with pytest.raises(RuntimeError, match="Could not resolve a download source"):
        helper._trigger_zimage_download(tmp_path, ["a.safetensors"])


def test_trigger_emits_signal_and_raises(tmp_path, monkeypatch):
    helper = _make_helper()
    monkeypatch.setattr(
        bundle_mod.ModelFileChecker,
        "get_repo_id_for_version",
        staticmethod(lambda *a, **k: "org/repo"),
    )
    with pytest.raises(RuntimeError, match="download triggered"):
        helper._trigger_zimage_download(tmp_path, ["a.safetensors"])
    helper._owner.emit_signal.assert_called_once()
    args, _ = helper._owner.emit_signal.call_args
    assert args[1]["repo_id"] == "org/repo"
    assert args[1]["missing_files"] == ["a.safetensors"]
