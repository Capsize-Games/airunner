"""Tests for Z-Image bundle requirement helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import torch
from safetensors.torch import save_file

from airunner.components.art.managers.zimage.mixins.zimage_pipeline_loading_mixin import (
    ZImagePipelineLoadingMixin,
)
from airunner.components.art.managers.zimage.zimage_bundle_requirements import (
    list_archived_files,
    list_bundle_files,
    get_downloadable_files_for_mode,
    get_missing_files_for_mode,
    get_required_files_for_mode,
    get_unused_files_for_mode,
)
from airunner.enums import SignalCode
from airunner.bin.zimage_bundle_report import _archive_unused_files


class DummyZImageLoader(ZImagePipelineLoadingMixin):
    """Minimal loader stub for exercising the bundle gate."""

    def __init__(self, model_path: Path):
        self.logger = MagicMock()
        self.model_path = str(model_path)
        self.version = "Z-Image Turbo"
        self.pipeline_action = "txt2img"
        self.image_request = None
        self.signals: list[tuple[SignalCode, dict]] = []

    def emit_signal(self, code, data=None):
        """Record emitted signals for assertions."""
        self.signals.append((code, data or {}))


def test_native_fp8_requirements_skip_transformer_bundle(tmp_path):
    """Native FP8 mode should not require pretrained transformer files."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    required = get_required_files_for_mode(checkpoint)
    assert "scheduler/scheduler_config.json" not in required
    assert "transformer/config.json" not in required
    assert "model_index.json" not in required


def test_native_fp8_mode_accepts_sharded_text_encoder(tmp_path):
    """Sharded text-encoder weights should satisfy the lean FP8 bundle."""
    checkpoint = _create_native_fp8_bundle(tmp_path, sharded_text_encoder=True)
    missing = get_missing_files_for_mode(checkpoint)
    assert missing == []


def test_native_fp8_mode_marks_transformer_dir_unused(tmp_path):
    """Pretrained transformer files should audit as unused in native FP8 mode."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    _write_text(tmp_path / "txt2img" / "transformer" / "config.json", "{}")
    _touch(tmp_path / "txt2img" / "transformer" / "diffusion_pytorch_model.safetensors")
    unused = get_unused_files_for_mode(checkpoint)
    assert "transformer/config.json" in unused
    assert "transformer/diffusion_pytorch_model.safetensors" in unused


def test_ensure_files_available_allows_lean_native_fp8_bundle(tmp_path):
    """Lean native FP8 bundles should pass without download signals."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    loader = DummyZImageLoader(checkpoint)
    loader._ensure_zimage_files_available()
    assert loader.signals == []


def test_ensure_files_available_reports_only_needed_missing_files(tmp_path):
    """Missing-file signals should exclude unused pretrained transformer files."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    (tmp_path / "txt2img" / "vae" / "diffusion_pytorch_model.safetensors").unlink()
    loader = DummyZImageLoader(checkpoint)
    with pytest.raises(RuntimeError, match="download triggered"):
        loader._ensure_zimage_files_available()
    signal_code, payload = loader.signals[0]
    assert signal_code == SignalCode.ART_MODEL_DOWNLOAD_REQUIRED
    assert "vae/diffusion_pytorch_model.safetensors" in payload["missing_files"]
    assert "transformer/config.json" not in payload["missing_files"]
    assert "scheduler/scheduler_config.json" not in payload["missing_files"]


def test_preflight_download_check_skips_archived_native_fp8_files(tmp_path):
    """Base preflight should not trigger downloads for archived FP8 bundle files."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    loader = DummyZImageLoader(checkpoint)
    should_download, download_info = loader._check_and_trigger_download()
    assert should_download is False
    assert download_info == {}
    assert loader.signals == []


def test_preflight_download_check_only_emits_live_missing_files(tmp_path):
    """Base preflight should only emit genuinely required lean bundle files."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    (tmp_path / "txt2img" / "vae" / "diffusion_pytorch_model.safetensors").unlink()
    loader = DummyZImageLoader(checkpoint)
    should_download, download_info = loader._check_and_trigger_download()
    assert should_download is True
    assert download_info["missing_files"] == [
        "vae/diffusion_pytorch_model.safetensors"
    ]
    assert loader.signals[0][1]["missing_files"] == [
        "vae/diffusion_pytorch_model.safetensors"
    ]


def test_downloadable_files_for_native_fp8_skip_transformer_bundle(tmp_path):
    """Downloader should only fetch lean companion files for native FP8 bundles."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    files = get_downloadable_files_for_mode(checkpoint)
    assert "text_encoder/config.json" in files
    assert "vae/diffusion_pytorch_model.safetensors" in files
    assert all(not item.startswith("transformer/") for item in files)
    assert "scheduler/scheduler_config.json" not in files


