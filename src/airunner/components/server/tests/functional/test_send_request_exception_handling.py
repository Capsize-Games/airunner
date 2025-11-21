import json
import time
import socket
from http.client import HTTPConnection

import pytest
import requests

from airunner.components.server.api.api_server_thread import APIServerThread
from airunner.components.server.api.server import set_api


class FakeLLM:
    def send_request(self, *args, **kwargs):
        # Simulate raising an exception immediately to trigger NDJSON error return
        raise RuntimeError("Simulated send_request error")


class FakeAPI:
    def __init__(self):
        self.llm = FakeLLM()


def wait_for_server(server_thread, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if getattr(server_thread, "server", None) is not None:
            return True
        time.sleep(0.01)
    return False


def test_send_request_exception_returns_ndjson_error():
    """When api.llm.send_request raises an exception, the server should write an NDJSON error line immediately."""
    set_api(FakeAPI())
    server_thread = APIServerThread(host="127.0.0.1", port=0)
    server_thread.start()

    try:
        assert wait_for_server(server_thread), "Server failed to start"
        port = server_thread.server.server_address[1]

        payload = {
            "prompt": "Will cause send_request to raise",
            "action": "CHAT",
            "stream": True,
            "llm_request": {"max_new_tokens": 5, "temperature": 0.0},
        }

        response = requests.post(
            f"http://127.0.0.1:{port}/llm",
            json=payload,
            timeout=(1, 5),
            stream=True,
        )

        assert response.status_code == 200

        # Read lines from the NDJSON stream
        lines = list(response.iter_lines())
        assert len(lines) > 0, "Expected at least one NDJSON line"

        # First line should be the error message (immediate NDJSON)
        first_line = lines[0]
        try:
            chunk = json.loads(first_line)
        except Exception:
            pytest.fail("Failed to parse first NDJSON line as JSON")

        assert chunk.get("error", False) is True
        assert "Error invoking LLM" in chunk.get(
            "message", ""
        ), "Error message missing"

    finally:
        # Attempt a best-effort shutdown. Closing the server socket unblocks the
        # accept()/select() in the server thread so it can exit. This is more
        # reliable in tests than server.shutdown() which sometimes waits.
        try:
            if getattr(server_thread, "server", None):
                try:
                    sock = getattr(server_thread.server, "socket", None)
                    if sock:
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                        except Exception:
                            pass
                        try:
                            sock.close()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        server_thread.join(timeout=2.0)
