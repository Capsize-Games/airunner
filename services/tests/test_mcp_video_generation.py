"""Contracts for the MCP video daemon client."""

from __future__ import annotations

from typing import Any, Callable

import httpx
import pytest

from airunner_services.mcp.config import MCPConfig
from airunner_services.mcp.daemon_client import DaemonError
from airunner_services.mcp.video_client import VideoDaemonClient


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    **overrides: Any,
) -> VideoDaemonClient:
    """Build a video client backed by a mock daemon transport."""
    options = {
        "daemon_url": "http://127.0.0.1:8080",
        "api_key": "test-key",
        "generation_timeout_s": 0.1,
        "poll_interval_s": 0.0,
    }
    options.update(overrides)
    config = MCPConfig(**options)
    return VideoDaemonClient(config, httpx.MockTransport(handler))


def test_video_client_round_trip() -> None:
    """Happy: video requests use the expected routes and return values."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/video/generate":
            return httpx.Response(200, json={"job_id": "job-1"})
        if request.url.path == "/api/v1/video/status/job-1":
            return httpx.Response(200, json={"status": "completed"})
        if request.url.path == "/api/v1/video/result/job-1":
            return httpx.Response(200, content=b"mp4")
        if request.url.path == "/api/v1/video/cancel/job-1":
            return httpx.Response(200, json={"status": "cancelled"})
        if request.url.path == "/api/v1/video/models":
            return httpx.Response(200, json={"models": ["checkpoint"]})
        return httpx.Response(404)

    client = _client(handler)
    assert client.start_video({"prompt": "test"}) == "job-1"
    assert client.get_status("job-1") == {"status": "completed"}
    assert client.fetch_mp4("job-1") == b"mp4"
    assert client.cancel("job-1") == {"status": "cancelled"}
    assert client.list_models() == {"models": ["checkpoint"]}
    assert [request.method for request in requests] == [
        "POST",
        "GET",
        "GET",
        "DELETE",
        "GET",
    ]


def test_requests_use_configured_timeout() -> None:
    """Happy: HTTP requests use the configured request timeout."""
    timeouts: list[float | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"]["read"])
        return httpx.Response(200, json={"models": []})

    _client(handler, request_timeout_s=2.5).list_models()
    assert timeouts == [2.5]


def test_loopback_token_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy: loopback requests reuse the shared token helper."""
    monkeypatch.setattr(
        "airunner_services.mcp.video_client._loopback_token_header",
        lambda url, api_key: {"X-Airunner-Token": "loopback-token"},
    )
    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("X-Airunner-Token"))
        return httpx.Response(200, json={"models": []})

    config = MCPConfig(daemon_url="http://127.0.0.1:8188")
    VideoDaemonClient(config, httpx.MockTransport(handler)).list_models()
    assert seen == ["loopback-token"]


def test_http_and_transport_errors_use_daemon_error() -> None:
    """Sad: HTTP failures and transport failures follow the client contract."""
    client = _client(lambda request: httpx.Response(503, text="offline"))
    with pytest.raises(DaemonError) as caught:
        client.list_models()
    assert caught.value.status_code == 503

    def disconnected(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = _client(disconnected)
    with pytest.raises(DaemonError, match="daemon unreachable") as caught:
        client.list_models()
    assert caught.value.status_code is None


def test_hostile_job_ids_never_reach_http() -> None:
    """Hostile: empty and path-like IDs are rejected by every job method."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    client = _client(handler)
    for job_id in ("", "../secret", "a/b", "a\\b"):
        for call in (
            client.get_status,
            client.fetch_mp4,
            client.cancel,
            client.wait_for_completion,
        ):
            with pytest.raises(DaemonError):
                call(job_id)
    assert requests == []


def test_generated_path_like_job_id_is_rejected() -> None:
    """Hostile: malformed IDs returned by the daemon are not accepted."""
    for job_id in ("../secret", None):
        client = _client(
            lambda request: httpx.Response(200, json={"job_id": job_id})
        )
        with pytest.raises(DaemonError, match="daemon returned a bad job id"):
            client.start_video({"prompt": "test"})


def test_wait_uses_configured_poll_and_generation_timeouts() -> None:
    """Sad: polling honors MCPConfig timing values."""
    states = iter(("running", "completed"))
    client = _client(
        lambda request: httpx.Response(200, json={"status": next(states)}),
        generation_timeout_s=0.2,
        poll_interval_s=0.0,
    )
    assert client.wait_for_completion("job-1") == {"status": "completed"}

    client = _client(
        lambda request: httpx.Response(200, json={"status": "running"}),
        generation_timeout_s=0.0,
        poll_interval_s=0.0,
    )
    with pytest.raises(DaemonError, match="timed out"):
        client.wait_for_completion("job-1")
