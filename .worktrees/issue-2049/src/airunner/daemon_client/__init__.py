"""GUI-side re-export of the canonical daemon HTTP client.

The single source of truth for the daemon wire-format client lives in
``airunner_services.daemon_client``.  This package is kept as a thin
compatibility layer so GUI code can keep importing from
``airunner.daemon_client`` without duplicating the client.
"""

from airunner_services.daemon_client.gui_bridge_mixin import APIBridgeError
from airunner_services.daemon_client.gui_bridge_mixin import HardwareProfile
from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner_services.daemon_client.resource_store import GuiResourceStore
from airunner_services.daemon_client.resource_store import ResourceRecord

__all__ = [
    "APIBridgeError",
    "GuiDaemonClient",
    "GuiResourceStore",
    "HardwareProfile",
    "ResourceRecord",
]
