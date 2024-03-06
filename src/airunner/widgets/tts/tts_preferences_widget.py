from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.tts_preferences_ui import Ui_tts_preferences


class TTSPreferencesWidget(BaseWidget):
    widget_class_ = Ui_tts_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_form()
    
    def initialize_form(self):
        elements = [
            self.ui.enable_tts,
            self.ui.model_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        tts_model = self.settings["tts_settings"]["model"]
        self.ui.enable_tts.setChecked(self.settings["tts_settings"]["enable_tts"])
        self.ui.model_combobox.clear()
        models = ["Bark", "SpeechT5", "Espeak"]
        self.ui.model_combobox.addItems(models)
        self.ui.model_combobox.setCurrentText(tts_model)
        self.ui.bark_preferences.setVisible(tts_model == "Bark")
        self.ui.speecht5_preferences.setVisible(tts_model == "SpeechT5")
        self.ui.espeak_preferences.setVisible(tts_model == "Espeak")

        for element in elements:
            element.blockSignals(False)

    def enable_tts_changed(self, val):
        settings = self.settings
        settings["tts_settings"]["enable_tts"] = val
        self.settings = settings

    def model_changed(self, val):
        settings = self.settings
        settings["tts_settings"]["model"] = val
        self.settings = settings
        self.initialize_form()
