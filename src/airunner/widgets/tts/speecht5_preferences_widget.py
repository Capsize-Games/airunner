from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.speecht5_preferences_ui import Ui_speecht5_preferences


class SpeechT5PreferencesWidget(BaseWidget):
    widget_class_ = Ui_speecht5_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        elements = [
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        # gender = self.settings["tts_settings"]["gender"]
        # voice = self.settings["tts_settings"]["voice"]

        self.ui.voice_combobox.clear()
        # self.ui.gender_combobox.setCurrentText(gender)
        # self.ui.voice_combobox.addItems(self.voices[language][gender])
        # self.ui.voice_combobox.setCurrentText(voice)

        for element in elements:
            element.blockSignals(False)

    def voice_changed(self, text):
        self.update_tts_settings("voice", text)

    def gender_changed(self, text):
        self.update_tts_settings("gender", text)
        self.update_tts_settings("voice", self.ui.voice_combobox.currentText())
