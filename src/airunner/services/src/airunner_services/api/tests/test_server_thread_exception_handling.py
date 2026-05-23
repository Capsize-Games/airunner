"""Tests for legacy server-thread exception handling."""

import json
import time

import pytest
import requests

from airunner_services.api.legacy_server import set_api
from airunner_services.api.server_thread import APIServerThread


class FakeLLM:
    def send_request(self, *args, **kwargs):
        raise RuntimeError("Simulated send_request error")


class FakeAPI:
    def __init__(self):
        self.llm = FakeLLM()


def wait_for_server(server_thread, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        server = getattr(server_thread, "server", None)
        if server is not None and getattr(server, "started", False):
            return True
        time.sleep(0.01)
    return False


def get_bound_port(server_thread) -> int:
    """Return the bound uvicorn port for a running server thread."""
    server = getattr(server_thread, "server", None)
    if server is None:
        raise RuntimeError("Server is not available")

    listeners = getattr(server, "servers", [])
    if not listeners:
        raise RuntimeError("Server listeners are not available")

    sockets = getattr(listeners[0], "sockets", [])
    if not sockets:
        raise RuntimeError("Server sockets are not available")

    return sockets[0].getsockname()[1]


def test_send_request_exception_returns_ndjson_error():
    """Streaming requests should fail with an immediate NDJSON error."""
    set_api(FakeAPI())
    server_thread = APIServerThread(host="127.0.0.1", port=0)
    server_thread.start()

    try:
        assert wait_for_server(server_thread), "Server failed to start"
        port = get_bound_port(server_thread)

        payload = {
            "prompt": "Will cause send_request to raise",
            "action": "CHAT",
            "stream": True,
            "llm_request": {"max_new_tokens": 5, "temperature": 0.0},
        }

        response = requests.post(
            f"http://127.0.0.1:{port}/llm/generate",
            json=payload,
            timeout=(1, 5),
            stream=True,
        )

        assert response.status_code == 200

        lines = list(response.iter_lines())
        assert lines, "Expected at least one NDJSON line"

        first_line = lines[0]
        try:
            chunk = json.loads(first_line)
        except Exception:
            pytest.fail("Failed to parse first NDJSON line as JSON")

        assert chunk.get("error", False) is True
        assert "Error invoking LLM" in chunk.get("message", "")

    finally:
        server_thread.stop()
        server_thread.join(timeout=2.0)