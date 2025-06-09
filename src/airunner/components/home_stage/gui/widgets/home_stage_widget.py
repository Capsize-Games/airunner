from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.gui.widgets.base_widget import BaseWidget


class HomeStageWidget(BaseWidget):
    """Code editor widget with line numbers and syntax highlighting."""

    widget_class_ = Ui_home_stage_widget
