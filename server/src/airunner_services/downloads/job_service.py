"""Service-owned download job coordination for headless clients."""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

try:
    import nltk
except ImportError:
    nltk = None

from airunner_services.settings import MODELS_DIR
from airunner_services.config.local_settings_store import get_setting
from airunner_services.downloads.civitai import (
    fetch_model_info_for_url,
    get_files_to_download,
    sanitize_filename,
    select_version,
)
from airunner_services.downloads.huggingface import (
    HuggingFaceDownloadRequest,
    prepare_huggingface_download_request,
)
from airunner_services.contract_enums import SignalCode as WorkerSignalCode
from airunner_services.downloads.huggingface_download_worker import (
    HuggingFaceDownloadWorker as ServiceHuggingFaceDownloadWorker,
)
from airunner_services.downloads.service import download_civitai_file
from airunner_services.llm.utils.model_downloader import (
    DownloadCancelledError,
    HuggingFaceDownloader as SimpleHuggingFaceDownloader,
)
from airunner_services.downloads.persistent_job_tracker import (
    JobState,
    JobStatus,
    PersistentJobTracker,
)
from airunner_services.utils.zip_utils import safe_extract_zip
from airunner_services.runtimes.file_policy import normalize_local_path


class DownloadJobService:
    """Coordinate provider downloads behind one shared job lifecycle."""

    def __init__(
        self,
        tracker: PersistentJobTracker | None = None,
        huggingface_downloader: SimpleHuggingFaceDownloader | None = None,
        huggingface_worker_factory: (
            Callable[[], ServiceHuggingFaceDownloadWorker] | None
        ) = None,
    ) -> None:
        self._tracker = tracker or PersistentJobTracker()
        self._huggingface_downloader = (
            huggingface_downloader or SimpleHuggingFaceDownloader()
        )
        self._huggingface_worker_factory = (
            huggingface_worker_factory or ServiceHuggingFaceDownloadWorker
        )
        self._cancel_events: dict[str, threading.Event] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()

    async def start_huggingface_download(
        self,
        repo_id: str,
        *,
        model_type: str = "llm",
        output_dir: str | None = None,
        missing_files: list[str] | None = None,
        gguf_filename: str | None = None,
        prefer_pre_quantized: bool = True,
    ) -> str:
        """Create and start one HuggingFace download job."""
        request = prepare_huggingface_download_request(
            repo_id=repo_id,
            model_type=model_type,
            output_dir=output_dir,
            missing_files=missing_files,
            gguf_filename=gguf_filename,
            prefer_pre_quantized=prefer_pre_quantized,
        )
        resolved_output_dir = request.output_dir or _default_hf_output_dir(
            request.repo_id,
            request.model_type,
        )
        normalized_request = replace(
            request,
            output_dir=normalize_local_path(
                resolved_output_dir,
                label="Download output directory",
            ),
        )
        metadata = {
            "provider": "huggingface",
            "repo_id": normalized_request.repo_id,
            "model_type": normalized_request.model_type,
        }
        return await self._start_job(
            metadata,
            self._run_huggingface_job,
            normalized_request,
        )

    async def start_huggingface_file_download(
        self,
        repo_id: str,
        filename: str,
        *,
        output_dir: str,
    ) -> str:
        """Create and start one single-file HuggingFace download job."""
        normalized_output_dir = normalize_local_path(
            output_dir,
            label="Download output directory",
        )
        metadata = {
            "provider": "huggingface",
            "repo_id": repo_id,
            "filename": filename,
        }
        return await self._start_job(
            metadata,
            self._run_huggingface_file_job,
            repo_id,
            filename,
            normalized_output_dir,
        )

    async def start_civitai_model_download(
        self,
        url: str,
        *,
        output_dir: str | None = None,
        api_key: str | None = None,
    ) -> str:
        """Create and start one CivitAI model download job."""
        resolved_output_dir = normalize_local_path(
            output_dir or os.path.join(MODELS_DIR, "art/models/civitai"),
            label="Download output directory",
        )
        metadata = {"provider": "civitai", "url": url}
        return await self._start_job(
            metadata,
            self._run_civitai_model_job,
            url,
            resolved_output_dir,
            api_key or get_setting("civitai/api_key", ""),
        )

    async def start_civitai_file_download(
        self,
        url: str,
        *,
        output_path: str,
        file_size: int,
        api_key: str | None = None,
    ) -> str:
        """Create and start one CivitAI single-file download job."""
        normalized_output_path = normalize_local_path(
            output_path,
            label="Download file path",
        )
        metadata = {"provider": "civitai", "url": url}
        return await self._start_job(
            metadata,
            self._run_civitai_file_job,
            url,
            normalized_output_path,
            max(0, int(file_size)),
            api_key or get_setting("civitai/api_key", ""),
        )

    async def start_url_download(
        self,
        url: str,
        *,
        output_dir: str,
        filename: str | None = None,
        extract_zip: bool = False,
    ) -> str:
        """Create and start one generic URL download job."""
        normalized_output_dir = normalize_local_path(
            output_dir,
            label="Download output directory",
        )
        resolved_filename = filename or _download_filename(url)
        metadata = {"provider": "url", "url": url}
        return await self._start_job(
            metadata,
            self._run_url_download_job,
            url,
            normalized_output_dir,
            resolved_filename,
            extract_zip,
        )

    async def start_nltk_download(self, data_names: list[str]) -> str:
        """Create and start one NLTK data download job."""
        resolved_names = [
            name.strip() for name in data_names if str(name).strip()
        ]
        if not resolved_names:
            raise ValueError("At least one NLTK data name is required")
        metadata = {
            "provider": "nltk",
            "data_names": resolved_names,
        }
        return await self._start_job(
            metadata,
            self._run_nltk_download_job,
            resolved_names,
        )

    async def get_status(self, job_id: str) -> JobState | None:
        """Return the tracked state for one download job."""
        return await self._tracker.get_status(job_id)

    async def get_result(
        self,
        job_id: str,
        timeout: float = 300.0,
    ) -> Any:
        """Return the terminal result for one download job."""
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            job = await self._tracker.get_status(job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")
            if job.status == JobStatus.COMPLETED:
                return job.result
            if job.status == JobStatus.FAILED:
                raise Exception(job.error or "Job failed")
            if job.status == JobStatus.CANCELLED:
                raise Exception("Job cancelled")
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Job {job_id} timed out")
            await asyncio.sleep(0.05)

    async def cancel(self, job_id: str) -> bool:
        """Request cancellation for one running download job."""
        with self._lock:
            cancel_event = self._cancel_events.get(job_id)
        if cancel_event is not None:
            cancel_event.set()
        return await self._tracker.cancel_job(job_id)

    def start_huggingface_download_sync(self, *args: Any, **kwargs: Any) -> str:
        """Synchronously create one HuggingFace download job."""
        return asyncio.run(self.start_huggingface_download(*args, **kwargs))

    def start_huggingface_file_download_sync(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Synchronously create one single-file HuggingFace download job."""
        return asyncio.run(self.start_huggingface_file_download(*args, **kwargs))

    def start_civitai_file_download_sync(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Synchronously create one single-file CivitAI download job."""
        return asyncio.run(self.start_civitai_file_download(*args, **kwargs))

    def start_url_download_sync(self, *args: Any, **kwargs: Any) -> str:
        """Synchronously create one generic URL download job."""
        return asyncio.run(self.start_url_download(*args, **kwargs))

    def start_nltk_download_sync(self, *args: Any, **kwargs: Any) -> str:
        """Synchronously create one NLTK data download job."""
        return asyncio.run(self.start_nltk_download(*args, **kwargs))

    def get_status_sync(self, job_id: str) -> JobState | None:
        """Synchronously return the status for one tracked job."""
        return asyncio.run(self.get_status(job_id))

    def cancel_sync(self, job_id: str) -> bool:
        """Synchronously cancel one tracked job."""
        return asyncio.run(self.cancel(job_id))

    async def _start_job(
        self,
        metadata: dict[str, Any],
        runner: Callable[..., None],
        *args: Any,
    ) -> str:
        """Create one tracked job and start its background runner."""
        job_id = await self._tracker.create_job(metadata=metadata)
        cancel_event = threading.Event()
        thread = threading.Thread(
            target=runner,
            args=(job_id, cancel_event, *args),
            daemon=True,
        )
        with self._lock:
            self._cancel_events[job_id] = cancel_event
            self._threads[job_id] = thread
        thread.start()
        return job_id

    def _run_huggingface_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        request: HuggingFaceDownloadRequest,
    ) -> None:
        """Run one HuggingFace download inside a background thread."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        worker = self._huggingface_worker_factory()
        completion: dict[str, Any] | None = None
        failure: str | None = None
        stop_watch = threading.Event()

        def handle_signal(code: object, data: dict[str, Any] | None = None) -> None:
            nonlocal completion, failure
            payload = data or {}
            if code == WorkerSignalCode.UPDATE_DOWNLOAD_LOG:
                self._record_log_message(job_id, str(payload.get("message") or ""))
                return
            if code == WorkerSignalCode.UPDATE_DOWNLOAD_PROGRESS:
                progress = float(payload.get("progress") or 0.0)
                self._update_job(job_id, progress, JobStatus.RUNNING)
                return
            if code == WorkerSignalCode.UPDATE_FILE_DOWNLOAD_PROGRESS:
                self._record_file_progress(
                    job_id,
                    str(payload.get("filename") or ""),
                    int(payload.get("downloaded") or 0),
                    int(payload.get("total") or 0),
                )
                return
            if code == WorkerSignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE:
                completion = payload
                return
            if code == WorkerSignalCode.HUGGINGFACE_DOWNLOAD_FAILED:
                failure = str(payload.get("error") or "Download failed")

        def watch_cancel() -> None:
            while not stop_watch.is_set():
                if cancel_event.is_set():
                    worker.is_cancelled = True
                    return
                time.sleep(0.05)

        worker.emit_signal = handle_signal  # type: ignore[method-assign]
        cancel_watcher = threading.Thread(target=watch_cancel, daemon=True)
        cancel_watcher.start()
        try:
            worker.handle_message(request.as_payload())
            if cancel_event.is_set() or worker.is_cancelled:
                self._cancel_job(job_id)
                return
            if failure is not None:
                self._fail_job(job_id, failure)
                return
            if completion is None:
                self._fail_job(
                    job_id,
                    "Download ended without completion signal",
                )
                return
            model_path = str(completion.get("model_path") or request.output_dir or "")
            self._complete_job(
                job_id,
                {
                    "provider": "huggingface",
                    "repo_id": str(
                        completion.get("repo_id") or request.repo_id
                    ),
                    "model_type": str(
                        completion.get("model_type") or request.model_type
                    ),
                    "paths": [model_path] if model_path else [],
                    "pipeline_action": completion.get("pipeline_action"),
                },
            )
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            stop_watch.set()
            cancel_watcher.join(timeout=0.1)
            self._forget_job(job_id)

    def _run_huggingface_file_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        repo_id: str,
        filename: str,
        output_dir: str,
    ) -> None:
        """Run one single-file HuggingFace download inside a background thread."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        self._record_log_message(job_id, f"Starting download: {filename}")
        last_progress = -1.0

        def progress(downloaded: int, total: int) -> None:
            nonlocal last_progress
            current_progress = _coerce_progress(downloaded, total)
            if current_progress < 100.0 and current_progress - last_progress < 1.0:
                return
            last_progress = current_progress
            asyncio.run(
                self._tracker.update_progress(
                    job_id,
                    current_progress,
                    JobStatus.RUNNING,
                )
            )
            self._record_file_progress(
                job_id,
                filename,
                downloaded,
                total,
            )

        try:
            path = self._huggingface_downloader.download_file(
                repo_id,
                filename,
                output_dir,
                progress_callback=progress,
                cancel_callback=cancel_event.is_set,
            )
            self._complete_job(
                job_id,
                {
                    "provider": "huggingface",
                    "repo_id": repo_id,
                    "filename": filename,
                    "paths": [str(path)],
                },
            )
        except DownloadCancelledError:
            self._cancel_job(job_id)
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            self._forget_job(job_id)

    def _run_civitai_model_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        url: str,
        output_dir: str,
        api_key: str,
    ) -> None:
        """Run one CivitAI model download inside a background thread."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        try:
            model_info = fetch_model_info_for_url(url, api_key)
            version = model_info.get("selectedVersion") or select_version(
                model_info
            )
            if version is None:
                raise ValueError("No CivitAI model version available")
            model_name = sanitize_filename(
                str(model_info.get("name") or "civitai_model")
            )
            model_path = Path(output_dir) / model_name
            files_to_download = get_files_to_download(version, model_path)
            total_size = sum(
                max(0, int(file_info.get("size") or 0))
                for file_info in files_to_download
            )
            downloaded_size = 0
            downloaded_paths = []
            for file_info in files_to_download:
                file_total = max(0, int(file_info.get("size") or 0))
                progress = _civitai_progress_reporter(
                    job_id,
                    self._tracker,
                    downloaded_size,
                    total_size,
                )
                completed = download_civitai_file(
                    file_info["url"],
                    model_path / file_info["filename"],
                    file_total,
                    api_key=api_key,
                    progress_callback=progress,
                    cancel_callback=cancel_event.is_set,
                )
                if not completed or cancel_event.is_set():
                    self._cancel_job(job_id)
                    return
                downloaded_size += file_total
                downloaded_paths.append(
                    str(model_path / file_info["filename"])
                )
            if not files_to_download:
                downloaded_paths.append(str(model_path))
            self._complete_job(
                job_id,
                {
                    "provider": "civitai",
                    "url": url,
                    "model_name": model_name,
                    "paths": downloaded_paths,
                },
            )
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            self._forget_job(job_id)

    def _run_civitai_file_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        url: str,
        output_path: str,
        file_size: int,
        api_key: str,
    ) -> None:
        """Run one CivitAI file download inside a background thread."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        progress = _civitai_progress_reporter(
            job_id,
            self._tracker,
            0,
            file_size,
        )
        try:
            completed = download_civitai_file(
                url,
                output_path,
                file_size,
                api_key=api_key,
                progress_callback=progress,
                cancel_callback=cancel_event.is_set,
            )
            if not completed or cancel_event.is_set():
                self._cancel_job(job_id)
                return
            self._complete_job(
                job_id,
                {
                    "provider": "civitai",
                    "url": url,
                    "paths": [output_path],
                },
            )
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            self._forget_job(job_id)

    def _run_url_download_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        url: str,
        output_dir: str,
        filename: str,
        extract_zip: bool,
    ) -> None:
        """Run one generic URL download, optionally extracting a ZIP."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / filename
        self._record_log_message(job_id, f"Starting download: {filename}")
        last_progress = -1.0

        def progress(downloaded: int, total: int) -> None:
            nonlocal last_progress
            current_progress = _coerce_progress(downloaded, total)
            if current_progress < 100.0 and current_progress - last_progress < 1.0:
                return
            last_progress = current_progress
            self._update_job(job_id, current_progress, JobStatus.RUNNING)
            self._record_file_progress(
                job_id,
                filename,
                downloaded,
                total,
            )

        try:
            completed = download_civitai_file(
                url,
                output_path,
                0,
                progress_callback=progress,
                cancel_callback=cancel_event.is_set,
            )
            if not completed or cancel_event.is_set():
                self._cancel_job(job_id)
                return
            if extract_zip:
                self._record_log_message(job_id, f"Extracting {filename}...")
                with zipfile.ZipFile(output_path, "r") as archive:
                    safe_extract_zip(archive, output_root)
                output_path.unlink(missing_ok=True)
                paths = [output_dir]
            else:
                paths = [str(output_path)]
            self._complete_job(
                job_id,
                {
                    "provider": "url",
                    "url": url,
                    "paths": paths,
                },
            )
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            self._forget_job(job_id)

    def _record_log_message(self, job_id: str, message: str) -> None:
        """Persist one user-facing log message into job metadata."""
        if not message:
            return
        self._update_job_metadata(
            job_id,
            {"last_log_message": message},
        )

    def _record_file_progress(
        self,
        job_id: str,
        filename: str,
        downloaded: int,
        total: int,
    ) -> None:
        """Persist one file-progress update into job metadata."""
        if not filename:
            return
        self._update_job_metadata(
            job_id,
            {
                "file_progress": {
                    "filename": filename,
                    "downloaded": max(0, int(downloaded)),
                    "total": max(0, int(total)),
                }
            },
        )

    def _update_job_metadata(
        self,
        job_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Push one metadata update into the shared tracker."""
        asyncio.run(self._tracker.update_metadata(job_id, metadata))

    def _run_nltk_download_job(
        self,
        job_id: str,
        cancel_event: threading.Event,
        data_names: list[str],
    ) -> None:
        """Run one NLTK data download job inside a background thread."""
        self._update_job(job_id, 0.0, JobStatus.RUNNING)
        if nltk is None:
            self._fail_job(job_id, "NLTK is not installed")
            self._forget_job(job_id)
            return

        original_limit = sys.getrecursionlimit()
        total = max(1, len(data_names))
        downloaded_names: list[str] = []

        try:
            sys.setrecursionlimit(1500)
            for index, data_name in enumerate(data_names, start=1):
                if cancel_event.is_set():
                    self._cancel_job(job_id)
                    return

                completed = bool(nltk.download(data_name, quiet=True))
                if not completed:
                    raise RuntimeError(
                        f"Failed to download NLTK {data_name}"
                    )

                downloaded_names.append(data_name)
                progress = min(99.0, (float(index) / float(total)) * 100.0)
                self._update_job(job_id, progress, JobStatus.RUNNING)

            if cancel_event.is_set():
                self._cancel_job(job_id)
                return

            self._complete_job(
                job_id,
                {
                    "provider": "nltk",
                    "data_names": downloaded_names,
                },
            )
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
            sys.setrecursionlimit(original_limit)
            self._forget_job(job_id)

    def _update_job(
        self,
        job_id: str,
        progress: float,
        status: str,
    ) -> None:
        """Push one status update into the shared tracker."""
        asyncio.run(self._tracker.update_progress(job_id, progress, status))

    def _complete_job(self, job_id: str, result: dict[str, Any]) -> None:
        """Mark one job as complete in the shared tracker."""
        asyncio.run(self._tracker.complete_job(job_id, result))

    def _fail_job(self, job_id: str, error: str) -> None:
        """Mark one job as failed in the shared tracker."""
        asyncio.run(self._tracker.fail_job(job_id, error))

    def _cancel_job(self, job_id: str) -> None:
        """Mark one job as cancelled in the shared tracker."""
        asyncio.run(self._tracker.cancel_job(job_id))

    def _forget_job(self, job_id: str) -> None:
        """Drop one finished thread and cancel token from local state."""
        with self._lock:
            self._cancel_events.pop(job_id, None)
            self._threads.pop(job_id, None)


