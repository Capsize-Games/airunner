from PySide6.QtCore import QSettings

from airunner.settings import ORGANIZATION, APPLICATION_NAME
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tool_tab.templates.tool_tab_ui import Ui_tool_tab_widget


class ToolTabWidget(BaseWidget):
    widget_class_ = Ui_tool_tab_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
