"""Real FastAPI route tests for correlated LLM stream cancellation."""

from __future__ import annotations

import threading
import time

import pytest
from starlette.testclient import TestClient

from airunner_services.api import loopback_token
from airunner_services.api import server as server_module
from airunner_services.api.server import create_app
from airunner_services.database import reset_engine, setup_database
from airunner_services.ipc.messages import (
    EnvelopeStatus,
    ResponseEnvelope,
    StreamDelta,
)
from airunner_services.runtimes.contracts import RuntimeKind


class _CancellableClient:
    def __init__(self) -> None:
        self.started = threading.Event()
        self.cancelled = threading.Event()
        self.cancel_calls: list[str] = []

    def stream(self, envelope):
        self.started.set()
        yield StreamDelta(
            request_id=envelope.request_id,
            delta={"content": "started"},
        )
        self.cancelled.wait(5)
        if self.cancelled.is_set():
            yield StreamDelta(
                request_id=envelope.request_id,
                status=EnvelopeStatus.CANCELLED,
                final=True,
            )
        else:
            yield StreamDelta(
                request_id=envelope.request_id,
                delta={"content": "finished"},
                final=True,
            )

    def cancel(self, request_id):
        self.cancel_calls.append(request_id)
        self.cancelled.set()
        return ResponseEnvelope(
            request_id=request_id,
            status=EnvelopeStatus.CANCELLED,
        )


class _Registry:
    def __init__(self, client) -> None:
        self.client = client

    def resolve(self, runtime, provider=None, deployment_mode=None):
        assert runtime is RuntimeKind.LLM
        return self.client


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AIRUNNER_DATABASE_URL", f"sqlite:///{tmp_path / 'api.sqlite'}"
    )
    monkeypatch.setenv("AIRUNNER_DISABLE_DB_SETUP_CACHE", "1")
    reset_engine()
    setup_database()
    monkeypatch.setattr(
        loopback_token,
        "loopback_token_path",
        lambda: tmp_path / "config" / "token",
    )
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setattr(server_module, "is_loopback_request", lambda _conn: True)
    app = create_app()
    runtime = _CancellableClient()
    app.state.runtime_registry = _Registry(runtime)
    token = loopback_token.get_or_create_loopback_token()
    yield TestClient(app), runtime, {"X-Airunner-Token": token}
    reset_engine()
    loopback_token._cache_loaded = False
    loopback_token._cached_token = None


def _started_frame(ws, timeout: float = 3.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frame = ws.receive_json()
        if frame.get("content") == "started":
            return frame
    raise AssertionError("stream did not start before deadline")


def test_cancel_route_is_owner_and_tenant_scoped(api) -> None:
    client, runtime, headers = api
    headers = {**headers, "X-Namespace": "tenant-a"}
    with client.websocket_connect(
        "/api/v1/llm/stream", headers=headers
    ) as ws:
        ws.send_json({"message": "wait", "request_id": "owned-123"})
        frame = _started_frame(ws)
        assert frame["request_id"] == "owned-123"

        foreign = client.post(
            "/api/v1/daemon/runtimes/llm/cancel",
            json={"request_id": "owned-123"},
            headers={**headers, "X-Namespace": "tenant-b"},
        )
        assert foreign.status_code == 404
        assert runtime.cancel_calls == []

        response = client.post(
            "/api/v1/daemon/runtimes/llm/cancel",
            json={"request_id": "owned-123"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert runtime.cancel_calls == ["owned-123"]
        terminal = ws.receive_json()
        assert terminal["type"] == "cancelled"
        assert terminal["request_id"] == "owned-123"


def test_disconnect_during_prefill_cancels_without_waiting_for_first_chunk(api) -> None:
    client, runtime, headers = api
    # Replace the client with one that does not produce a frame until it is
    # cancelled, modeling a long prompt prefill before the first token.
    class _PrefillClient(_CancellableClient):
        def stream(self, envelope):
            self.started.set()
            self.cancelled.wait(5)
            if self.cancelled.is_set():
                yield StreamDelta(
                    request_id=envelope.request_id,
                    status=EnvelopeStatus.CANCELLED,
                    final=True,
                )

    runtime = _PrefillClient()
    client.app.state.runtime_registry = _Registry(runtime)
    with client.websocket_connect(
        "/api/v1/llm/stream", headers=headers
    ) as ws:
        ws.send_json({"message": "long prefill", "request_id": "prefill-1"})
        assert runtime.started.wait(2)
        ws.close()
    assert runtime.cancelled.wait(3)
    assert runtime.cancel_calls == ["prefill-1"]


def test_bounded_pending_messages_close_and_cancel_blocked_prefill(api) -> None:
    client, _runtime, headers = api

    class _PrefillClient(_CancellableClient):
        def stream(self, envelope):
            self.started.set()
            self.cancelled.wait(5)
            if self.cancelled.is_set():
                yield StreamDelta(
                    request_id=envelope.request_id,
                    status=EnvelopeStatus.CANCELLED,
                    final=True,
                )

    runtime = _PrefillClient()
    client.app.state.runtime_registry = _Registry(runtime)
    with client.websocket_connect(
        "/api/v1/llm/stream", headers=headers
    ) as ws:
        ws.send_json({"message": "blocked prefill", "request_id": "overflow-1"})
        assert runtime.started.wait(2)
        for index in range(9):
            try:
                ws.send_json({"message": f"queued {index}"})
            except Exception:
                # The server closes once the pending message bound is exceeded.
                break
        assert runtime.cancelled.wait(3)
    assert runtime.cancel_calls == ["overflow-1"]


def test_duplicate_active_request_id_is_rejected(api) -> None:
    client, runtime, headers = api
    with client.websocket_connect(
        "/api/v1/llm/stream", headers=headers
    ) as ws:
        ws.send_json({"message": "first", "request_id": "same-id"})
        assert _started_frame(ws)["request_id"] == "same-id"

        # The first request is still active. A second connection under the
        # same authenticated principal cannot replace its ownership record.
        with client.websocket_connect(
            "/api/v1/llm/stream", headers=headers
        ) as second:
            second.send_json({"message": "second", "request_id": "same-id"})
            error = second.receive_json()
            assert error["code"] == "request_id_unavailable"
            assert error["request_id"] == "same-id"

        client.post(
            "/api/v1/daemon/runtimes/llm/cancel",
            json={"request_id": "same-id"},
            headers=headers,
        )
        assert runtime.cancel_calls == ["same-id"]
