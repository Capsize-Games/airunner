from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from airunner.components.application.workers.huggingface_download_worker import (
    HuggingFaceDownloadWorker,
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