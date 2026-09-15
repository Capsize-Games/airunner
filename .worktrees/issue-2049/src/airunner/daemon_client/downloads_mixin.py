"""Compatibility re-export for the retired GUI-side downloads mixin.

The canonical daemon client now provides all download endpoints directly on
``GuiDaemonClient``.  This module is retained only so any accidental import
of the former mixin continues to resolve.
"""

from airunner_services.daemon_client.gui_bridge_mixin import GuiBridgeMixin

DownloadsClientMixin = GuiBridgeMixin

__all__ = ["DownloadsClientMixin"]
