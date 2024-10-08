from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.speecht5_preferences_ui import Ui_speecht5_preferences


class SpeechT5PreferencesWidget(BaseWidget):
    widget_class_ = Ui_speecht5_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        self.ui.rate.init(current_value=self.speech_t5_settings.rate)
        self.ui.volume.init(current_value=self.speech_t5_settings.volume)
        self.ui.pitch.init(current_value=self.speech_t5_settings.pitch)
