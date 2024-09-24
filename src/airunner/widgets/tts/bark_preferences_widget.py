from airunner.settings import BARK_VOICES
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.bark_preferences_ui import Ui_bark_preferences


class BarkPreferencesWidget(BaseWidget):
    widget_class_ = Ui_bark_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voices = BARK_VOICES

    def initialize_form(self):
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        language = self.bark_settings.language
        gender = self.bark_settings.gender
        voice = self.bark_settings.voice

        self.ui.voice_combobox.clear()
        self.ui.language_combobox.addItems(self.voices.keys())
        self.ui.language_combobox.setCurrentText(language)
        self.ui.gender_combobox.setCurrentText(gender)
        self.ui.voice_combobox.addItems(self.voices[language][gender])
        self.ui.voice_combobox.setCurrentText(voice)

        for element in elements:
            element.blockSignals(False)

    def language_changed(self, text):
        self.update_bark_settings("language", text)
        self.update_bark_settings("gender", self.ui.gender_combobox.currentText())
        self.update_bark_settings("voice", self.ui.voice_combobox.currentText())


    def voice_changed(self, text):
        self.update_bark_settings("voice", text)

    def gender_changed(self, text):
        self.update_bark_settings("gender", text)
        self.update_bark_settings("voice", self.ui.voice_combobox.currentText())
