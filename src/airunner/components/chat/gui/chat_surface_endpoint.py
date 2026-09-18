"""Resolve the loopback endpoint of the daemon-hosted chat surface (#2230).

The desktop chat surface is served by the daemon (see
``airunner_services.api.routes.client_bundle``), so the page's origin and
the socket host are the daemon's loopback origin. This module is the single
place that answers "where is that origin and what is the token".
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from airunner_services.api.loopback_token import get_or_create_loopback_token
from airunner_services.runtimes.daemon_config import DaemonConfig

DAEMON_URL_ENV = "AIRUNNER_DAEMON_URL"
INDEX_PATH = "/index.html"


@dataclass(frozen=True)
class ChatSurfaceEndpoint:
    """The loopback origin and credential of the daemon-hosted surface."""

    base_url: str
    token: str

    @property
    def index_url(self) -> str:
        """Return the absolute URL of the surface's entry document."""
        return f"{self.base_url.rstrip('/')}{INDEX_PATH}"


def daemon_base_url() -> str:
    """Return the daemon's loopback origin, honouring an explicit override."""
    override = (os.environ.get(DAEMON_URL_ENV) or "").strip()
    if override:
        return override.rstrip("/")
    server = DaemonConfig().config.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", 8188)
    return f"http://{host}:{port}"


def resolve_chat_surface_endpoint() -> ChatSurfaceEndpoint:
    """Return the loopback endpoint and token for the chat surface."""
    return ChatSurfaceEndpoint(
        base_url=daemon_base_url(),
        token=get_or_create_loopback_token(),
    )


__all__ = [
    "DAEMON_URL_ENV",
    "INDEX_PATH",
    "ChatSurfaceEndpoint",
    "daemon_base_url",
    "resolve_chat_surface_endpoint",
]
