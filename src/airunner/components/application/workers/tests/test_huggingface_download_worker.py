from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

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

    def test_rmbg_download_uses_bootstrap_output_dir(
        self,
        tmp_path,
        monkeypatch,
    ):
        worker = HuggingFaceDownloadWorker()
        output_dir = tmp_path / "rmbg"
        temp_dir = tmp_path / ".downloading"
        temp_dir.mkdir()
        created_threads = []

        class _Settings:
            def value(self, *_args, **_kwargs):
                return ""

        class _FakeThread:
            def __init__(self, target, args, daemon):
                created_threads.append(
                    {
                        "target": target,
                        "args": args,
                        "daemon": daemon,
                    }
                )

            def start(self):
                return None

        monkeypatch.setattr(
            "airunner.components.application.workers."
            "huggingface_download_worker.get_qsettings",
            lambda: _Settings(),
        )
        monkeypatch.setattr(
            "airunner.components.application.workers."
            "huggingface_download_worker.threading.Thread",
            _FakeThread,
        )
        monkeypatch.setattr(
            worker,
            "_prepare_temp_dir",
            lambda _model_path: temp_dir,
        )
        monkeypatch.setattr(
            worker,
            "_wait_for_completion",
            lambda _count: False,
        )
        monkeypatch.setattr(worker, "emit_signal", Mock())
        worker.downloader.get_model_files = Mock(
            side_effect=AssertionError(
                "RMBG downloads should not fetch the API file list"
            )
        )

        worker._download_model(
            repo_id="briaai/RMBG-2.0",
            model_type="rmbg",
            output_dir=str(output_dir),
        )

        assert worker._model_path == output_dir
        assert {
            thread["args"][1]
            for thread in created_threads
        } == {
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "BiRefNet_config.py",
            "birefnet.py",
        }
        worker.downloader.get_model_files.assert_not_called()


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