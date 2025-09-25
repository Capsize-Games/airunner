from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.gui.widgets.stablediffusion.templates.stablediffusion_tool_tab_ui import (
    Ui_stablediffusion_tool_tab_widget,
)
from airunner.utils.settings.get_qsettings import get_qsettings


class StablediffusionToolTabWidget(BaseWidget):
    widget_class_ = Ui_stablediffusion_tool_tab_widget

    def __init__(self, *args, **kwargs):
        self._splitters = ["layer_tab_splitter"]
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self.ui.tool_tab_widget_container.currentChanged.connect(
            self.on_tool_tab_widget_container_currentChanged
        )

    @Slot(int)
    def on_tool_tab_widget_container_currentChanged(self, index: int):
        self.qsettings.setValue(
            "tabs/stablediffusion_tool_tab/active_index", index
        )

    def showEvent(self, event):
        super().showEvent(event)
        active_index = int(
            self.qsettings.value(
                "tabs/stablediffusion_tool_tab/active_index", 0
            )
        )
        self.ui.tool_tab_widget_container.setCurrentIndex(active_index)
