"""Compatibility re-export for the retired GUI-side client base.

The canonical daemon client is no longer assembled from per-domain mixins.
This module is retained only so any accidental import of the former base
class continues to resolve.
"""

from airunner_services.daemon_client.gui_daemon_client import GuiDaemonClient

_DaemonClientBase = GuiDaemonClient

__all__ = ["_DaemonClientBase"]
