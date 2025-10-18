from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.home_stage.gui.widgets.system_resources_panel_widget import (
    SystemResourcesPanelWidget,
)
from airunner.components.home_stage.gui.widgets.training_widget import (
    TrainingWidget,
)


class HomeStageWidget(BaseWidget):
    """Home stage widget with native PySide6 panels."""

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Replace placeholder widgets in the grid with actual panel widgets
        grid_layout = self.ui.gridLayout

        # Two-column layout: Training Panel (left), System Resources (right)
        self.training_panel = TrainingWidget()
        grid_layout.addWidget(self.training_panel, 0, 0)

        self.system_resources_panel = SystemResourcesPanelWidget()
        grid_layout.addWidget(self.system_resources_panel, 0, 1)
