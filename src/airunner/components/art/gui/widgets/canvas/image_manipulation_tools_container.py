from PySide6.QtCore import Slot, QTimer
from airunner.components.art.gui.widgets.canvas.templates.image_manipulation_tools_container_ui import (
    Ui_image_manipulation_tools_container,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.enums import StableDiffusionVersion


# Versions that don't support ControlNet or Inpaint
_NO_CONTROLNET_INPAINT_VERSIONS = (
    StableDiffusionVersion.Z_IMAGE_TURBO.value,
    StableDiffusionVersion.Z_IMAGE_BASE.value,
)


class ImageManipulationToolsContainer(BaseWidget):
    widget_class_ = Ui_image_manipulation_tools_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self._controlnet_tab = None
        self._inpaint_tab = None
        self._last_version = None
        self.ui.image_manipulation_tools_tab_container.currentChanged.connect(
            self.on_tab_changed
        )
        # Set up a timer to periodically check version changes
        self._version_check_timer = QTimer(self)
        self._version_check_timer.setInterval(500)  # Check every 500ms
        self._version_check_timer.timeout.connect(self._check_version_and_update_tabs)

    @Slot(int)
    def on_tab_changed(self, index: int):
        self.qsettings.setValue(
            "tabs/image_manipulation_tools_container/active_index", index
        )

    def _check_version_and_update_tabs(self):
        """Check if version changed and update tab visibility accordingly."""
        current_version = self.generator_settings.version
        if current_version != self._last_version:
            self._last_version = current_version
            self._update_tab_visibility()

    def _update_tab_visibility(self):
        """Hide/show ControlNet and Inpaint tabs based on model version.
        
        Z-Image models don't support ControlNet or Inpaint pipelines,
        so those tabs should be hidden when Z-Image is selected.
        """
        tab_widget = self.ui.image_manipulation_tools_tab_container
        current_version = self.generator_settings.version
        should_hide = current_version in _NO_CONTROLNET_INPAINT_VERSIONS
        
        # Store references to removed tabs so they can be restored
        if should_hide:
            # Remove ControlNet tab (index 1) and Inpaint tab (index 2)
            # Note: Remove in reverse order to preserve indices
            if tab_widget.count() > 2:
                self._inpaint_tab = tab_widget.widget(2)
                tab_widget.removeTab(2)
            if tab_widget.count() > 1:
                self._controlnet_tab = tab_widget.widget(1)
                tab_widget.removeTab(1)
        else:
            # Restore tabs if they were previously removed
            if self._controlnet_tab is not None and tab_widget.count() == 1:
                tab_widget.insertTab(1, self._controlnet_tab, "Controlnet")
                self._controlnet_tab = None
            if self._inpaint_tab is not None and tab_widget.count() == 2:
                tab_widget.insertTab(2, self._inpaint_tab, "Inpaint")
                self._inpaint_tab = None

    def showEvent(self, event):
        super().showEvent(event)
        # Update tab visibility based on current model version
        self._last_version = self.generator_settings.version
        self._update_tab_visibility()
        
        # Start the version check timer
        self._version_check_timer.start()
        
        # Restore active tab index
        active_index = int(
            self.qsettings.value(
                "tabs/image_manipulation_tools_container/active_index", 0
            )
        )
        # Ensure index is valid for current tab count
        max_index = self.ui.image_manipulation_tools_tab_container.count() - 1
        active_index = min(active_index, max_index)
        self.ui.image_manipulation_tools_tab_container.setCurrentIndex(
            active_index
        )

    def hideEvent(self, event):
        super().hideEvent(event)
        # Stop the timer when widget is hidden
        self._version_check_timer.stop()
