from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.lora.lora_container_ui import Ui_lora_container


class LoraContainerWidget(BaseWidget):
    widget_class_ = Ui_lora_container

    def __init__(self, *args, **kwargs):
        self.app = kwargs.pop("app", None)
        super().__init__(*args, **kwargs)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.ui.toggleAllLora.setStyleSheet("""
        margin-left: 11px;
        background-color: transparent;
        """)
        self.ui.toggleAllLora.clicked.connect(self.toggle_all_lora)

    def toggle_all_lora(self, checked):
        for i in range(self.ui.lora_scroll_area.widget().layout().count()):
            lora_widget = self.ui.lora_scroll_area.widget().layout().itemAt(i).widget()
            if lora_widget:
                lora_widget.enabledCheckbox.setChecked(checked)
