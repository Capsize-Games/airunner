"""Service-owned download job coordination for headless clients."""

from __future__ import annotations

import asyncio
import os
import threading
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

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
from airunner_services.downloads.service import download_civitai_file
from airunner_services.llm.utils.model_downloader import (
    DownloadCancelledError,
    HuggingFaceDownloader,
)
from airunner_services.utils.job_tracker import JobState, JobStatus, JobTracker
from airunner_services.utils.zip_utils import safe_extract_zip
from airunner_model.runtimes.file_policy import normalize_local_path


class DownloadJobService:
    """Coordinate provider downloads behind one shared job lifecycle."""

    def __init__(
        self,
        tracker: JobTracker | None = None,
        huggingface_downloader: HuggingFaceDownloader | None = None,
    ) -> None:
        self._tracker = tracker or JobTracker()
        self._huggingface_downloader = (
            huggingface_downloader or HuggingFaceDownloader()
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
            if job.status is JobStatus.COMPLETED:
                return job.result
            if job.status is JobStatus.FAILED:
                raise Exception(job.error or "Job failed")
            if job.status is JobStatus.CANCELLED:
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
        progress = _progress_reporter(job_id, self._tracker)
        try:
            if request.model_type == "gguf" and request.gguf_filename:
                downloaded_path = self._huggingface_downloader.download_gguf_model(
                    request.repo_id,
                    request.gguf_filename,
                    local_dir=request.output_dir,
                    progress_callback=progress,
                    cancel_callback=cancel_event.is_set,
                )
            else:
                downloaded_path = self._huggingface_downloader.download_model(
                    request.repo_id,
                    local_dir=request.output_dir,
                    model_type=request.model_type,
                    include_patterns=request.missing_files,
                    progress_callback=progress,
                    cancel_callback=cancel_event.is_set,
                )
            if cancel_event.is_set():
                self._cancel_job(job_id)
                return
            self._complete_job(
                job_id,
                {
                    "provider": "huggingface",
                    "repo_id": request.repo_id,
                    "model_type": request.model_type,
                    "paths": [str(downloaded_path)],
                },
            )
        except DownloadCancelledError:
            self._cancel_job(job_id)
        except Exception as exc:
            self._fail_job(job_id, str(exc))
        finally:
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
        progress = _civitai_progress_reporter(job_id, self._tracker, 0, 0)
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

    def _update_job(
        self,
        job_id: str,
        progress: float,
        status: JobStatus,
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
    if model_type in {"llm", "ministral3", "gguf"}:
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
    return max(0.0, min(99.0, (float(current) / float(total)) * 100.0))


def _download_filename(url: str) -> str:
    """Return one filesystem filename derived from a URL path."""
    candidate = url.split("?", 1)[0].rstrip("/").split("/")[-1]
    return candidate or "download.bin"


def _progress_reporter(
    job_id: str,
    tracker: JobTracker,
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
    tracker: JobTracker,
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