from PySide6.QtCore import Slot
from airunner.components.art.gui.widgets.canvas.templates.image_manipulation_tools_container_ui import (
    Ui_image_manipulation_tools_container,
)
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.utils.settings.get_qsettings import get_qsettings


class ImageManipulationToolsContainer(BaseWidget):
    widget_class_ = Ui_image_manipulation_tools_container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qsettings = get_qsettings()
        self.ui.image_manipulation_tools_tab_container.currentChanged.connect(
            self.on_tab_changed
        )

    @Slot(int)
    def on_tab_changed(self, index: int):
        self.qsettings.setValue(
            "tabs/image_manipulation_tools_container/active_index", index
        )

    def showEvent(self, event):
        super().showEvent(event)
        active_index = int(
            self.qsettings.value(
                "tabs/image_manipulation_tools_container/active_index", 0
            )
        )
        self.ui.image_manipulation_tools_tab_container.setCurrentIndex(
            active_index
        )
