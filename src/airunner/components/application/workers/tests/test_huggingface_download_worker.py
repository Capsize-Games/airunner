from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import torch
from safetensors.torch import save_file

from airunner.components.application.workers.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
)
from airunner.components.data.bootstrap.unified_model_files import (
    get_required_files_for_model,
)


class FakeResponse:
    def __init__(self, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=8192):
        for chunk in self._chunks:
            yield chunk


class TestHuggingFaceDownloadWorker:
    def test_resolve_art_download_context_from_repo_id(self):
        version, pipeline_action = HuggingFaceDownloadWorker._resolve_art_download_context(
            repo_id="Tongyi-MAI/Z-Image-Turbo",
            version=None,
            pipeline_action=None,
        )

        assert version == "Z-Image Turbo"
        assert pipeline_action == "txt2img"

    def test_download_file_restarts_after_http_416(self):
        worker = HuggingFaceDownloadWorker()
        payload = b"abcdef"

        with TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir) / ".downloading"
            model_dir = Path(tmpdir) / "model"
            temp_dir.mkdir(parents=True)
            model_dir.mkdir(parents=True)

            partial_path = temp_dir / "model_index.json"
            partial_path.write_bytes(b"abc")

            responses = [
                FakeResponse(status_code=416),
                FakeResponse(
                    status_code=200,
                    headers={"content-length": str(len(payload))},
                    chunks=[payload],
                ),
            ]

            with patch(
                "airunner.components.application.workers.huggingface_download_worker.requests.get",
                side_effect=responses,
            ):
                with patch.object(worker, "emit_signal"):
                    worker._download_file(
                        repo_id="Tongyi-MAI/Z-Image-Turbo",
                        filename="model_index.json",
                        file_size=len(payload),
                        temp_dir=temp_dir,
                        model_path=model_dir,
                        api_key="",
                    )

            final_path = model_dir / "model_index.json"
            assert final_path.exists()
            assert final_path.read_bytes() == payload
            assert "model_index.json" in worker._completed_files

    def test_prune_zimage_bootstrap_files_for_native_fp8_bundle(self, tmp_path):
        worker = HuggingFaceDownloadWorker()
        bundle_dir = _create_zimage_fp8_bundle(tmp_path)
        bootstrap = get_required_files_for_model(
            "art",
            "Z-Image Turbo",
            "Z-Image Turbo",
            "txt2img",
        )

        pruned = worker._prune_zimage_bootstrap_files(bundle_dir, bootstrap)

        assert "text_encoder/config.json" in pruned
        assert "vae/diffusion_pytorch_model.safetensors" in pruned
        assert "scheduler/scheduler_config.json" not in pruned
        assert all(not name.startswith("transformer/") for name in pruned)

    def test_prune_zimage_missing_files_for_native_fp8_bundle(self, tmp_path):
        worker = HuggingFaceDownloadWorker()
        bundle_dir = _create_zimage_fp8_bundle(tmp_path)
        missing_files = [
            "transformer/config.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ]

        pruned = worker._prune_zimage_missing_files(bundle_dir, missing_files)

        assert pruned == [
            "text_encoder/config.json",
            "vae/diffusion_pytorch_model.safetensors",
        ]


def _create_zimage_fp8_bundle(tmp_path: Path) -> Path:
    bundle_dir = tmp_path / "txt2img"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _write_json(bundle_dir / "text_encoder" / "model.safetensors.index.json", {
        "weight_map": {
            "encoder.layers.0.weight": "model-00001-of-00003.safetensors",
            "encoder.layers.1.weight": "model-00002-of-00003.safetensors",
            "encoder.layers.2.weight": "model-00003-of-00003.safetensors",
        }
    })
    _save_tensor(bundle_dir / "lean_fp8_checkpoint.safetensors")
    return bundle_dir


def _save_tensor(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file({"weight": torch.zeros(1)}, str(path))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(data))