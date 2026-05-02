"""Connection states for the GUI daemon client."""

from __future__ import annotations

from enum import Enum


class DaemonConnectionState(str, Enum):
    """Explicit GUI daemon connection states."""

    NOT_STARTED = "not_started"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"