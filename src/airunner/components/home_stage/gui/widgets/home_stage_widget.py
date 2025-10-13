from airunner.components.home_stage.gui.widgets.templates.home_stage_ui import (
    Ui_home_stage_widget,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.home_stage.gui.widgets.knowledge_base_panel_widget import (
    KnowledgeBasePanelWidget,
)
from airunner.components.home_stage.gui.widgets.system_resources_panel_widget import (
    SystemResourcesPanelWidget,
)
from airunner.components.home_stage.gui.widgets.section_3_panel_widget import (
    Section3PanelWidget,
)
from airunner.components.home_stage.gui.widgets.section_4_panel_widget import (
    Section4PanelWidget,
)


class HomeStageWidget(BaseWidget):
    """Home stage widget with native PySide6 panels."""

    widget_class_ = Ui_home_stage_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Replace placeholder widgets in the grid with actual panel widgets
        grid_layout = self.ui.gridLayout

        # Row 0: Knowledge Base (0,0), System Resources (0,1)
        old_kb_widget = grid_layout.itemAtPosition(0, 0).widget()
        old_kb_widget.setParent(None)
        self.knowledge_base_panel = KnowledgeBasePanelWidget()
        grid_layout.addWidget(self.knowledge_base_panel, 0, 0)

        old_sr_widget = grid_layout.itemAtPosition(0, 1).widget()
        old_sr_widget.setParent(None)
        self.system_resources_panel = SystemResourcesPanelWidget()
        grid_layout.addWidget(self.system_resources_panel, 0, 1)

        # Row 1: Section 3 (1,0), Section 4 (1,1)
        old_s3_widget = grid_layout.itemAtPosition(1, 0).widget()
        old_s3_widget.setParent(None)
        self.section_3_panel = Section3PanelWidget()
        grid_layout.addWidget(self.section_3_panel, 1, 0)

        old_s4_widget = grid_layout.itemAtPosition(1, 1).widget()
        old_s4_widget.setParent(None)
        self.section_4_panel = Section4PanelWidget()
        grid_layout.addWidget(self.section_4_panel, 1, 1)
