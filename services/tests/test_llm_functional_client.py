"""Unit coverage for the functional LLM HTTP client (issue #2242).

The ``/llm/generate`` functional tests must observe the daemon's own
verdict -- including a slow first-load 504 -- instead of dying first as
a client socket timeout. These tests pin that contract without starting
a daemon or loading a model.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

import pytest

from llm_functional_support import LLM_GENERATE_TIMEOUT_SECONDS
from llm_functional_support import post_json

_RESPONSE_DELAY_SECONDS = 1.5
_SHORT_TIMEOUT_SECONDS = 0.3
_LONG_TIMEOUT_SECONDS = 10.0

# Legacy non-streaming LLM routes budget 300s server-side
# (legacy_llm_nonstream.collect_non_stream_response and the ollama/openai
# compat ``done.wait`` calls). The generate client must exceed it.
_SERVER_GENERATE_BUDGET_SECONDS = 300.0


class _DelayedHandler(BaseHTTPRequestHandler):
    """Answer one POST after a fixed delay like a slow daemon."""

    def do_POST(self) -> None:
        """Sleep past short client timeouts, then answer 200."""
        import time

        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        time.sleep(_RESPONSE_DELAY_SECONDS)
        body = b"{}"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silence request logging during tests."""
        del format, args


@pytest.fixture
def delayed_server() -> Iterator[str]:
    """Serve one delayed POST endpoint on a background thread."""
    server = HTTPServer(("127.0.0.1", 0), _DelayedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


def test_generate_timeout_outlives_server_budget() -> None:
    """The generate client budget must exceed the 300s server budget."""
    assert (
        LLM_GENERATE_TIMEOUT_SECONDS > _SERVER_GENERATE_BUDGET_SECONDS
    )


def test_post_json_honors_short_timeout(delayed_server: str) -> None:
    """A too-small timeout raises instead of returning a verdict."""
    with pytest.raises(TimeoutError):
        post_json(
            delayed_server,
            {},
            timeout_seconds=_SHORT_TIMEOUT_SECONDS,
        )


def test_post_json_returns_delayed_response(delayed_server: str) -> None:
    """An adequate timeout observes the slow server's verdict."""
    status, body, content_type = post_json(
        delayed_server,
        {},
        timeout_seconds=_LONG_TIMEOUT_SECONDS,
    )
    assert status == 200
    assert body == b"{}"
    assert content_type == "application/json"
