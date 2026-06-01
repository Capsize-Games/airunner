"""Service-owned job tracking helpers for asynchronous runtime work."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class JobStatus(Enum):
    """Lifecycle states for one tracked asynchronous job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobState:
    """Track the current state for one asynchronous job."""

    job_id: str
    status: JobStatus
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return one JSON-serializable representation of the job state."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class JobTracker:
    """Track asynchronous jobs across request lifecycles."""

    _instance: Optional["JobTracker"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Return one shared tracker instance for the process."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the tracker once per process."""
        if self._initialized:
            return

        self._jobs: dict[str, JobState] = {}
        self._futures: dict[str, asyncio.Future] = {}
        self._initialized = True
        logger.info("JobTracker initialized")

    async def create_job(
        self,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create one tracked job and return its identifier."""
        async with self._lock:
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = JobState(
                job_id=job_id,
                status=JobStatus.PENDING,
                metadata=metadata or {},
            )
            self._futures[job_id] = asyncio.Future()
            logger.info("Created job %s", job_id)
            return job_id

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        status: Optional[JobStatus] = None,
    ) -> None:
        """Update one job progress value and optional status."""
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning("Job %s not found for progress update", job_id)
                return

            job = self._jobs[job_id]
            job.progress = progress
            if status:
                job.status = status
            job.updated_at = datetime.now()
            logger.debug("Job %s progress: %s%%", job_id, progress)

    async def update_metadata(
        self,
        job_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Merge one metadata update into the tracked job state."""
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning("Job %s not found for metadata update", job_id)
                return

            job = self._jobs[job_id]
            job.metadata.update(metadata)
            job.updated_at = datetime.now()

    async def complete_job(self, job_id: str, result: Any) -> None:
        """Mark one job as complete and resolve any waiting future."""
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning("Job %s not found for completion", job_id)
                return

            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.result = result
            job.updated_at = datetime.now()

            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_result(result)

            logger.info("Job %s completed", job_id)

    async def fail_job(self, job_id: str, error: str) -> None:
        """Mark one job as failed and resolve waiters with one error."""
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning("Job %s not found for failure", job_id)
                return

            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = error
            job.updated_at = datetime.now()

            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_exception(Exception(error))

            logger.error("Job %s failed: %s", job_id, error)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel one pending or running job when possible."""
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning("Job %s not found for cancellation", job_id)
                return False

            job = self._jobs[job_id]
            if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
                logger.info(
                    "Job %s cannot be cancelled (status: %s)",
                    job_id,
                    job.status,
                )
                return False

            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now()
            future = self._futures.get(job_id)
            if future is not None and not future.done():
                future.set_exception(Exception("Job cancelled by user"))

            logger.info("Job %s cancelled", job_id)
            return True

    async def get_status(self, job_id: str) -> Optional[JobState]:
        """Return one tracked job state when it exists."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_result(self, job_id: str, timeout: float = 300.0) -> Any:
        """Return one job result, waiting until completion when needed."""
        async with self._lock:
            if job_id not in self._jobs:
                raise ValueError(f"Job {job_id} not found")

            job = self._jobs[job_id]
            if job.status == JobStatus.COMPLETED:
                return job.result
            if job.status == JobStatus.FAILED:
                raise Exception(job.error or "Job failed")
            if job.status == JobStatus.CANCELLED:
                raise Exception("Job cancelled")

            future = self._futures.get(job_id)
            if future is None:
                raise ValueError(f"Job {job_id} has no future")

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Job %s timed out after %ss", job_id, timeout)
            raise

    async def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> None:
        """Drop old terminal-state jobs from the tracker."""
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for job_id, job in self._jobs.items():
                if job.status not in {
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                }:
                    continue

                age = (now - job.updated_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                self._futures.pop(job_id, None)

            if to_remove:
                logger.info("Cleaned up %s old jobs", len(to_remove))

    def get_all_jobs(self) -> dict[str, JobState]:
        """Return a shallow copy of all tracked jobs."""
        return self._jobs.copy()


__all__ = ["JobState", "JobStatus", "JobTracker"]
