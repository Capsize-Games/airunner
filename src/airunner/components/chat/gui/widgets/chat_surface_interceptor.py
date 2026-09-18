"""Loopback-only egress guard for the desktop chat surface (#2230).

The chat surface is a browser page, so every request it makes must be
checked against the global egress policy (#2083) *and* carry the daemon's
loopback token. QtWebEngine cannot set a header on a WebSocket handshake
from JavaScript, and the cloud-excluded desktop bundle carries no auth
extension to supply the ``?token=`` the web client would otherwise use —
so the host attaches the credential to every loopback request instead.

A reference to the interceptor must be kept alive by the caller: the
profile does not take ownership of the Python wrapper, and a temporary
interceptor is garbage-collected before it can fire.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject
from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
TOKEN_HEADER = b"x-airunner-token"
NETWORK_SCHEMES = frozenset({"http", "https", "ws", "wss"})


class LoopbackTokenInterceptor(QWebEngineUrlRequestInterceptor):
    """Block non-loopback requests and stamp the loopback token on the rest."""

    def __init__(self, token: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._token = token

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        """Block foreign hosts; attach the token to loopback requests."""
        url = info.requestUrl()
        if url.scheme() not in NETWORK_SCHEMES:
            return
        if url.host() not in LOOPBACK_HOSTS:
            info.block(True)
            return
        if self._token:
            info.setHttpHeader(TOKEN_HEADER, self._token.encode("utf-8"))


__all__ = [
    "LOOPBACK_HOSTS",
    "NETWORK_SCHEMES",
    "TOKEN_HEADER",
    "LoopbackTokenInterceptor",
]
