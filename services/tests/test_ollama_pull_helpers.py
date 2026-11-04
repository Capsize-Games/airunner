"""Bounded Ollama pull observation tests with controlled job states."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException

from airunner_services.api.routes import ollama_pull_helpers
from airunner_services.api.routes.ollama_pull_helpers import (
    stream_ollama_pull,
    wait_for_ollama_pull,
)
from airunner_services.api.routes.ollama_model_helpers import (
    resolve_ollama_model,
)
from airunner_services.utils.job_tracker import JobState
from airunner_services.utils.job_tracker import JobStatus


class _ConnectedRequest:
    """Request double that stays connected while a job is observed."""

    async def is_disconnected(self) -> bool:
        return False


class _DisconnectAfterOneStatus:
    """Disconnect after the first state poll has produced progress."""

    def __init__(self) -> None:
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.calls > 1


class _DisconnectedRequest:
    """Request double that is already disconnected."""

    async def is_disconnected(self) -> bool:
        return True


class _FakeJobs:
    """Return a finite or repeating status sequence without side effects."""

    def __init__(self, states: list[JobState]) -> None:
        self.states = states
        self.position = 0
        self.cancel_calls = 0

    async def get_status(self, job_id: str) -> JobState | None:
        if job_id != "fake-job" or not self.states:
            return None
        index = min(self.position, len(self.states) - 1)
        self.position += 1
        return self.states[index]

    async def cancel(self, _job_id: str) -> bool:
        self.cancel_calls += 1
        return True


def _active_job() -> JobState:
    return JobState("fake-job", JobStatus.RUNNING, progress=12.0)


def _short_deadlines(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ollama_pull_helpers,
        "pull_timeouts",
        lambda: (0.006, 0.02, 0.001),
    )


def test_wait_for_pull_has_finite_observation_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _short_deadlines(monkeypatch)
    jobs = _FakeJobs([_active_job()])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(wait_for_ollama_pull(jobs, "fake-job", _ConnectedRequest()))

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "model_pull_observation_timed_out"
    assert jobs.cancel_calls == 0


def test_stream_timeout_is_an_error_terminal_not_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _short_deadlines(monkeypatch)
    jobs = _FakeJobs([_active_job()])

    async def collect() -> list[dict[str, object]]:
        return [
            json.loads(line)
            async for line in stream_ollama_pull(
                jobs,
                "fake-job",
                _ConnectedRequest(),
            )
        ]

    records = asyncio.run(collect())
    assert records[0] == {"status": "starting"}
    assert records[-1] == {
        "status": "error",
        "error": "Model pull observation timed out",
    }
    assert all(record.get("status") != "success" for record in records)
    assert jobs.cancel_calls == 0


def test_missing_job_status_is_a_nonstream_error() -> None:
    jobs = _FakeJobs([])
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(wait_for_ollama_pull(jobs, "fake-job", _ConnectedRequest()))
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "model_pull_status_lost"


def test_missing_job_status_is_stream_error() -> None:
    jobs = _FakeJobs([])

    async def collect() -> list[dict[str, object]]:
        return [
            json.loads(line)
            async for line in stream_ollama_pull(
                jobs,
                "fake-job",
                _ConnectedRequest(),
            )
        ]

    records = asyncio.run(collect())
    assert records[-1] == {
        "status": "error",
        "error": "Model pull status unavailable",
    }


def test_cancelled_job_is_terminal_error_for_both_protocol_modes() -> None:
    jobs = _FakeJobs(
        [JobState("fake-job", JobStatus.CANCELLED, progress=12.0)]
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(wait_for_ollama_pull(jobs, "fake-job", _ConnectedRequest()))
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "model_pull_failed"

    async def collect() -> list[dict[str, object]]:
        return [
            json.loads(line)
            async for line in stream_ollama_pull(
                jobs,
                "fake-job",
                _ConnectedRequest(),
            )
        ]

    records = asyncio.run(collect())
    assert records[-1] == {"status": "error", "error": "Model pull failed"}
    assert all(record.get("status") != "success" for record in records)


def test_status_queries_have_a_finite_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ollama_pull_helpers,
        "pull_timeouts",
        lambda: (1.0, 0.001, 0.001),
    )

    class _HangingJobs:
        async def get_status(self, _job_id: str) -> None:
            await asyncio.Event().wait()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            wait_for_ollama_pull(
                _HangingJobs(),
                "fake-job",
                _ConnectedRequest(),
            )
        )
    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "model_pull_status_timed_out"


def test_disconnect_stops_observation_without_cancelling_shared_job() -> None:
    jobs = _FakeJobs(
        [
            _active_job(),
            JobState("fake-job", JobStatus.COMPLETED, progress=100.0),
        ]
    )

    async def collect() -> list[dict[str, object]]:
        return [
            json.loads(line)
            async for line in stream_ollama_pull(
                jobs,
                "fake-job",
                _DisconnectAfterOneStatus(),
            )
        ]

    records = asyncio.run(collect())
    assert records == [
        {"status": "starting"},
        {"status": "downloading", "progress": 12.0},
    ]
    assert jobs.position == 1
    assert jobs.cancel_calls == 0


def test_nonstream_disconnect_does_not_poll_or_cancel_shared_job() -> None:
    jobs = _FakeJobs(
        [JobState("fake-job", JobStatus.COMPLETED, progress=100.0)]
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            wait_for_ollama_pull(jobs, "fake-job", _DisconnectedRequest())
        )
    assert jobs.position == 0
    assert jobs.cancel_calls == 0


def test_pull_timeout_configuration_is_finite_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIRUNNER_OLLAMA_PULL_TIMEOUT_SECONDS", "inf")
    monkeypatch.setenv("AIRUNNER_OLLAMA_PULL_STATUS_TIMEOUT_SECONDS", "999999")
    monkeypatch.setenv("AIRUNNER_OLLAMA_PULL_POLL_INTERVAL_SECONDS", "0")

    observation, status, poll = ollama_pull_helpers.pull_timeouts()
    assert observation == ollama_pull_helpers.DEFAULT_OBSERVATION_TIMEOUT_SECONDS
    assert status == ollama_pull_helpers.MAX_STATUS_TIMEOUT_SECONDS
    assert poll == ollama_pull_helpers.DEFAULT_POLL_INTERVAL_SECONDS


def test_preferred_download_repository_is_a_supported_model_alias() -> None:
    model = resolve_ollama_model("unsloth/Qwen3.5-9B-GGUF")
    assert model is not None
    assert model.model_id == "qwen3.5-9b"
    assert model.repo_id == "unsloth/Qwen3.5-9B-GGUF"