def _default_hf_output_dir(repo_id: str, model_type: str) -> str:
    """Return the shared local output directory for one HF model type."""
    model_name = repo_id.split("/")[-1]
    if model_type in {"llm", "gguf"}:
        return os.path.join(MODELS_DIR, "text/models/llm/causallm", model_name)
    if model_type == "art":
        return os.path.join(MODELS_DIR, "art/models", model_name)
    if model_type == "tts":
        return os.path.join(MODELS_DIR, "text/models/tts", model_name)
    if model_type == "stt":
        return os.path.join(MODELS_DIR, "text/models/stt", model_name)
    if model_type == "embedding":
        return os.path.join(MODELS_DIR, "text/models/llm/embedding", model_name)
    return os.path.join(MODELS_DIR, "models", model_name)


def _coerce_progress(current: int, total: int) -> float:
    """Return one normalized progress percentage."""
    if total <= 0:
        return 0.0
    return max(0.0, min(100.0, (float(current) / float(total)) * 100.0))


def _download_filename(url: str) -> str:
    """Return one filesystem filename derived from a URL path."""
    candidate = url.split("?", 1)[0].rstrip("/").split("/")[-1]
    return candidate or "download.bin"


def _progress_reporter(
    job_id: str,
    tracker: PersistentJobTracker,
) -> Callable[[str, int, int], None]:
    """Return one throttled HF progress callback."""
    last_progress = -1.0

    def report(_filename: str, downloaded: int, total: int) -> None:
        nonlocal last_progress
        progress = _coerce_progress(downloaded, total)
        if progress < 100.0 and progress - last_progress < 1.0:
            return
        last_progress = progress
        asyncio.run(tracker.update_progress(job_id, progress, JobStatus.RUNNING))

    return report


def _civitai_progress_reporter(
    job_id: str,
    tracker: PersistentJobTracker,
    completed_bytes: int,
    total_bytes: int,
) -> Callable[[int, int], None]:
    """Return one throttled CivitAI progress callback."""
    last_progress = -1.0

    def report(downloaded: int, total: int) -> None:
        nonlocal last_progress
        overall_total = total_bytes or total
        overall_progress = _coerce_progress(completed_bytes + downloaded, overall_total)
        if overall_progress < 100.0 and overall_progress - last_progress < 1.0:
            return
        last_progress = overall_progress
        asyncio.run(
            tracker.update_progress(job_id, overall_progress, JobStatus.RUNNING)
        )

    return report


__all__ = ["DownloadJobService"]