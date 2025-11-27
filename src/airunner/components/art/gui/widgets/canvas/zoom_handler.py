from PySide6.QtGui import QTransform

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.components.application.gui.windows.main.settings_mixin import SettingsMixin


class ZoomHandler(
    MediatorMixin,
    SettingsMixin,
):
    @property
    def zoom_in_step(self) -> float:
        zoom_level = self.grid_settings.zoom_level
        if zoom_level > 6:
            return 2
        elif zoom_level > 4:
            return 1
        return self.grid_settings.zoom_in_step

    @property
    def zoom_out_step(self) -> float:
        zoom_level = self.grid_settings.zoom_level
        if zoom_level > 6:
            return 2
        elif zoom_level > 4:
            return 1
        if zoom_level <= 1.0:
            return 0.05
        return self.grid_settings.zoom_out_step

    @property
    def zoom_level(self) -> float:
        zoom = self.grid_settings.zoom_level
        if zoom <= 0:
            zoom = 0.1
        return zoom

    @zoom_level.setter
    def zoom_level(self, value):
        self.update_grid_settings(zoom_level=value)

    def on_zoom_level_changed(self) -> QTransform:
        # Create a QTransform object and scale it
        zoom_level = self.grid_settings.zoom_level
        transform = QTransform()
        transform.scale(zoom_level, zoom_level)
        return transform

    def wheelEvent(self, event) -> QTransform:
        """Handle mouse wheel events for zooming.

        Args:
            event: Qt wheel event containing delta and position.

        Returns:
            QTransform with the new zoom level applied.
        """
        # Get the scroll delta (positive = zoom in, negative = zoom out)
        delta = event.angleDelta().y()

        current_zoom = self.zoom_level

        if delta > 0:
            # Zoom in
            new_zoom = current_zoom + self.zoom_in_step
        else:
            # Zoom out
            new_zoom = current_zoom - self.zoom_out_step

        # Clamp zoom level to reasonable bounds
        new_zoom = max(0.1, min(new_zoom, 10.0))

        # Update the zoom level in settings
        self.zoom_level = new_zoom

        # Create and return the transform
        transform = QTransform()
        transform.scale(new_zoom, new_zoom)
        return transform
