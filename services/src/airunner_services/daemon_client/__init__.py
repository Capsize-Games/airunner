"""Canonical daemon HTTP client and its launcher helpers.

This package is the single source of truth for the client-side wire format
used to talk to the local daemon.  The desktop client imports the same
``GuiDaemonClient`` through ``airunner.daemon_client``, which re-exports the
service-owned implementation.
"""

from airunner_services.daemon_client.gui_bridge_mixin import APIBridgeError
from airunner_services.daemon_client.gui_bridge_mixin import GuiBridgeMixin
from airunner_services.daemon_client.gui_bridge_mixin import HardwareProfile
from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner_services.daemon_client.launcher import DaemonLauncher

__all__ = [
    "APIBridgeError",
    "DaemonLauncher",
    "GuiBridgeMixin",
    "GuiDaemonClient",
    "HardwareProfile",
]
