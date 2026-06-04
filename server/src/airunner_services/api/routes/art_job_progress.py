"""Progress helpers for art job execution."""

import asyncio
from typing import Optional

from airunner_services.utils.job_tracker import (
    JobStatus as JobState,
    JobTracker,
)


# JobTracker coordination
# Progress callbacks run from the runtime thread, so this module exists only to
# normalize those updates before they cross back into the async tracker layer.


async def job_cancelled(tracker: JobTracker, job_id: str) -> bool:
    """Return True when the tracked art job has already been cancelled."""
    job = await tracker.get_status(job_id)
    return bool(job is not None and job.status is JobState.CANCELLED)


async def fail_art_job(
    tracker: JobTracker,
    job_id: str,
    message: str,
) -> None:
    """Fail one art job unless it has already been cancelled."""
    if await job_cancelled(tracker, job_id):
        return
    await tracker.fail_job(job_id, message)


def coerce_job_progress(progress_data: dict) -> Optional[float]:
    """Return one normalized job progress percentage."""
    try:
        progress = float(progress_data.get("progress"))
    except (TypeError, ValueError):
        return None
    return max(0.0, min(99.0, progress))


def update_tracker_progress(
    loop: asyncio.AbstractEventLoop,
    tracker: JobTracker,
    job_id: str,
    progress_data: dict,
) -> None:
    """Push one normalized progress update into the JobTracker."""
    progress = coerce_job_progress(progress_data)
    if progress is None:
        return
    asyncio.run_coroutine_threadsafe(
        tracker.update_progress(job_id, progress, JobState.RUNNING),
        loop,
    )


def progress_callback(
    loop: asyncio.AbstractEventLoop,
    tracker: JobTracker,
    job_id: str,
):
    """Return one thread-safe progress callback for the tracker."""

    # The closure keeps the runtime callback tiny while the normalization logic
    # above stays testable and independent from the API route layer.

    def on_progress(progress_data: dict) -> None:
        update_tracker_progress(loop, tracker, job_id, progress_data)

    return on_progress