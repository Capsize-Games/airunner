"""Bounded observation helpers for Ollama model-pull jobs."""

from __future__ import annotations

import asyncio
import json
import math
import os
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException

from airunner_services.utils.job_tracker import JobStatus

DEFAULT_OBSERVATION_TIMEOUT_SECONDS = 1800.0
MAX_OBSERVATION_TIMEOUT_SECONDS = 21600.0
DEFAULT_STATUS_TIMEOUT_SECONDS = 5.0
MAX_STATUS_TIMEOUT_SECONDS = 30.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.1
MAX_POLL_INTERVAL_SECONDS = 5.0


class PullStatusTimeout(TimeoutError):
    """A shared job-status query did not return within its bound."""


def _configured_seconds(
    name: str,
    default: float,
    maximum: float,
) -> float:
    """Read a positive finite timeout from the environment with a cap."""
    try:
        value = float(os.environ.get(name, default))
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(value) or value <= 0:
        return default
    return min(value, maximum)


def pull_timeouts() -> tuple[float, float, float]:
    """Return bounded observation, status-query, and polling intervals."""
    return (
        _configured_seconds(
            "AIRUNNER_OLLAMA_PULL_TIMEOUT_SECONDS",
            DEFAULT_OBSERVATION_TIMEOUT_SECONDS,
            MAX_OBSERVATION_TIMEOUT_SECONDS,
        ),
        _configured_seconds(
            "AIRUNNER_OLLAMA_PULL_STATUS_TIMEOUT_SECONDS",
            DEFAULT_STATUS_TIMEOUT_SECONDS,
            MAX_STATUS_TIMEOUT_SECONDS,
        ),
        _configured_seconds(
            "AIRUNNER_OLLAMA_PULL_POLL_INTERVAL_SECONDS",
            DEFAULT_POLL_INTERVAL_SECONDS,
            MAX_POLL_INTERVAL_SECONDS,
        ),
    )


async def _get_status(service: Any, job_id: str, timeout: float) -> Any:
    """Read one shared job state with a finite per-query timeout."""
    try:
        return await asyncio.wait_for(service.get_status(job_id), timeout)
    except asyncio.TimeoutError as exc:
        raise PullStatusTimeout from exc


def _job_terminal_payload(job: Any) -> dict[str, str] | None:
    """Return an Ollama terminal payload, or None while work is active."""
    if job.status is JobStatus.COMPLETED:
        return {"status": "success"}
    if job.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
        return {"status": "error", "error": "Model pull failed"}
    return None


def _encode(payload: dict[str, Any]) -> bytes:
    """Encode one newline-delimited Ollama response record."""
    return json.dumps(payload).encode("utf-8") + b"\n"


async def wait_for_ollama_pull(
    service: Any,
    job_id: str,
    request: Any,
) -> dict[str, str]:
    """Wait a bounded time for the job's actual terminal state."""
    observation_timeout, status_timeout, poll_interval = pull_timeouts()
    deadline = time.monotonic() + observation_timeout
    while True:
        if await request.is_disconnected():
            # Stop observing only. The shared download continues under its
            # own lifecycle and is never cancelled by a client disconnect.
            raise asyncio.CancelledError
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise HTTPException(
                status_code=504,
                detail="model_pull_observation_timed_out",
            )
        try:
            job = await _get_status(
                service,
                job_id,
                min(status_timeout, remaining),
            )
        except PullStatusTimeout as exc:
            raise HTTPException(
                status_code=504,
                detail="model_pull_status_timed_out",
            ) from exc
        if job is None:
            raise HTTPException(status_code=502, detail="model_pull_status_lost")
        terminal = _job_terminal_payload(job)
        if terminal is not None:
            if terminal["status"] == "success":
                return terminal
            raise HTTPException(status_code=502, detail="model_pull_failed")
        await asyncio.sleep(min(poll_interval, max(0.0, remaining)))


async def stream_ollama_pull(
    service: Any,
    job_id: str,
    request: Any,
) -> AsyncIterator[bytes]:
    """Stream real job progress and one accurate terminal/error record."""
    observation_timeout, status_timeout, poll_interval = pull_timeouts()
    deadline = time.monotonic() + observation_timeout
    yield _encode({"status": "starting"})
    while True:
        if await request.is_disconnected():
            # No terminal status is sent after disconnect; do not cancel work.
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            yield _encode(
                {"status": "error", "error": "Model pull observation timed out"}
            )
            return
        try:
            job = await _get_status(
                service,
                job_id,
                min(status_timeout, remaining),
            )
        except PullStatusTimeout:
            yield _encode(
                {"status": "error", "error": "Model pull status timed out"}
            )
            return
        if job is None:
            yield _encode(
                {"status": "error", "error": "Model pull status unavailable"}
            )
            return
        terminal = _job_terminal_payload(job)
        if terminal is not None:
            yield _encode(terminal)
            return

        status = "downloading" if job.status is JobStatus.RUNNING else "starting"
        yield _encode({"status": status, "progress": float(job.progress)})
        await asyncio.sleep(min(poll_interval, max(0.0, remaining)))


__all__ = [
    "DEFAULT_OBSERVATION_TIMEOUT_SECONDS",
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "DEFAULT_STATUS_TIMEOUT_SECONDS",
    "MAX_OBSERVATION_TIMEOUT_SECONDS",
    "MAX_POLL_INTERVAL_SECONDS",
    "MAX_STATUS_TIMEOUT_SECONDS",
    "PullStatusTimeout",
    "pull_timeouts",
    "stream_ollama_pull",
    "wait_for_ollama_pull",
]
