from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.stablediffusion.templates.stablediffusion_tool_tab_ui import (
    Ui_stablediffusion_tool_tab_widget,
)
from airunner.data.models import Tab


class StablediffusionToolTabWidget(BaseWidget):
    widget_class_ = Ui_stablediffusion_tool_tab_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.tool_tab_widget_container.currentChanged.connect(
            self.on_tool_tab_widget_container_currentChanged
        )

    @Slot(int)
    def on_tool_tab_widget_container_currentChanged(self, index: int):
        Tab.update_tabs(
            "stablediffusion_tool_tab",
            self.ui.tool_tab_widget_container,
            index,
        )

    def showEvent(self, event):
        super().showEvent(event)
        section = "stablediffusion_tool_tab"
        for index in range(self.ui.tool_tab_widget_container.count()):
            tab_text = self.ui.tool_tab_widget_container.tabText(index)
            tab = Tab.objects.filter_by_first(section=section, name=tab_text)
            if not tab:
                Tab.objects.create(
                    section=section, name=tab_text, index=index, active=False
                )

        tabs = Tab.objects.filter_by(section=section)
        for tab in tabs:
            if tab.active:
                self.ui.tool_tab_widget_container.setCurrentIndex(tab.index)
                break
