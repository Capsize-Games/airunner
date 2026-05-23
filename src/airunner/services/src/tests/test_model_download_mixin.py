"""Tests for the service-owned LLM model download mixin."""

from __future__ import annotations

from types import SimpleNamespace

from airunner_services.utils.job_tracker import JobState, JobStatus

from airunner_services.llm.workers.mixins.model_download_mixin import (
    ModelDownloadMixin,
)


class FakeDownloadDelegate:
    """Minimal GUI delegate double for download dialog requests."""

    def __init__(self) -> None:
        self.calls = []

    def show_llm_download_dialog(
        self,
        worker,
        model_info,
        model_path,
        repo_id,
        missing_files=None,
    ) -> bool:
        self.calls.append(
            {
                "worker": worker,
                "model_info": model_info,
                "model_path": model_path,
                "repo_id": repo_id,
                "missing_files": missing_files,
            }
        )
        return True


class FakeWorker(ModelDownloadMixin):
    """Small concrete worker for exercising ModelDownloadMixin."""

    def __init__(self) -> None:
        self.logger = SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        )
        self._download_dialog_showing = False
        self._pending_convert_to_gguf = False
        self.download_ui_delegate = None
        self.headless_calls = []

    def _get_model_info(self, repo_id: str):
        return {
            "name": repo_id,
            "model_type": "llm",
            "setup_quantization": False,
            "quantization_bits": 4,
        }

    def _download_headless(
        self,
        model_info,
        model_path,
        repo_id,
        missing_files=None,
    ) -> bool:
        self.headless_calls.append(
            (model_info, model_path, repo_id, missing_files)
        )
        return True


class FakeHeadlessProgress:
    """Small progress tracker double for headless download tests."""

    def __init__(self, model_name: str, model_path: str) -> None:
        self.model_name = model_name
        self.model_path = model_path
        self.logs = []
        self.progress_updates = []
        self.completed = []
        self.failed = []

    def on_log_updated(self, data) -> None:
        self.logs.append(data)

    def on_progress_updated(self, data) -> None:
        self.progress_updates.append(data)

    def on_download_complete(self, data) -> None:
        self.completed.append(data)

    def on_download_failed(self, data) -> None:
        self.failed.append(data)


class FakeHeadlessJobService:
    """Minimal job-service double for headless download tests."""

    instances = []

    def __init__(self) -> None:
        self.started = []
        self._statuses = [
            JobState(
                job_id="job-1",
                status=JobStatus.RUNNING,
                progress=35.0,
            ),
            JobState(
                job_id="job-1",
                status=JobStatus.COMPLETED,
                progress=100.0,
                result={"paths": ["/tmp/models/example-model"]},
            ),
        ]
        self.__class__.instances.append(self)

    def start_huggingface_download_sync(self, **kwargs) -> str:
        self.started.append(kwargs)
        return "job-1"

    def get_status_sync(self, _job_id: str):
        if len(self._statuses) > 1:
            return self._statuses.pop(0)
        return self._statuses[0]


class HeadlessWorker(ModelDownloadMixin):
    """Concrete worker that exercises the real headless download path."""

    def __init__(self) -> None:
        self.logger = SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        )
        self._download_dialog_showing = False
        self.completed = []

    def on_huggingface_download_complete_signal(self, data) -> None:
        self.completed.append(data)
        self._download_dialog_showing = False


def test_model_download_mixin_uses_gui_delegate(monkeypatch) -> None:
    """GUI-capable workers should request dialog presentation via delegate."""
    monkeypatch.setattr(
        "airunner_services.llm.workers.mixins.model_download_mixin."
        "LLMProviderConfig.resolve_download_target",
        lambda *_args, **_kwargs: None,
    )
    worker = FakeWorker()
    delegate = FakeDownloadDelegate()
    worker.download_ui_delegate = delegate

    worker.on_llm_model_download_required_signal(
        {
            "repo_id": "example/model",
            "model_path": "/tmp/model.gguf",
        }
    )

    assert worker.headless_calls == []
    assert worker._download_dialog_showing is True
    assert delegate.calls[0]["worker"] is worker
    assert delegate.calls[0]["repo_id"] == "example/model"


def test_model_download_mixin_falls_back_to_headless(monkeypatch) -> None:
    """Workers without a GUI delegate should use the headless path."""
    monkeypatch.setattr(
        "airunner_services.llm.workers.mixins.model_download_mixin."
        "LLMProviderConfig.resolve_download_target",
        lambda *_args, **_kwargs: None,
    )
    worker = FakeWorker()

    worker.on_llm_model_download_required_signal(
        {
            "repo_id": "example/model",
            "model_path": "/tmp/model.gguf",
            "missing_files": ["config.json"],
        }
    )

    assert worker.headless_calls == [
        (
            {
                "name": "example/model",
                "model_type": "llm",
                "setup_quantization": False,
                "quantization_bits": 4,
            },
            "/tmp/model.gguf",
            "example/model",
            ["config.json"],
        )
    ]


def test_headless_download_uses_download_job_service(monkeypatch) -> None:
    """Headless downloads should poll the shared job service."""
    monkeypatch.setattr(
        "airunner_services.downloads.job_service.DownloadJobService",
        FakeHeadlessJobService,
    )
    monkeypatch.setattr(
        "airunner_services.llm.workers.mixins.model_download_mixin."
        "HeadlessDownloadProgress",
        FakeHeadlessProgress,
    )
    monkeypatch.setattr(
        "airunner_services.llm.workers.mixins.model_download_mixin."
        "time.sleep",
        lambda _seconds: None,
    )

    worker = HeadlessWorker()

    success = worker._download_headless(
        {
            "name": "example/model",
            "model_type": "llm",
            "setup_quantization": False,
            "quantization_bits": 4,
        },
        "/tmp/models/example-model.bin",
        "example/model",
        ["config.json"],
    )

    assert success is True
    assert FakeHeadlessJobService.instances[0].started == [
        {
            "repo_id": "example/model",
            "model_type": "llm",
            "output_dir": "/tmp/models",
            "missing_files": ["config.json"],
            "gguf_filename": None,
        }
    ]
    assert worker.completed == [
        {
            "repo_id": "example/model",
            "model_path": "/tmp/models/example-model",
            "model_type": "llm",
        }
    ]