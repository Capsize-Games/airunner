from typing import Optional

from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stablediffusion_tool_tab_ui import (
    Ui_stablediffusion_tool_tab_widget,
)
from airunner.utils.settings.get_qsettings import get_qsettings


class StablediffusionToolTabWidget(BaseWidget):
    widget_class_ = Ui_stablediffusion_tool_tab_widget
    _min_tab_index = 0
    _max_tab_index = 5

    def __init__(self, *args, **kwargs):
        self._splitters = ["layer_tab_splitter"]
        self._requested_active_index: Optional[int] = None
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self._configure_tool_tab_widget()

    def _configure_tool_tab_widget(self) -> None:
        """Hide the visible tab bar and wire persistence hooks."""
        tab_widget = self.ui.tool_tab_widget_container
        tab_widget.tabBar().hide()
        tab_widget.currentChanged.connect(
            self.on_tool_tab_widget_container_currentChanged
        )

    @classmethod
    def _clamp_tool_tab_index(cls, index: int) -> int:
        """Clamp one requested tool-tab index to the supported range."""
        return max(cls._min_tab_index, min(index, cls._max_tab_index))

    def current_tool_page_index(self) -> int:
        """Return the active tool-tab index."""
        return self._clamp_tool_tab_index(
            self.ui.tool_tab_widget_container.currentIndex()
        )

    def show_tool_page(self, index: int) -> None:
        """Select one tool-tab page and persist the choice."""
        clamped_index = self._clamp_tool_tab_index(index)
        self._requested_active_index = clamped_index
        self.ui.tool_tab_widget_container.setCurrentIndex(clamped_index)
        self.qsettings.setValue(
            "tabs/stablediffusion_tool_tab/active_index",
            clamped_index,
        )

    @Slot(int)
    def on_tool_tab_widget_container_currentChanged(self, index: int):
        index = self._clamp_tool_tab_index(index)
        self._requested_active_index = index
        self.qsettings.setValue(
            "tabs/stablediffusion_tool_tab/active_index", index
        )

    def showEvent(self, event):
        super().showEvent(event)
        active_index = self._requested_active_index
        if active_index is None:
            saved_index = self.qsettings.value(
                "tabs/stablediffusion_tool_tab/active_index",
                self._min_tab_index,
            )
            try:
                active_index = int(saved_index)
            except (TypeError, ValueError):
                active_index = self._min_tab_index
        self.show_tool_page(active_index)
