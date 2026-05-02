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

    def __init__(
        self,
        *,
        payload=None,
        lines=None,
        content: bytes = b"",
        status_code: int = 200,
    ):
        self._payload = payload or {}
        self._lines = lines or []
        self.content = content
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
        if "exit_code_on_start" in self.ready_state:
            self.ready_state["ready"] = False
            self.ready_state["exit_code"] = self.ready_state[
                "exit_code_on_start"
            ]
            return
        self.ready_state["ready"] = True
        if "health_payload_on_start" in self.ready_state:
            self.ready_state["health_payload"] = self.ready_state[
                "health_payload_on_start"
            ]

    def stop(self):
        self.ready_state["ready"] = False

    def last_exit_code(self):
        return self.ready_state.get("exit_code")


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
            return FakeResponse(
                payload=self.ready_state.get("health_payload")
                or {"status": "ready"}
            )
        if url.endswith("/admin/shutdown"):
            if self.ready_state.get("shutdown_effective", True):
                self.ready_state["ready"] = False
            return FakeResponse(payload={"status": "ok"})
        if url.endswith("/api/v1/daemon/status"):
            if not self.ready_state["ready"]:
                raise requests.ConnectionError("daemon down")
            return FakeResponse(
                payload={
                    "lifecycle": {"loaded_models": ["LLM"]},
                    "runtimes": [
                        {
                            "runtime": "llm",
                            "status": "ready",
                            "loaded": True,
                        }
                    ],
                }
            )
        if "/api/v1/daemon/runtimes/llm?" in url:
            summaries = self.ready_state.get("llm_summaries") or []
            if summaries:
                return FakeResponse(payload=summaries.pop(0))
            return FakeResponse(
                payload={
                    "runtime": "llm",
                    "status": "ready",
                    "loaded": True,
                }
            )
        if url.endswith("/api/v1/daemon/runtimes/llm/load"):
            return FakeResponse(payload={"status": "ok"})
        if url.endswith("/api/v1/daemon/runtimes/llm/unload"):
            return FakeResponse(payload={"status": "ok"})
        if url.endswith("/api/v1/daemon/runtimes/tts/cancel"):
            return FakeResponse(payload={"status": "cancelled"})
        if url.endswith("/api/v1/tts/synthesize"):
            return FakeResponse(content=b"wav-bytes")
        if url.endswith("/api/v1/art/generate"):
            return FakeResponse(payload={"job_id": "art-job-1", "status": "running"})
        if url.endswith("/api/v1/art/status/art-job-1"):
            art_statuses = self.ready_state.get("art_statuses") or []
            if art_statuses:
                return FakeResponse(payload=art_statuses.pop(0))
            return FakeResponse(
                payload={
                    "job_id": "art-job-1",
                    "status": "completed",
                    "progress": 100.0,
                }
            )
        if url.endswith("/api/v1/art/result/art-job-1"):
            return FakeResponse(content=b"png-bytes")
        if url.endswith("/api/v1/art/cancel/art-job-1"):
            return FakeResponse(payload={"status": "cancelled"})
        if url.endswith("/api/v1/stt/transcribe"):
            return FakeResponse(payload={"text": "hello", "language": "en"})
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


def test_ensure_connected_restarts_stale_dev_daemon():
    ready_state = {
        "ready": True,
        "health_payload": {
            "status": "ready",
            "dev_build_token": "old-token",
        },
        "health_payload_on_start": {
            "status": "ready",
            "dev_build_token": "new-token",
        },
    }
    launcher = FakeLauncher(ready_state)
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=launcher,
        session=session,
        detect_stale_dev_daemon=True,
        sleep=lambda _seconds: None,
    )
    client._expected_dev_build_token = lambda: "new-token"

    connected = client.ensure_connected()

    assert connected is True
    assert launcher.started == 1
    assert any(call[1].endswith("/admin/shutdown") for call in session.calls)


def test_ensure_connected_keeps_running_when_dev_token_missing():
    ready_state = {
        "ready": True,
        "health_payload": {
            "status": "ready",
        },
    }
    launcher = FakeLauncher(ready_state)
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=launcher,
        session=session,
        detect_stale_dev_daemon=True,
        sleep=lambda _seconds: None,
    )
    client._expected_dev_build_token = lambda: "new-token"
    debug_messages = []
    client.logger.debug = lambda message, *args: debug_messages.append(
        message % args if args else message
    )

    connected = client.ensure_connected()
    connected_again = client.ensure_connected()

    assert connected is True
    assert connected_again is True
    assert launcher.started == 0
    assert not any(call[1].endswith("/admin/shutdown") for call in session.calls)
    assert debug_messages == [
        "Daemon health payload missing dev_build_token; skipping stale-daemon recycle"
    ]


