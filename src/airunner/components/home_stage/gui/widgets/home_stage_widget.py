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
        old_left_widget = grid_layout.itemAtPosition(0, 0).widget()
        if old_left_widget:
            old_left_widget.setParent(None)
        self.training_panel = TrainingWidget()
        grid_layout.addWidget(self.training_panel, 0, 0)

        old_right_widget = grid_layout.itemAtPosition(0, 1).widget()
        if old_right_widget:
            old_right_widget.setParent(None)
        self.system_resources_panel = SystemResourcesPanelWidget()
        grid_layout.addWidget(self.system_resources_panel, 0, 1)
