"""Tests for the GUI daemon client overlay."""

from __future__ import annotations

import json
from types import SimpleNamespace

import requests

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)
from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner.enums import LLMActionType


class FakeResponse:
    """Minimal requests.Response-style double."""

    def __init__(self, *, payload=None, lines=None, status_code: int = 200):
        self._payload = payload or {}
        self._lines = lines or []
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_lines(self):
        return iter(self._lines)


class FakeLauncher:
    """Simple daemon launcher double."""

    def __init__(self, ready_state):
        self.ready_state = ready_state
        self.started = 0

    def start(self):
        self.started += 1
        self.ready_state["ready"] = True

    def stop(self):
        self.ready_state["ready"] = False


class FakeSession:
    """Simple requests session double."""

    def __init__(self, ready_state, stream_lines=None):
        self.ready_state = ready_state
        self.stream_lines = stream_lines or []
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("/health"):
            if not self.ready_state["ready"]:
                raise requests.ConnectionError("daemon down")
            return FakeResponse(payload={"status": "ready"})
        if url.endswith("/api/v1/daemon/status"):
            if not self.ready_state["ready"]:
                raise requests.ConnectionError("daemon down")
            return FakeResponse(payload={"lifecycle": {"loaded_models": ["LLM"]}})
        if url.endswith("/api/v1/daemon/runtimes/llm/load"):
            return FakeResponse(payload={"status": "ok"})
        if url.endswith("/api/v1/daemon/runtimes/llm/unload"):
            return FakeResponse(payload={"status": "ok"})
        if url.endswith("/llm/generate"):
            return FakeResponse(lines=self.stream_lines)
        if url.endswith("/admin/interrupt"):
            if not self.ready_state["ready"]:
                raise requests.ConnectionError("daemon down")
            return FakeResponse(payload={"status": "ok"})
        raise AssertionError(f"Unexpected URL: {url}")


def test_ensure_connected_auto_starts_daemon():
    ready_state = {"ready": False}
    states = []
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=FakeSession(ready_state),
        state_callback=lambda state, details: states.append((state, details)),
        sleep=lambda _seconds: None,
    )

    connected = client.ensure_connected()

    assert connected is True
    assert client.state is DaemonConnectionState.CONNECTED
    assert states[0][0] is DaemonConnectionState.CONNECTING
    assert states[-1][0] is DaemonConnectionState.CONNECTED


def test_stream_llm_request_posts_expected_payload_and_headers():
    ready_state = {"ready": True}
    session = FakeSession(
        ready_state,
        stream_lines=[
            json.dumps(
                {
                    "message": "hello",
                    "is_first_message": True,
                    "is_end_of_message": False,
                    "sequence_number": 0,
                    "action": "CHAT",
                }
            ).encode("utf-8"),
            json.dumps(
                {
                    "message": " world",
                    "is_first_message": False,
                    "is_end_of_message": True,
                    "sequence_number": 1,
                    "action": "CHAT",
                }
            ).encode("utf-8"),
        ],
    )
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )
    llm_request = LLMRequest(max_new_tokens=32, model_service="local")

    chunks = list(
        client.stream_llm_request(
            "Say hello",
            llm_request,
            LLMActionType.CHAT,
            "req-123",
            conversation_id=7,
        )
    )

    assert [chunk["message"] for chunk in chunks] == ["hello", " world"]
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert url.endswith("/llm/generate")
    assert kwargs["headers"]["x-request-id"] == "req-123"
    assert kwargs["json"]["prompt"] == "Say hello"
    assert kwargs["json"]["conversation_id"] == 7
    assert kwargs["json"]["model_service"] == "local"


def test_interrupt_requires_existing_connection():
    ready_state = {"ready": False}
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=FakeSession(ready_state),
    )

    try:
        client.interrupt_llm()
    except RuntimeError as exc:
        assert "daemon" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when daemon is down")


def test_daemon_runtime_status_uses_daemon_endpoint():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    status = client.daemon_runtime_status()

    assert status["lifecycle"]["loaded_models"] == ["LLM"]
    assert session.calls[-1][1].endswith("/api/v1/daemon/status")


def test_runtime_control_posts_expected_payload():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    client.load_runtime("llm", request_id="req-1")
    client.unload_runtime("llm")

    runtime_calls = [
        call
        for call in session.calls
        if "/api/v1/daemon/runtimes/llm/" in call[1]
    ]
    load_call = runtime_calls[0]
    unload_call = runtime_calls[1]
    assert load_call[1].endswith("/api/v1/daemon/runtimes/llm/load")
    assert load_call[2]["json"]["request_id"] == "req-1"
    assert unload_call[1].endswith("/api/v1/daemon/runtimes/llm/unload")