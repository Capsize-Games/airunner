from PySide6.QtCore import Slot

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tool_tab.templates.tool_tab_ui import Ui_tool_tab_widget
from airunner.enums import SignalCode
from airunner.data.models import SplitterSetting, ApplicationSettings


class ToolTabWidget(BaseWidget):
    widget_class_ = Ui_tool_tab_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for item in (
            (SignalCode.QUIT_APPLICATION, lambda message: self.save_state()),
        ):
            self.register(item[0], item[1])
        
        self.ui.tool_tab_widget_container.currentChanged.connect(self.on_tab_section_changed)

    @Slot(int)
    def on_tab_section_changed(self, index: int):
        ApplicationSettings.update_active_tabs("right", index)

    def save_state(self):
        settings = SplitterSetting.objects.filter_by(name="llm_splitter").first()
        if not settings:
            SplitterSetting.objects.create(
                name="llm_splitter",
                splitter_settings=self.ui.llm_splitter.saveState()
            )
        else:
            SplitterSetting.objects.update(
                settings.id,
                llm_splitter=self.ui.llm_splitter.saveState()
            )
    
    def restore_state(self):
        # Set the default tab index
        active_index = 0
        settings = ApplicationSettings.objects.first()
        for tab in settings.tabs["right"]:
            if tab["active"]:
                active_index = tab["index"]
                break
        self.ui.tool_tab_widget_container.setCurrentIndex(active_index)

        settings = SplitterSetting.objects.filter_by(name="llm_splitter").first()
        if settings:
            self.ui.llm_splitter.restoreState(settings.splitter_settings)
