"""Unit tests for SidecarArtClient model-status reconciliation logic.

These tests exercise the daemon-side status computation without a real
sidecar: a fake launcher and a fake ``requests`` session stand in for the
sidecar process.  The behaviours under test are the root-cause fix for the
GUI showing an indeterminate "running" progress bar at startup:

* An idle sidecar must never report the stale cached ``loading`` status
  (which previously mapped to ``starting`` forever).
* A live ``art_model_status`` field from the sidecar ``/health`` payload is
  preferred over the local cache.
* The cached status is reconciled on job completion/failure and at
  launcher/load boundaries.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from airunner_services.ipc.messages import RequestEnvelope
from airunner_services.runtimes.art_daemon_runtime_settings import (
    ArtDaemonRuntimeSettings,
)
from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.runtimes.contracts import RuntimeHealthStatus
from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.sidecar_art_client import SidecarArtClient


def _settings() -> ArtDaemonRuntimeSettings:
    """Return minimal art daemon settings for client construction."""
    return ArtDaemonRuntimeSettings(
        host="127.0.0.1",
        port=8190,
        base_daemon_config_path=None,
        art_model_path=None,
        art_model_version=None,
        art_scheduler=None,
        startup_timeout_seconds=5.0,
        request_timeout_seconds=1.0,
        invocation_timeout_seconds=5.0,
        status_poll_interval_seconds=0.01,
    )


class _FakeLauncher:
    """Minimal launcher double exposing the sidecar endpoint contract."""

    endpoint = "http://127.0.0.1:8190"
    api_base_url = "http://127.0.0.1:8190/api/v1/art"

    def __init__(self, health_status=RuntimeHealthStatus.READY):
        self._health_status = health_status
        self.stopped = False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.stopped = True

    def is_running(self) -> bool:
        return not self.stopped

    def health_status(self):
        return self._health_status, self._health_status.value


class _FakeResponse:
    def __init__(self, payload=None, content=b"", status_code=200):
        self._payload = payload or {}
        self.content = content
        self.status_code = status_code
        self.text = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """Session double that serves health and job-status payloads."""

    def __init__(self, health_payload=None, job_status=None):
        self.health_payload = (
            {"art_execution_finished_status": True}
            if health_payload is None
            else health_payload
        )
        self.job_status = (
            {"status": "completed", "execution_finished": True}
            if job_status is None
            else {"execution_finished": True, **job_status}
        )
        self.requests: list[tuple[str, str]] = []

    def request(self, method, url, **kwargs):
        del kwargs
        self.requests.append((method, url))
        if url.endswith("/health"):
            return _FakeResponse(self.health_payload)
        if url.endswith("/generate"):
            return _FakeResponse({"job_id": "job-1"})
        if "/status/" in url:
            return _FakeResponse(self.job_status)
        return _FakeResponse({})

    def close(self) -> None:
        pass


def _client(
    *,
    health_payload=None,
    job_status=None,
    health_status=RuntimeHealthStatus.READY,
) -> SidecarArtClient:
    """Build one SidecarArtClient wired to fake launcher/session doubles."""
    return SidecarArtClient(
        settings=_settings(),
        launcher=_FakeLauncher(health_status=health_status),
        session=_FakeSession(
            health_payload=health_payload,
            job_status=job_status,
        ),
    )


def _invoke_request(action=RuntimeAction.INVOKE, payload=None):
    return RequestEnvelope(
        runtime=RuntimeKind.ART,
        action=action,
        payload=payload or {"prompt": "a cat"},
    )


# ---------------------------------------------------------------------------
# Idle sidecar must never report the stale cached "loading" status.
# ---------------------------------------------------------------------------


def test_idle_fallback_never_reports_stale_loading():
    """An idle sidecar with a stale cached ``loading`` reports STOPPED."""
    client = _client(health_payload={})  # /health returns no art_model_status
    client._remember_model_status("loading")
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED
    assert health.metadata.get("model_status") == "unloaded"


def test_idle_fallback_keeps_loaded_when_previously_confirmed():
    """An idle sidecar previously confirmed loaded reports READY."""
    client = _client(health_payload={})
    client._remember_model_status("loaded")
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata.get("model_status") == "loaded"


def test_active_job_still_reports_starting_while_loading():
    """A tracked job with no loaded confirmation still reports STARTING."""
    client = _client(health_payload={})
    client._remember_model_status("loading")
    client._track_job("request-1", "job-1")
    try:
        health = client.healthcheck()
    finally:
        client._untrack_job("request-1")
    assert health.status is RuntimeHealthStatus.STARTING
    assert health.metadata.get("model_status") == "loading"


def test_active_job_with_loaded_confirmation_reports_ready():
    """A tracked job on a confirmed loaded sidecar reports READY."""
    client = _client(health_payload={})
    client._remember_model_status("loaded")
    client._track_job("request-1", "job-1")
    try:
        health = client.healthcheck()
    finally:
        client._untrack_job("request-1")
    assert health.status is RuntimeHealthStatus.READY


# ---------------------------------------------------------------------------
# Live sidecar /health art_model_status is preferred over the cache.
# ---------------------------------------------------------------------------


def test_remote_model_status_reads_art_model_status():
    """The sidecar ``art_model_status`` field is read from /health."""
    client = _client(health_payload={"art_model_status": "unloaded"})
    assert client._remote_model_status() == "unloaded"


def test_healthcheck_prefers_live_unloaded_status():
    """A live ``unloaded`` health field wins over a stale loading cache."""
    client = _client(health_payload={"art_model_status": "unloaded"})
    client._remember_model_status("loading")
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED
    assert health.metadata.get("model_status") == "unloaded"


def test_healthcheck_prefers_live_loaded_status():
    """A live ``loaded`` health field maps to READY."""
    client = _client(health_payload={"art_model_status": "loaded"})
    client._remember_model_status("unloaded")
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.READY
    assert health.metadata.get("model_status") == "loaded"


# ---------------------------------------------------------------------------
# Status-string mapping used by the daemon runtime summary.
# ---------------------------------------------------------------------------


def test_status_from_model_status_mapping():
    """Model-status strings map to the daemon runtime health semantics."""
    cases = {
        "loaded": RuntimeHealthStatus.READY,
        "ready": RuntimeHealthStatus.READY,
        "loading": RuntimeHealthStatus.STARTING,
        "unloaded": RuntimeHealthStatus.STOPPED,
        "disabled": RuntimeHealthStatus.STOPPED,
        "failed": RuntimeHealthStatus.FAILED,
        "error": RuntimeHealthStatus.FAILED,
    }
    for model_status, expected in cases.items():
        status, _details = SidecarArtClient._status_from_model_status(
            model_status,
            "default",
        )
        assert status is expected, model_status


# ---------------------------------------------------------------------------
# Cache reconciliation on job observation and load boundaries.
# ---------------------------------------------------------------------------


def test_observe_job_status_failed_resets_cache():
    """A failed job resets the cached status so it cannot stay loading."""
    client = _client()
    client._remember_model_status("loading")
    client._observe_job_status("failed", 0.0)
    assert client._last_known_model_status == "unloaded"


def test_observe_job_status_completed_keeps_loaded():
    """A completed job leaves the cached status as loaded."""
    client = _client()
    client._observe_job_status("completed", 100.0)
    assert client._last_known_model_status == "loaded"


def test_generate_image_failure_reconciles_cache():
    """A failed generation reconciles the cache and clears the active job."""
    client = _client(
        job_status={"status": "failed", "error": "boom"},
    )
    client._remember_model_status("loading")
    response = client.invoke_with_progress(_invoke_request())
    assert response.status.value == "failed"
    assert client._last_known_model_status == "unloaded"
    assert not client._has_active_jobs()
    # The very next poll reports the sidecar as idle/stopped, not starting.
    health = client.healthcheck()
    assert health.status is RuntimeHealthStatus.STOPPED


def test_terminal_job_status_waits_for_execution_finished() -> None:
    client = _client()
    statuses = [
        {"status": "cancelled"},
        {"status": "cancelled", "execution_finished": False},
        {"status": "cancelled", "execution_finished": True},
    ]
    requests_seen: list[str] = []

    def request(method, path, **kwargs):
        del method, kwargs
        requests_seen.append(path)
        if path.endswith("/status/job-1"):
            return statuses.pop(0)
        raise AssertionError(f"Unexpected sidecar path: {path}")

    client._request = request
    status, _payload, error = client._wait_for_job("job-1")

    assert status.value == "cancelled"
    assert error is None
    assert requests_seen == [
        "/status/job-1",
        "/status/job-1",
        "/status/job-1",
    ]


@pytest.mark.parametrize(
    ("terminal_status", "expected"),
    [
        ("completed", "succeeded"),
        ("failed", "failed"),
        ("cancelled", "cancelled"),
    ],
)
def test_all_terminal_statuses_wait_for_physical_completion(
    terminal_status: str, expected: str
) -> None:
    client = _client()
    statuses = [
        {"status": terminal_status, "execution_finished": False},
        {"status": terminal_status, "execution_finished": True},
    ]
    poll_count = 0

    def request(method, path, **kwargs):
        nonlocal poll_count
        del method
        if path.endswith("/status/job-1"):
            poll_count += 1
            return statuses.pop(0)
        if path.endswith("/result/job-1"):
            assert kwargs["expect_json"] is False
            return b"verified-test-image-bytes"
        raise AssertionError(f"Unexpected sidecar path: {path}")

    client._request = request
    status, _payload, _error = client._wait_for_job("job-1")

    assert status.value == expected
    assert poll_count == 2


def test_old_sidecar_is_rejected_before_art_job_submission() -> None:
    client = _client(health_payload={})
    response = client.invoke_with_progress(_invoke_request())

    assert response.status.value == "failed"
    assert "completion status" in response.error.message
    session = client._session
    assert not any(url.endswith("/generate") for _method, url in session.requests)


def test_close_terminates_poller_after_persistent_status_failure() -> None:
    import threading

    client = _client()
    status_attempted = threading.Event()
    result: list[tuple[object, dict, str | None]] = []

    def request(method, path, **_kwargs):
        if method == "DELETE":
            return {}
        status_attempted.set()
        raise RuntimeError("sidecar unavailable")

    client._request = request
    poller = threading.Thread(
        target=lambda: result.append(client._wait_for_job("job-1"))
    )
    poller.start()
    assert status_attempted.wait(timeout=1)
    client.close()
    poller.join(timeout=1)

    assert not poller.is_alive()
    assert result and result[0][0].value == "failed"
    assert "termination was confirmed" in (result[0][2] or "")
    assert client._launcher.stopped is False


def test_initial_progress_callback_failure_keeps_job_tracked_until_finish() -> None:
    from airunner_services.runtimes.message_envelopes import load_message_types

    client = _client()
    client._submit_job = lambda _invocation: "job-1"
    observed_tracking: list[bool] = []

    def progress(_value):
        observed_tracking.append(client._active_jobs.get("request-1") == "job-1")
        raise RuntimeError("observer failure")

    client._wait_for_job = lambda *_args, **_kwargs: (
        load_message_types().EnvelopeStatus.SUCCEEDED,
        {"images": ["cG5n"]},
        None,
    )
    request = _invoke_request()
    request.request_id = "request-1"
    response = client.invoke_with_progress(request, progress)

    assert observed_tracking == [True]
    assert response.status.value == "succeeded"
    assert not client._has_active_jobs()


def test_ambiguous_external_submission_holds_until_client_close() -> None:
    import threading

    client = _client()
    client._submit_job = lambda _invocation: (_ for _ in ()).throw(
        RuntimeError("response lost after POST")
    )
    result = []
    worker = threading.Thread(
        target=lambda: result.append(client.invoke_with_progress(_invoke_request()))
    )
    worker.start()
    worker.join(timeout=0.05)
    assert worker.is_alive()
    assert result == []

    client.close()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert result and result[0].status.value == "failed"
    assert "outcome was uncertain" in result[0].error.message


def test_ambiguous_managed_submission_stops_owned_sidecar() -> None:
    client = _client()
    client._managed_launcher = True
    client._submit_job = lambda _invocation: (_ for _ in ()).throw(
        RuntimeError("response lost after POST")
    )

    response = client.invoke_with_progress(_invoke_request())

    assert response.status.value == "failed"
    assert client._launcher.stopped is True


def test_load_runtime_resets_cache():
    """A load boundary clears the stale cached model status."""
    client = _client()
    client._remember_model_status("loading")
    response = client.invoke_with_progress(
        _invoke_request(action=RuntimeAction.LOAD_MODEL, payload={})
    )
    assert response.status.value == "succeeded"
    assert client._last_known_model_status is None
