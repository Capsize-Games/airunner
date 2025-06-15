# Signal handlers for NodeGraphWidget

from typing import Dict


def _on_nodegraph_zoom_changed(self, data: Dict):
    """Signal handler for NODEGRAPH_ZOOM signal."""
    zoom = data.get("zoom_level", 0)

    # Get the center from the current application settings
    # Don't try to access viewer directly from this handler
    settings = self.application_settings
    try:
        center_x = int(getattr(settings, "nodegraph_center_x", 0) or 0)
        center_y = int(getattr(settings, "nodegraph_center_y", 0) or 0)
    except (TypeError, ValueError):
        center_x = 0
        center_y = 0

    # Update the settings
    from airunner.components.settings.data.application_settings import ApplicationSettings

    ApplicationSettings.objects.update(
        self.application_settings.id,
        nodegraph_zoom=zoom,
        nodegraph_center_x=center_x,
        nodegraph_center_y=center_y,
    )


def _on_nodegraph_pan_changed(self, data: Dict):
    """Signal handler for NODEGRAPH_PAN signal."""
    try:
        center_x = int(data.get("center_x", 0) or 0)
        center_y = int(data.get("center_y", 0) or 0)
    except (TypeError, ValueError):
        center_x = 0
        center_y = 0

    # Get current zoom from the current application settings
    settings = self.application_settings
    zoom = getattr(settings, "nodegraph_zoom", 0)

    # Update the settings
    from airunner.components.settings.data.application_settings import ApplicationSettings

    ApplicationSettings.objects.update(
        self.application_settings.id,
        nodegraph_zoom=zoom,
        nodegraph_center_x=center_x,
        nodegraph_center_y=center_y,
    )
