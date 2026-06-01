"""GUI-facing API package — re-exports from the daemon client.

The bridge and signal adapter functionality is now part of
``GuiDaemonClient`` itself.  This package is kept as a compatibility
re-export layer.
"""

from airunner.daemon_client.gui_daemon_client import (
    APIBridgeError,
    GuiDaemonClient,
)

__all__ = [
    "APIBridgeError",
    "GuiDaemonClient",
]
