from PySide6.QtGui import QTransform

from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


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
        self.update_grid_settings("zoom_level", value)

    def on_zoom_level_changed(self) -> QTransform:
        # Create a QTransform object and scale it
        zoom_level = self.grid_settings.zoom_level
        transform = QTransform()
        transform.scale(zoom_level, zoom_level)
        return transform
