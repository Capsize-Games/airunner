from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.stt.gui.widgets.templates.stt_settings_ui import Ui_stt_settings


class STTSettingsWidget(BaseWidget):
    widget_class_ = Ui_stt_settings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
