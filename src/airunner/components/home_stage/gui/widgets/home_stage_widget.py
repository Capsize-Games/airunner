from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QVBoxLayout

from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.enums import SignalCode
from airunner.components.home_stage.gui.widgets.training_widget import (
    TrainingWidget,
)
from airunner.components.model_management.gui.model_status_widget import (
    ModelStatusWidget,
)


class HomeStageWidget(BaseWidget):
    """Home stage widget with native PySide6 panels."""

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
        }
        super().__init__(*args, **kwargs)
        self.training_panel = None
        self.model_status_panel = None
        self._deferred_startup_loaded = False
        self._startup_ready = False

    def _get_panel_layout(self, panel) -> QVBoxLayout:
        """Return the panel layout, creating it on first use."""
        layout = panel.layout()
        if layout is None:
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def _finish_deferred_startup(self) -> None:
        """Create the Home tab panels after the main window is ready."""
        if self._deferred_startup_loaded:
            return

        self._deferred_startup_loaded = True
        self.training_panel = TrainingWidget(self.ui.knowledge_base_panel)
        self._get_panel_layout(self.ui.knowledge_base_panel).addWidget(
            self.training_panel
        )

        self.model_status_panel = ModelStatusWidget(
            self.ui.system_resources_panel
        )
        self._get_panel_layout(self.ui.system_resources_panel).addWidget(
            self.model_status_panel
        )

    def showEvent(self, event):
        super().showEvent(event)
        if self._startup_ready and not self._deferred_startup_loaded:
            QTimer.singleShot(0, self._finish_deferred_startup)

    @Slot()
    def on_main_window_loaded_signal(self):
        """Load Home widgets only after GUI startup timing is complete."""
        self._startup_ready = True
        if self.isVisible() and not self._deferred_startup_loaded:
            QTimer.singleShot(0, self._finish_deferred_startup)
