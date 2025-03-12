from PySide6.QtCore import Slot
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.stablediffusion.templates.stablediffusion_tool_tab_ui import Ui_stablediffusion_tool_tab_widget
from airunner.data.models import ApplicationSettings

class StablediffusionToolTabWidget(BaseWidget):
    widget_class_ = Ui_stablediffusion_tool_tab_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.tool_tab_widget_container.currentChanged.connect(self.on_tab_section_changed)
    
    @Slot(int)
    def on_tab_section_changed(self, index: int):
        ApplicationSettings.update_active_tabs("stablediffusion_tool_tab", index)

    def showEvent(self, event):
        super().showEvent(event)
        settings = ApplicationSettings.objects.first()
        tabs = settings.tabs.get("stablediffusion_tool_tab", None)
        if not tabs:
            tabs = [
                {
                    "name": f"{self.ui.tool_tab_widget_container.tabText(index)}",
                    "index": index,
                    "active": False
                } for index in range(self.ui.tool_tab_widget_container.count())
            ]
            ApplicationSettings.objects.update(
                settings.id,
                tabs={
                    **settings.tabs,
                    "stablediffusion_tool_tab": tabs
                }
            )
        for i, tab in enumerate(tabs):
            if tab.get("active", False):
                self.ui.tool_tab_widget_container.setCurrentIndex(i)
                break