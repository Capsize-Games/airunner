from PySide6.QtCore import Slot

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tool_tab.templates.tool_tab_ui import Ui_tool_tab_widget
from airunner.enums import SignalCode
from airunner.data.models import SplitterSetting, Tab


class ToolTabWidget(BaseWidget):
    widget_class_ = Ui_tool_tab_widget

    def __init__(self, *args, **kwargs):
        self.splitters = [
            "llm_splitter"
        ]
        super().__init__(*args, **kwargs)        
        self.ui.tool_tab_widget_container.currentChanged.connect(
            self.on_tab_section_changed
        )

    @Slot(int)
    def on_tab_section_changed(self, index: int):
        Tab.update_tabs("right", self.ui.tool_tab_widget_container, index)
    
    def restore_state(self):
        active_index = 0
        tabs = Tab.objects.filter_by(section="right")
        for tab in tabs:
            if tab.active:
                active_index = tab.index
                break
        self.ui.tool_tab_widget_container.setCurrentIndex(active_index)
        super().restore_state()