def test_is_available_uses_requested_health_timeout():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    connected = client.is_available(timeout_seconds=0.1)

    assert connected is True
    assert session.calls[0][2]["timeout"] == 0.1


def test_ensure_connected_reports_exited_daemon_process():
    ready_state = {
        "ready": False,
        "exit_code_on_start": 134,
    }
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=FakeSession(ready_state),
        sleep=lambda _seconds: None,
    )

    connected = client.ensure_connected()

    assert connected is False
    assert client.last_error == "Daemon process exited early with code 134"
    assert client.state is DaemonConnectionState.FAILED


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


def test_daemon_runtime_status_forwards_timeout_override():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    client.daemon_runtime_status(timeout_seconds=0.5)

    assert session.calls[-1][2]["timeout"] == 0.5


def test_runtime_status_uses_runtime_summary_endpoint():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    status = client.runtime_status("llm")

    assert status["runtime"] == "llm"
    assert status["loaded"] is True
    assert "/api/v1/daemon/runtimes/llm?" in session.calls[-1][1]


def test_wait_runtime_ready_polls_until_loaded():
    ready_state = {
        "ready": True,
        "llm_summaries": [
            {"runtime": "llm", "status": "starting", "loaded": False},
            {"runtime": "llm", "status": "ready", "loaded": True},
        ],
    }
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
        sleep=lambda _seconds: None,
    )

    ready = client.wait_runtime_ready("llm", loaded=True)

    assert ready is True
    runtime_calls = [
        call for call in session.calls if "/api/v1/daemon/runtimes/llm?" in call[1]
    ]
    assert len(runtime_calls) == 2


def test_synthesize_tts_posts_daemon_tts_request():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    audio = client.synthesize_tts("Hello world", request_id="tts-1")

    assert audio == b"wav-bytes"
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert url.endswith("/api/v1/tts/synthesize")
    assert kwargs["json"]["request_id"] == "tts-1"


def test_start_art_generation_can_skip_daemon_auto_export():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    response = client.start_art_generation(
        prompt="A bridge",
        skip_auto_export=True,
    )

    assert response["job_id"] == "art-job-1"
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert url.endswith("/api/v1/art/generate")
    assert kwargs["json"]["skip_auto_export"] is True


def test_wait_art_job_polls_until_completion():
    ready_state = {
        "ready": True,
        "art_statuses": [
            {"job_id": "art-job-1", "status": "running", "progress": 10.0},
            {"job_id": "art-job-1", "status": "completed", "progress": 100.0},
        ],
    }
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
        sleep=lambda _seconds: None,
    )

    image_bytes = client.wait_art_job("art-job-1")

    assert image_bytes == b"png-bytes"


def test_wait_art_job_reports_progress_updates():
    ready_state = {
        "ready": True,
        "art_statuses": [
            {"job_id": "art-job-1", "status": "running", "progress": 10.0},
            {"job_id": "art-job-1", "status": "running", "progress": 55.0},
            {"job_id": "art-job-1", "status": "completed", "progress": 100.0},
        ],
    }
    updates = []
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
        sleep=lambda _seconds: None,
    )

    image_bytes = client.wait_art_job(
        "art-job-1",
        progress_callback=updates.append,
    )

    assert image_bytes == b"png-bytes"
    assert updates == [
        {"job_id": "art-job-1", "status": "running", "progress": 10.0},
        {"job_id": "art-job-1", "status": "running", "progress": 55.0},
        {"job_id": "art-job-1", "status": "completed", "progress": 100.0},
    ]


def test_cancel_art_job_uses_delete_endpoint():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    response = client.cancel_art_job("art-job-1")

    assert response["status"] == "cancelled"
    assert session.calls[-1][0] == "DELETE"


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


def test_transcribe_audio_posts_multipart_request():
    ready_state = {"ready": True}
    session = FakeSession(ready_state)
    client = GuiDaemonClient(
        launcher=FakeLauncher(ready_state),
        session=session,
    )

    response = client.transcribe_audio(b"pcm", mime_type="audio/wav")

    assert response == {"text": "hello", "language": "en"}
    method, url, kwargs = session.calls[-1]
    assert method == "POST"
    assert url.endswith("/api/v1/stt/transcribe")
    file_info = kwargs["files"]["audio"]
    assert file_info[0] == "audio.bin"
    assert file_info[1] == b"pcm"
    assert file_info[2] == "audio/wav"