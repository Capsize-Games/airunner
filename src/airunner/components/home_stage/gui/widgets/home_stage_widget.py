from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.home_stage.gui.widgets.training_widget import (
    TrainingWidget,
)
from airunner.components.model_management.gui.model_status_widget import (
    ModelStatusWidget,
)


class HomeStageWidget(BaseWidget):
    """Home stage widget with native PySide6 panels."""

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grid_layout = self.ui.gridLayout

        # Two-column layout: Training | Model Status
        self.training_panel = TrainingWidget()
        grid_layout.addWidget(self.training_panel, 0, 0)

        self.model_status_panel = ModelStatusWidget()
        grid_layout.addWidget(self.model_status_panel, 0, 1)