def test_list_bundle_files_ignores_archive_dir(tmp_path):
    """Archived files should not be treated as active bundle files."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    archive_file = (
        tmp_path
        / "txt2img"
        / "archive"
        / "native_fp8_single_file"
        / "snapshot"
        / "transformer"
        / "diffusion_pytorch_model.safetensors"
    )
    _touch(archive_file)
    assert "archive/native_fp8_single_file/snapshot/transformer/diffusion_pytorch_model.safetensors" not in list_bundle_files(checkpoint)
    assert "archive/native_fp8_single_file/snapshot/transformer/diffusion_pytorch_model.safetensors" in list_archived_files(checkpoint)


def test_archive_unused_files_moves_native_fp8_unused_payload(tmp_path):
    """Archive action should move unused native FP8 files out of the live bundle."""
    checkpoint = _create_native_fp8_bundle(tmp_path)
    _write_text(tmp_path / "txt2img" / "transformer" / "config.json", "{}")
    _touch(tmp_path / "txt2img" / "transformer" / "diffusion_pytorch_model.safetensors")
    result = _archive_unused_files(checkpoint, "active")
    assert "transformer/config.json" in result["moved_files"]
    assert "transformer/diffusion_pytorch_model.safetensors" in result["moved_files"]
    assert not (tmp_path / "txt2img" / "transformer" / "config.json").exists()
    assert (Path(result["archive_dir"]) / "transformer" / "config.json").exists()
    assert Path(result["manifest_path"]).exists()


def _create_native_fp8_bundle(
    tmp_path: Path,
    sharded_text_encoder: bool = False,
) -> Path:
    """Create a lean FP8 bundle in a temporary directory."""
    bundle_dir = tmp_path / "txt2img"
    _write_json(bundle_dir / "text_encoder" / "config.json", {"architectures": ["Qwen3Model"]})
    _write_text(bundle_dir / "tokenizer" / "tokenizer_config.json", "{}")
    _write_text(bundle_dir / "tokenizer" / "tokenizer.json", "{}")
    _write_text(bundle_dir / "tokenizer" / "merges.txt", "")
    _write_text(bundle_dir / "tokenizer" / "vocab.json", "{}")
    _write_json(bundle_dir / "vae" / "config.json", {"sample_size": 64})
    _save_tensor(bundle_dir / "vae" / "diffusion_pytorch_model.safetensors")
    _save_tensor(bundle_dir / "lean_fp8_checkpoint.safetensors")
    if sharded_text_encoder:
        _create_sharded_text_encoder(bundle_dir / "text_encoder")
    else:
        _save_tensor(
            bundle_dir / "text_encoder" / "model.safetensors",
            metadata={"format": "pt"},
        )
    return bundle_dir / "lean_fp8_checkpoint.safetensors"


def _create_sharded_text_encoder(text_encoder_dir: Path) -> None:
    """Create a text-encoder layout that resolves through the shard index."""
    _save_tensor(
        text_encoder_dir / "model.safetensors",
        metadata={"merged_from": "model.safetensors.index.json"},
    )
    index_path = text_encoder_dir / "model.safetensors.index.json"
    _write_json(
        index_path,
        {
            "weight_map": {
                "encoder.layers.0.weight": "model-00001-of-00002.safetensors",
                "encoder.layers.1.weight": "model-00002-of-00002.safetensors",
            }
        },
    )
    _touch(text_encoder_dir / "model-00001-of-00002.safetensors")
    _touch(text_encoder_dir / "model-00002-of-00002.safetensors")


def _save_tensor(path: Path, metadata: dict | None = None) -> None:
    """Write a minimal safetensors file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file({"weight": torch.zeros(1)}, str(path), metadata=metadata or {})


def _touch(path: Path) -> None:
    """Create an empty file at the requested path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _write_json(path: Path, data: dict) -> None:
    """Write JSON data to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _write_text(path: Path, content: str) -> None:
    """Write text content to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)