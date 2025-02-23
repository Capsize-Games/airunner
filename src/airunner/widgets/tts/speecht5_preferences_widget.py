from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.speecht5_preferences_ui import Ui_speecht5_preferences


class SpeechT5PreferencesWidget(BaseWidget):
    widget_class_ = Ui_speecht5_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        voice = self.speech_t5_settings.voice
        self.ui.voice.setCurrentText(voice)

    def initialize_form(self):
        self.ui.pitch.init(current_value=self.speech_t5_settings.pitch / 100)

    def voice_changed(self, text):
        self.update_speech_t5_settings("voice", text)
