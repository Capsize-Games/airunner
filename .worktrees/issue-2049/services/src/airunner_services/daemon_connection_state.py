"""Service-owned daemon connection states."""

from __future__ import annotations

from enum import Enum


class DaemonConnectionState(str, Enum):
    """Explicit daemon connection states for client-side orchestration."""

    NOT_STARTED = "not_started"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"