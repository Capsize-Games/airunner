"""Compatibility re-export for the retired GUI-side art mixin.

The canonical daemon client now provides all art endpoints directly on
``GuiDaemonClient``.  This module is retained only so any accidental import
of the former mixin continues to resolve.
"""

from airunner_services.daemon_client.gui_bridge_mixin import GuiBridgeMixin

ArtClientMixin = GuiBridgeMixin

__all__ = ["ArtClientMixin"]
