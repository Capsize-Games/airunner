from airunner.data.models.settings_models import ControlnetModel
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.controlnet.templates.controlnet_settings_widget_ui import Ui_controlnet_settings_widget


class ControlnetSettingsWidget(BaseWidget):
    widget_class_ = Ui_controlnet_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self._version = None
        self._load_controlnet_models()

    def controlnet_changed(self, val):
        self.update_controlnet_settings("controlnet", val)

    def on_application_settings_changed_signal(self):
        self._load_controlnet_models()

    def _load_controlnet_models(self):
        if self._version is None or self._version != self.generator_settings.version:
            self._version = self.generator_settings.version
            current_index = 0
            session = self.db_handler.get_db_session()
            controlnet_models = session.query(ControlnetModel).filter_by(
                version=self.generator_settings.version
            ).all()
            session.close()
            self.ui.controlnet.blockSignals(True)
            self.ui.controlnet.clear()
            for index, item in enumerate(controlnet_models):
                self.ui.controlnet.addItem(item.display_name)
                if self.controlnet_settings.controlnet == item.display_name:
                    current_index = index
            self.ui.controlnet.setCurrentIndex(current_index)
            self.ui.controlnet.blockSignals(False)
