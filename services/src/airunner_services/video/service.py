"""VideoService: single-flight job queue over a VideoBackend."""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path

from airunner_services.video.config import VideoConfig
from airunner_services.video.contracts import (
    VideoGenerationRequest,
    VideoJobStatus,
    VideoModelInfo,
)
from airunner_services.video.pipeline import VideoBackend


class QueueFullError(RuntimeError):
    """Raised when the pending queue is at capacity (HTTP 429)."""


class JobNotFoundError(KeyError):
    """Raised for unknown job ids (HTTP 404)."""


class VideoService:
    """Owns video jobs; exactly one runs at a time (single GPU)."""

    def __init__(self, config: VideoConfig | None = None,
                 backend: VideoBackend | None = None) -> None:
        self._config = config or VideoConfig.from_env()
        self._backend = backend  # lazily built on first job
        self._jobs: dict[str, VideoJobStatus] = {}
        self._requests: dict[str, VideoGenerationRequest] = {}
        self._outputs: dict[str, Path] = {}
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._cancelled: set[str] = set()

    def _ensure_backend(self) -> VideoBackend:
        if self._backend is None:
            from airunner_services.video.pipeline import (
                LtxDiffusersBackend,
            )

            self._backend = LtxDiffusersBackend(self._config)
        return self._backend

    def submit(self, request: VideoGenerationRequest) -> str:
        """Enqueue a job and return its id; QueueFullError at cap."""
        with self._lock:
            pending = sum(
                1 for j in self._jobs.values()
                if j.status in ("queued", "running")
            )
            if pending > self._config.max_queue:
                raise QueueFullError("video queue is full")
            job_id = uuid.uuid4().hex[:16]
            self._jobs[job_id] = VideoJobStatus(
                job_id=job_id, status="queued"
            )
            self._requests[job_id] = request
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._drain, daemon=True
                )
                self._worker.start()
            return job_id

    def _drain(self) -> None:
        while True:
            with self._lock:
                queued = [
                    j for j in self._jobs.values()
                    if j.status == "queued"
                ]
                if not queued:
                    return
                job = queued[0]
                job.status = "running"
                request = self._requests[job.job_id]
            out_dir = Path(self._config.output_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            out = out_dir / f"{job.job_id}.mp4"
            started = time.perf_counter()
            try:
                if job.job_id in self._cancelled:
                    raise RuntimeError("cancelled")
                result = self._ensure_backend().run(
                    request, out,
                    lambda p: setattr(job, "progress", p),
                )
                job.status = (
                    "cancelled"
                    if job.job_id in self._cancelled
                    else "completed"
                )
                job.wall_time_s = result.wall_time_s
                job.peak_vram_mb = result.peak_vram_mb
                job.peak_rss_mb = result.peak_rss_mb
                job.progress = 1.0
                self._outputs[job.job_id] = result.path
            except Exception as exc:  # surfaced as job error, not crash
                if job.job_id in self._cancelled:
                    job.status = "cancelled"
                else:
                    job.status = "failed"
                    job.error = str(exc)[:500]
                job.wall_time_s = time.perf_counter() - started

    def status(self, job_id: str) -> VideoJobStatus:
        """Return one job's status or raise JobNotFoundError."""
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    def result_path(self, job_id: str) -> Path:
        """Return the finished MP4 path (409 semantics at the route)."""
        job = self.status(job_id)
        if job.status != "completed" or job_id not in self._outputs:
            raise RuntimeError(f"job {job_id} is {job.status}")
        return self._outputs[job_id]

    def cancel(self, job_id: str) -> VideoJobStatus:
        """Mark a job cancelled (best-effort for a running job)."""
        job = self.status(job_id)
        self._cancelled.add(job_id)
        if job.status == "queued":
            job.status = "cancelled"
        return job

    def list_models(self) -> list[VideoModelInfo]:
        """List known checkpoints with install state + VRAM estimate."""
        specs = [("fp8", "FP8 E4M3", 13500.0),
                 ("nvfp4", "NVFP4", 9500.0)]
        return [
            VideoModelInfo(
                checkpoint=name, precision=precision,
                path=str(self._config.checkpoint_dir(name)),
                installed=self._config.checkpoint_dir(name).is_dir(),
                estimated_peak_vram_mb=estimate,
            )
            for name, precision, estimate in specs
        ]
