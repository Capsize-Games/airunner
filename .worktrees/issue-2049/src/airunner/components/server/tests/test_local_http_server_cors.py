"""Unit tests for the restricted LNA CORS headers (GitHub issue #2034).

Proves:
- ``Access-Control-Allow-Origin`` is never ``*`` and only echoes loopback
  origins (127.0.0.1 / localhost / ::1).
- Non-loopback origins receive no CORS grant at all.
- ``Access-Control-Allow-Private-Network: true`` is paired with the
  restricted origin (never sent alone for a rejected origin).
- LNA-disabled servers send no CORS headers.
"""

from __future__ import annotations

import email.message
import io

from airunner.components.server.local_http_server import (
    MultiDirectoryCORSRequestHandler,
)


def _make_handler(lna_enabled: bool, origin: str | None = None):
    handler = MultiDirectoryCORSRequestHandler.__new__(
        MultiDirectoryCORSRequestHandler
    )
    handler.lna_enabled = lna_enabled
    handler.headers = email.message.Message()
    if origin:
        handler.headers["Origin"] = origin
    handler.wfile = io.BytesIO()
    handler._headers_buffer = []
    handler.request_version = "HTTP/1.1"
    handler._close_connection = False
    return handler


def _header_map(handler) -> dict[str, str]:
    decoded = [line.decode("latin-1") for line in handler._headers_buffer]
    return {
        part[0].strip(): part[1].strip()
        for part in (line.split(":", 1) for line in decoded)
        if len(part) == 2
    }


def test_lna_cors_echoes_loopback_origin() -> None:
    handler = _make_handler(True, "http://127.0.0.1:5005")
    handler._send_lna_cors_headers()
    headers = _header_map(handler)
    assert headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5005"
    assert headers.get("Access-Control-Allow-Private-Network") == "true"


def test_lna_cors_accepts_localhost_origin() -> None:
    handler = _make_handler(True, "http://localhost:5005")
    handler._send_lna_cors_headers()
    headers = _header_map(handler)
    assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5005"
    assert headers.get("Access-Control-Allow-Private-Network") == "true"


def test_lna_cors_rejects_non_loopback_origin() -> None:
    handler = _make_handler(True, "http://evil.example")
    handler._send_lna_cors_headers()
    headers = _header_map(handler)
    assert "Access-Control-Allow-Origin" not in headers
    assert "Access-Control-Allow-Private-Network" not in headers


def test_lna_cors_rejects_https_scheme() -> None:
    handler = _make_handler(True, "https://127.0.0.1:5005")
    handler._send_lna_cors_headers()
    headers = _header_map(handler)
    assert "Access-Control-Allow-Origin" not in headers


def test_lna_cors_never_sends_wildcard() -> None:
    for origin in ("http://127.0.0.1:5005", "http://localhost:5005"):
        handler = _make_handler(True, origin)
        handler._send_lna_cors_headers()
        assert _header_map(handler).get("Access-Control-Allow-Origin") != "*"


def test_lna_disabled_sends_no_cors_headers() -> None:
    handler = _make_handler(False, "http://127.0.0.1:5005")
    handler._send_lna_cors_headers()
    assert handler._headers_buffer == []
