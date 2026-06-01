"""
Job tracking system for asynchronous API operations.

Used by art generation, TTS, and other long-running operations that need
to report progress and return results asynchronously.
"""

import asyncio
import uuid
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class JobStatus(Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobState:
    """
    Job state container.

    Attributes:
        job_id: Unique job identifier
        status: Current job status
        progress: Progress percentage (0-100)
        result: Result data (available when completed)
        error: Error message (available when failed)
        created_at: Job creation timestamp
        updated_at: Last update timestamp
        metadata: Additional job metadata
    """

    job_id: str
    status: JobStatus
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job state to dictionary.

        Returns:
            Dictionary representation
        """
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
    """
    Tracks asynchronous job state for API operations.

    This class provides a singleton-like interface for managing job lifecycle:
    - Create jobs with unique IDs
    - Update progress/status
    - Store results/errors
    - Retrieve job state
    - Cancel running jobs

    Thread-safe for use with FastAPI and Qt signal handlers.
    """

    _instance: Optional["JobTracker"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        """Singleton pattern for global job tracking."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize job tracker (only once)."""
        if self._initialized:
            return

        self._jobs: Dict[str, JobState] = {}
        self._futures: Dict[str, asyncio.Future] = {}
        self._initialized = True
        logger.info("JobTracker initialized")

    async def create_job(
        self, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new job.

        Args:
            metadata: Optional job metadata

        Returns:
            Job ID (UUID string)
        """
        async with self._lock:
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = JobState(
                job_id=job_id,
                status=JobStatus.PENDING,
                metadata=metadata or {},
            )
            self._futures[job_id] = asyncio.Future()
            logger.info(f"Created job {job_id}")
            return job_id

    async def update_progress(
        self, job_id: str, progress: float, status: Optional[JobStatus] = None
    ):
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            status: Optional new status
        """
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found for progress update")
                return

            job = self._jobs[job_id]
            job.progress = progress
            if status:
                job.status = status
            job.updated_at = datetime.now()

            logger.debug(f"Job {job_id} progress: {progress}%")

    async def complete_job(self, job_id: str, result: Any):
        """
        Mark job as completed with result.

        Args:
            job_id: Job ID
            result: Job result data
        """
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found for completion")
                return

            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.result = result
            job.updated_at = datetime.now()

            # Resolve future if waiting
            if job_id in self._futures and not self._futures[job_id].done():
                self._futures[job_id].set_result(result)

            logger.info(f"Job {job_id} completed")

    async def fail_job(self, job_id: str, error: str):
        """
        Mark job as failed with error.

        Args:
            job_id: Job ID
            error: Error message
        """
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found for failure")
                return

            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = error
            job.updated_at = datetime.now()

            # Resolve future if waiting
            if job_id in self._futures and not self._futures[job_id].done():
                self._futures[job_id].set_exception(Exception(error))

            logger.error(f"Job {job_id} failed: {error}")

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        async with self._lock:
            if job_id not in self._jobs:
                logger.warning(f"Job {job_id} not found for cancellation")
                return False

            job = self._jobs[job_id]

            # Can only cancel pending/running jobs
            if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
                logger.info(
                    f"Job {job_id} cannot be cancelled (status: {job.status})"
                )
                return False

            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now()

            # Resolve future if waiting
            if job_id in self._futures and not self._futures[job_id].done():
                self._futures[job_id].set_exception(
                    Exception("Job cancelled by user")
                )

            logger.info(f"Job {job_id} cancelled")
            return True

    async def get_status(self, job_id: str) -> Optional[JobState]:
        """
        Get job status.

        Args:
            job_id: Job ID

        Returns:
            JobState if found, None otherwise
        """
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_result(self, job_id: str, timeout: float = 300.0) -> Any:
        """
        Get job result (waits for completion if pending/running).

        Args:
            job_id: Job ID
            timeout: Timeout in seconds

        Returns:
            Job result

        Raises:
            asyncio.TimeoutError: If job doesn't complete within timeout
            Exception: If job fails or is cancelled
        """
        # Check if job exists
        async with self._lock:
            if job_id not in self._jobs:
                raise ValueError(f"Job {job_id} not found")

            job = self._jobs[job_id]

            # If already completed, return result immediately
            if job.status == JobStatus.COMPLETED:
                return job.result

            # If failed/cancelled, raise error immediately
            if job.status == JobStatus.FAILED:
                raise Exception(job.error or "Job failed")
            if job.status == JobStatus.CANCELLED:
                raise Exception("Job cancelled")

            # Otherwise, wait for future
            future = self._futures.get(job_id)
            if not future:
                raise ValueError(f"Job {job_id} has no future")

        # Wait outside lock
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Job {job_id} timed out after {timeout}s")
            raise

    async def cleanup_old_jobs(self, max_age_seconds: int = 3600):
        """
        Clean up old completed/failed jobs.

        Args:
            max_age_seconds: Maximum age for jobs to keep (default 1 hour)
        """
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for job_id, job in self._jobs.items():
                # Only clean up terminal states
                if job.status not in [
                    JobStatus.COMPLETED,
                    JobStatus.FAILED,
                    JobStatus.CANCELLED,
                ]:
                    continue

                age = (now - job.updated_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                if job_id in self._futures:
                    del self._futures[job_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")

    def get_all_jobs(self) -> Dict[str, JobState]:
        """
        Get all tracked jobs.

        Returns:
            Dictionary of job_id -> JobState
        """
        return self._jobs.copy()
