from PySide6.QtCore import Slot

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.widgets.tool_tab.templates.tool_tab_ui import (
    Ui_tool_tab_widget,
)
from airunner.utils.settings.get_qsettings import get_qsettings


class ToolTabWidget(BaseWidget):
    widget_class_ = Ui_tool_tab_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self.ui.tool_tab_widget_container.currentChanged.connect(
            self.on_tool_tab_widget_container_currentChanged
        )

    @Slot(int)
    def on_tool_tab_widget_container_currentChanged(self, index: int):
        self.qsettings.setValue("tabs/right/active_index", index)

    def restore_state(self):
        active_index = int(self.qsettings.value("tabs/right/active_index", 0))
        self.ui.tool_tab_widget_container.setCurrentIndex(active_index)
        super().restore_state()
