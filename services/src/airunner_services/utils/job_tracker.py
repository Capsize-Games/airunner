"""Service-owned job tracking helpers for asynchronous runtime work."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from airunner_common.settings import AIRUNNER_LOG_LEVEL
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
    execution_finished: bool = True

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
            "execution_finished": self.execution_finished,
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
        # Art generation is a physical, long-running resource.  Keep its
        # reservation until the runtime call and result handling really end,
        # even when the HTTP job has already been marked cancelled.
        self._art_slots: set[str] = set()
        self._art_tasks: dict[str, asyncio.Task] = {}
        self._art_clients: dict[str, Any] = {}
        self._cleanup_tasks: set[asyncio.Task] = set()
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

    async def create_art_job(
        self,
        metadata: Optional[dict[str, Any]] = None,
        *,
        capacity: int = 1,
    ) -> Optional[str]:
        """Atomically create an art job if provider capacity is available."""
        async with self._lock:
            if len(self._art_slots) >= capacity:
                return None
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = JobState(
                job_id=job_id,
                status=JobStatus.PENDING,
                metadata=metadata or {},
                execution_finished=False,
            )
            self._futures[job_id] = asyncio.Future()
            self._art_slots.add(job_id)
            logger.info("Created reserved art job %s", job_id)
            return job_id

    def attach_art_task(self, job_id: str, task: asyncio.Task, client: Any) -> None:
        """Retain the job task and runtime client for supervised shutdown."""
        self._art_tasks[job_id] = task
        self._art_clients[job_id] = client

    def bind_art_client(self, job_id: str, client: Any) -> None:
        """Retain the runtime client while an admitted job is preparing."""
        self._art_clients[job_id] = client

    async def finish_art_job(self, job_id: str) -> None:
        """Release capacity only after the job runner actually terminates."""
        async with self._lock:
            self._art_slots.discard(job_id)
            job = self._jobs.get(job_id)
            if job is not None:
                job.execution_finished = True
            self._art_tasks.pop(job_id, None)
            self._art_clients.pop(job_id, None)

    async def mark_art_job_running(self, job_id: str) -> bool:
        """Atomically start a pending art job before its runner is attached."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status is not JobStatus.PENDING:
                return False
            job.status = JobStatus.RUNNING
            job.progress = 1.0
            job.updated_at = datetime.now()
            return True

    async def discard_art_job(self, job_id: str) -> None:
        """Remove an admitted job that failed before its ID was returned."""
        async with self._lock:
            self._art_slots.discard(job_id)
            self._art_tasks.pop(job_id, None)
            self._art_clients.pop(job_id, None)
            self._jobs.pop(job_id, None)
            future = self._futures.pop(job_id, None)
            if future is not None and not future.done():
                future.cancel()

    async def shutdown_art_jobs(self, timeout: float = 30.0) -> None:
        """Request cancellation and wait without abandoning runtime threads.

        A timed-out task remains retained and keeps its capacity reservation;
        asyncio.wait does not cancel the runner or its underlying worker call.
        """
        async with self._lock:
            active = [
                (
                    job_id,
                    self._art_clients.get(job_id),
                    self._art_tasks.get(job_id),
                )
                for job_id in self._art_slots
                if self._jobs.get(job_id) is not None
            ]
        for job_id, _client, _task in active:
            await self.cancel_job(job_id)

        async def _cancel(client: Any, job_id: str) -> None:
            if client is None:
                return
            cancel = getattr(client, "cancel", None)
            if callable(cancel):
                await asyncio.to_thread(cancel, job_id)

        async def _cancel_all() -> None:
            await asyncio.gather(
                *(_cancel(client, job_id) for job_id, client, _ in active),
                return_exceptions=True,
            )

        cancel_task = asyncio.create_task(_cancel_all())
        self._cleanup_tasks.add(cancel_task)
        cancel_task.add_done_callback(self._cleanup_tasks.discard)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        _done, cancel_pending = await asyncio.wait(
            {cancel_task}, timeout=min(timeout, 5.0)
        )
        if cancel_pending:
            logger.error(
                "Art runtime cancellation requests remain active during "
                "shutdown; cleanup continues in the background"
            )
        tasks = [task for _, _, task in active if task is not None and not task.done()]
        if tasks:
            _done, pending = await asyncio.wait(
                tasks, timeout=max(0.0, deadline - loop.time())
            )
            if pending:
                logger.error(
                    "Art jobs remain active during shutdown (count=%d); "
                    "their reservations remain held",
                    len(pending),
                )

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
            if job.status in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            }:
                return
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
            if job.status in {
                JobStatus.CANCELLED,
                JobStatus.FAILED,
                JobStatus.COMPLETED,
            }:
                return
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
            if job.status in {
                JobStatus.CANCELLED,
                JobStatus.FAILED,
                JobStatus.COMPLETED,
            }:
                return
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
                if job_id in self._art_slots:
                    future.cancel()
                else:
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
                if job_id in self._art_slots:
                    continue
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
