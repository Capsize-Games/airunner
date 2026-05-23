"""GUI-facing API package — bridge, adapters, and client facades."""

from airunner.api.api_bridge import APIBridge, APIBridgeError
from airunner.api.signal_api_adapter import SignalAPIAdapter

__all__ = [
    "APIBridge",
    "APIBridgeError",
    "SignalAPIAdapter",
]
