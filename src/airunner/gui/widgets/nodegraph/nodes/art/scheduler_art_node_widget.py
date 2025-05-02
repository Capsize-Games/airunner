from PySide6.QtCore import Slot

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.nodegraph.nodes.art.templates.scheduler_ui import (
    Ui_scheduler_node,
)
from airunner.enums import Scheduler


class SchedulerArtNodeWidget(BaseWidget):
    widget_class_ = Ui_scheduler_node
    _scheduler: Scheduler = Scheduler.DPM_PP_2M_SDE_K

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.scheduler_combobox.addItems(
            [scheduler.value for scheduler in Scheduler]
        )
        self.ui.scheduler_combobox.setCurrentText(self._scheduler.value)

    @Slot(str)
    def on_scheduler_combobox_currentTextChanged(self, text: str):
        self._scheduler = Scheduler(text)
