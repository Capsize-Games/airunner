"""Tests for the chat surface's loopback egress guard (#2230).

The guard is the enforcement point for the offline-egress policy, and the
only way the cloud-excluded desktop bundle can authenticate its WebSocket
handshakes, so both halves are asserted directly.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import QUrl

from airunner.components.chat.gui.widgets.chat_surface_interceptor import (
    TOKEN_HEADER,
    LoopbackTokenInterceptor,
)


class _RequestInfo:
    """Minimal stand-in for ``QWebEngineUrlRequestInfo``."""

    def __init__(self, url: str) -> None:
        self._url = QUrl(url)
        self.blocked = False
        self.headers: Dict[bytes, bytes] = {}

    def requestUrl(self) -> QUrl:
        """Return the requested URL."""
        return self._url

    def block(self, value: bool) -> None:
        """Record an egress block."""
        self.blocked = value

    def setHttpHeader(self, name: bytes, value: bytes) -> None:
        """Record an injected header."""
        self.headers[name] = value


def _intercept(url: str, token: str = "secret") -> _RequestInfo:
    """Run one request through a fresh interceptor."""
    info = _RequestInfo(url)
    interceptor = LoopbackTokenInterceptor(token)
    interceptor.interceptRequest(info)  # type: ignore[arg-type]
    return info


def test_remote_http_is_blocked() -> None:
    """A non-loopback HTTP request is refused and carries no token."""
    info = _intercept("http://example.com/assets/app.js")
    assert info.blocked is True
    assert info.headers == {}


def test_remote_websocket_is_blocked() -> None:
    """A non-loopback WebSocket handshake is refused."""
    info = _intercept("wss://example.com/api/v1/events")
    assert info.blocked is True


def test_loopback_http_gets_the_token() -> None:
    """A loopback asset request carries the loopback token."""
    info = _intercept("http://127.0.0.1:8188/index.html")
    assert info.blocked is False
    assert info.headers[TOKEN_HEADER] == b"secret"


def test_loopback_websocket_handshake_gets_the_token() -> None:
    """The events socket handshake carries the token it cannot set itself."""
    info = _intercept("ws://127.0.0.1:8188/api/v1/events")
    assert info.blocked is False
    assert info.headers[TOKEN_HEADER] == b"secret"


def test_localhost_is_allowed() -> None:
    """Every loopback spelling is accepted."""
    assert _intercept("http://localhost:8188/").blocked is False
    assert _intercept("http://[::1]:8188/").blocked is False


def test_missing_token_adds_no_header() -> None:
    """An unset token never produces an empty credential header."""
    info = _intercept("http://127.0.0.1:8188/", token="")
    assert info.headers == {}


def test_non_network_schemes_are_left_alone() -> None:
    """Bundled resources are neither blocked nor stamped."""
    info = _intercept("qrc:/icons/feather/light/plus.svg")
    assert info.blocked is False
    assert info.headers == {}
