from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.speecht5_preferences_ui import (
    Ui_speecht5_preferences,
)
from airunner.data.models import SpeechT5Settings


class SpeechT5PreferencesWidget(BaseWidget):
    widget_class_ = Ui_speecht5_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        self.ui.voice_combobox.clear()

        for element in elements:
            element.blockSignals(False)

    def language_changed(self, text):
        # SpeechT5Settings.objects.update(
        #     language=text,
        #     gender=self.ui.gender_combobox.currentText(),
        #     voice=self.ui.voice_combobox.currentText(),
        # )
        pass

    def voice_changed(self, text):
        # SpeechT5Settings.objects.update(
        #     voice=text,
        # )
        pass

    def gender_changed(self, text):
        # SpeechT5Settings.objects.update(
        #     gender=text,
        #     voice=self.ui.voice_combobox.currentText(),
        # )
        pass
