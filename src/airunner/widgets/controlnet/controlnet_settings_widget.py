from airunner.data.bootstrap.controlnet_bootstrap_data import controlnet_bootstrap_data
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.controlnet.templates.controlnet_settings_widget_ui import Ui_controlnet_settings_widget


class ControlnetSettingsWidget(BaseWidget):
    widget_class_ = Ui_controlnet_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.controlnet.blockSignals(True)
        self.ui.controlnet.clear()
        current_index = 0
        for index, item in enumerate(controlnet_bootstrap_data):
            self.ui.controlnet.addItem(item["display_name"])
            if self.controlnet_image_settings.controlnet == item["display_name"]:
                current_index = index
        self.ui.controlnet.setCurrentIndex(current_index)
        self.ui.controlnet.blockSignals(False)

    def controlnet_changed(self, val):
        self.update_controlnet_image_settings("controlnet", controlnet_bootstrap_data[val]["display_name"])
