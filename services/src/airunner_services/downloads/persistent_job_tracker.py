"""File-backed job tracker that survives server restarts."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class JobStatus:
    """Enum-compatible status constants (string values)."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

_JOBS_DIR = os.path.join("/tmp", "airunner", "download_jobs")
_TERMINAL_MAX_AGE = 3600  # clean up terminal jobs after 1 hour


@dataclass
class JobState:
    """Serializable state for one tracked download job."""

    job_id: str
    status: str  # pending | running | completed | failed | cancelled | interrupted
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class PersistentJobTracker:
    """Track async jobs across server restarts via file persistence.

    On init, any ``running`` jobs left by a previous process are
    marked as ``interrupted`` so clients know the server restarted.
    Terminal-state jobs (completed / failed / cancelled) older than
    1 hour are cleaned up automatically.
    """

    _instance: Optional["PersistentJobTracker"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._jobs: dict[str, JobState] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._initialized = True
        os.makedirs(_JOBS_DIR, exist_ok=True)
        self._reload_from_disk()
        logger.info(
            "PersistentJobTracker initialized (%d jobs restored)",
            len(self._jobs),
        )

    def _job_path(self, job_id: str) -> str:
        return os.path.join(_JOBS_DIR, self._safe_name(job_id))

    @staticmethod
    def _safe_name(name: str) -> str:
        return name.replace("/", "_").replace("\\", "_") + ".json"

    def _save_to_disk(self, job: JobState) -> None:
        path = self._job_path(job.job_id)
        try:
            with open(path, "w") as fh:
                json.dump({
                    "job_id": job.job_id,
                    "status": job.status,
                    "progress": job.progress,
                    "result": job.result,
                    "error": job.error,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "metadata": job.metadata,
                }, fh)
        except OSError:
            pass

    def _delete_from_disk(self, job_id: str) -> None:
        path = self._job_path(job_id)
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass

    def _reload_from_disk(self) -> None:
        """Load all persisted jobs; mark ``running`` as ``interrupted``."""
        now_ts = time.time()
        to_clean: list[str] = []
        try:
            for fname in os.listdir(_JOBS_DIR):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(_JOBS_DIR, fname)
                try:
                    with open(path, "r") as fh:
                        data = json.load(fh)
                except (OSError, json.JSONDecodeError):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                    continue

                job_id = data.get("job_id", fname[:-5])
                status = data.get("status", "interrupted")
                # Clean up old terminal jobs
                if status in ("completed", "failed", "cancelled"):
                    try:
                        updated = data.get("updated_at", "")
                        if updated:
                            parsed = datetime.fromisoformat(updated)
                            age = parsed.timestamp()
                            if now_ts - age > _TERMINAL_MAX_AGE:
                                to_clean.append(job_id)
                                continue
                    except (ValueError, TypeError):
                        to_clean.append(job_id)
                        continue

                # Mark running jobs as interrupted
                if status == "running":
                    status = "interrupted"
                    data["error"] = (
                        "Server restarted while download was in progress"
                    )

                job = JobState(
                    job_id=job_id,
                    status=status,
                    progress=data.get("progress", 0.0),
                    result=data.get("result"),
                    error=data.get("error"),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    metadata=data.get("metadata", {}),
                )
                self._jobs[job_id] = job

                # Update on disk if we changed it
                if status != data.get("status"):
                    self._save_to_disk(job)

        except OSError:
            pass

        for jid in to_clean:
            self._delete_from_disk(jid)
            self._jobs.pop(jid, None)

    # ── Public API ──

    async def create_job(
        self,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        async with self._lock:
            job_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            job = JobState(
                job_id=job_id,
                status="pending",
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
            self._jobs[job_id] = job
            self._futures[job_id] = asyncio.Future()
            self._save_to_disk(job)
            logger.info("Created job %s", job_id)
            return job_id

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        status: Optional[str] = None,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.progress = progress
            if status:
                job.status = status
            job.updated_at = datetime.now().isoformat()
            self._save_to_disk(job)

    async def update_metadata(
        self,
        job_id: str,
        metadata: dict[str, Any],
    ) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.metadata.update(metadata)
            job.updated_at = datetime.now().isoformat()
            self._save_to_disk(job)

    async def complete_job(self, job_id: str, result: Any) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "completed"
            job.progress = 100.0
            job.result = result
            job.updated_at = datetime.now().isoformat()
            self._save_to_disk(job)
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_result(result)
            logger.info("Job %s completed", job_id)

    async def fail_job(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.error = error
            job.updated_at = datetime.now().isoformat()
            self._save_to_disk(job)
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_exception(Exception(error))
            logger.error("Job %s failed: %s", job_id, error)

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status not in ("pending", "running", "interrupted"):
                return False
            job.status = "cancelled"
            job.updated_at = datetime.now().isoformat()
            self._save_to_disk(job)
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_exception(Exception("Job cancelled by user"))
            logger.info("Job %s cancelled", job_id)
            return True

    async def get_status(self, job_id: str) -> Optional[JobState]:
        async with self._lock:
            return self._jobs.get(job_id)


__all__ = ["JobState", "PersistentJobTracker"]
