"""Helpers for daemon availability checks at GUI call sites."""

from __future__ import annotations

from airunner.daemon_client.daemon_connection_state import (
    DaemonConnectionState,
)


def daemon_client_is_available(
    client,
    *,
    timeout_seconds: float = 0.2,
) -> bool:
    """Return True when one daemon client can serve a request now."""
    if client is None:
        return False

    if getattr(client, "state", None) is DaemonConnectionState.CONNECTED:
        return True

    availability_check = getattr(client, "is_available", None)
    if not callable(availability_check):
        return True

    try:
        return bool(availability_check(timeout_seconds=timeout_seconds))
    except TypeError:
        return bool(availability_check())
    except Exception:
        return False