from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.tts_preferences_ui import Ui_tts_preferences


class TTSPreferencesWidget(BaseWidget):
    widget_class_ = Ui_tts_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voices = {
            "English": {
                "Male": [
                    "v2/en_speaker_0",
                    "v2/en_speaker_1",
                    "v2/en_speaker_2",
                    "v2/en_speaker_3",
                    "v2/en_speaker_4",
                    "v2/en_speaker_5",
                    "v2/en_speaker_6",
                    "v2/en_speaker_7",
                    "v2/en_speaker_8",
                ],
                "Female": [
                    "v2/en_speaker_9"
                ],
            },
            "Chinese (Simplified)": {
                "Male": [
                    "v2/zh_speaker_0",
                    "v2/zh_speaker_1",
                    "v2/zh_speaker_2",
                    "v2/zh_speaker_3",
                    "v2/zh_speaker_5",
                    "v2/zh_speaker_8",
                ],
                "Female": [
                    "v2/zh_speaker_4",
                    "v2/zh_speaker_6",
                    "v2/zh_speaker_7",
                    "v2/zh_speaker_9",
                ],
            },
            "French": {
                "Male": [
                    "v2/fr_speaker_0",
                    "v2/fr_speaker_3",
                    "v2/fr_speaker_4",
                    "v2/fr_speaker_6",
                    "v2/fr_speaker_7",
                    "v2/fr_speaker_8",
                    "v2/fr_speaker_9",
                ],
                "Female": [
                    "v2/fr_speaker_1",
                    "v2/fr_speaker_2",
                    "v2/fr_speaker_5",
                ],
            },
            "German": {
                "Male": [
                    "v2/de_speaker_0",
                    "v2/de_speaker_1",
                    "v2/de_speaker_2",
                    "v2/de_speaker_4",
                    "v2/de_speaker_5",
                    "v2/de_speaker_6",
                    "v2/de_speaker_7",
                    "v2/de_speaker_9",
                ],
                "Female": [
                    "v2/de_speaker_3",
                    "v2/de_speaker_8",
                ],
            },
            "Hindi": {
                "Male": [
                    "v2/hi_speaker_2",
                    "v2/hi_speaker_5",
                    "v2/hi_speaker_6",
                    "v2/hi_speaker_7",
                    "v2/hi_speaker_8",
                ],
                "Female": [
                    "v2/hi_speaker_0",
                    "v2/hi_speaker_1",
                    "v2/hi_speaker_3",
                    "v2/hi_speaker_4",
                    "v2/hi_speaker_9",
                ],
            },
            "Italian": {
                "Male": [
                    "v2/it_speaker_0",
                    "v2/it_speaker_1",
                    "v2/it_speaker_3",
                    "v2/it_speaker_4",
                    "v2/it_speaker_5",
                    "v2/it_speaker_6",
                    "v2/it_speaker_8",
                ],
                "Female": [
                    "v2/it_speaker_2",
                    "v2/it_speaker_7",
                    "v2/it_speaker_9",
                ],
            },
            "Japanese": {
                "Male": [
                    "v2/ja_speaker_2",
                    "v2/ja_speaker_6",
                ],
                "Female": [
                    "v2/ja_speaker_0",
                    "v2/ja_speaker_1",
                    "v2/ja_speaker_3",
                    "v2/ja_speaker_4",
                    "v2/ja_speaker_5",
                    "v2/ja_speaker_7",
                    "v2/ja_speaker_8",
                    "v2/ja_speaker_9",
                ],
            },
            "Korean": {
                "Male": [
                    "v2/ko_speaker_1",
                    "v2/ko_speaker_2",
                    "v2/ko_speaker_3",
                    "v2/ko_speaker_4",
                    "v2/ko_speaker_5",
                    "v2/ko_speaker_6",
                    "v2/ko_speaker_7",
                    "v2/ko_speaker_8",
                    "v2/ko_speaker_9",
                ],
                "Female": [
                    "v2/ko_speaker_0",
                ],
            },
            "Polish": {
                "Male": [
                    "v2/pl_speaker_0",
                    "v2/pl_speaker_1",
                    "v2/pl_speaker_2",
                    "v2/pl_speaker_3",
                    "v2/pl_speaker_5",
                    "v2/pl_speaker_7",
                    "v2/pl_speaker_8",
                ],
                "Female": [
                    "v2/pl_speaker_4",
                    "v2/pl_speaker_6",
                    "v2/pl_speaker_9",
                ],
            },
            "Portuguese": {
                "Male": [
                    "v2/pt_speaker_0",
                    "v2/pt_speaker_1",
                    "v2/pt_speaker_2",
                    "v2/pt_speaker_3",
                    "v2/pt_speaker_4",
                    "v2/pt_speaker_5",
                    "v2/pt_speaker_6",
                    "v2/pt_speaker_7",
                    "v2/pt_speaker_8",
                    "v2/pt_speaker_9",
                ],
                "Female": [],
            },
            "Russian": {
                "Male": [
                    "v2/ru_speaker_0",
                    "v2/ru_speaker_1",
                    "v2/ru_speaker_2",
                    "v2/ru_speaker_3",
                    "v2/ru_speaker_4",
                    "v2/ru_speaker_7",
                    "v2/ru_speaker_8",
                ],
                "Female": [
                    "v2/ru_speaker_5",
                    "v2/ru_speaker_6",
                    "v2/ru_speaker_9",
                ],
            },
            "Spanish": {
                "Male": [
                    "v2/es_speaker_0",
                    "v2/es_speaker_1",
                    "v2/es_speaker_2",
                    "v2/es_speaker_3",
                    "v2/es_speaker_4",
                    "v2/es_speaker_5",
                    "v2/es_speaker_6",
                    "v2/es_speaker_7",
                ],
                "Female": [
                    "v2/es_speaker_8",
                    "v2/es_speaker_9",
                ],
            },
            "Turkish": {
                "Male": [
                    "v2/tr_speaker_0",
                    "v2/tr_speaker_1",
                    "v2/tr_speaker_2",
                    "v2/tr_speaker_3",
                    "v2/tr_speaker_6",
                    "v2/tr_speaker_7",
                    "v2/tr_speaker_8",
                    "v2/tr_speaker_9",
                ],
                "Female": [
                    "v2/tr_speaker_4",
                    "v2/tr_speaker_5",
                ],
            },
        }
        self.initialize_form()
    
    def initialize_form(self):
        self.ui.language_combobox.blockSignals(True)
        self.ui.gender_combobox.blockSignals(True)
        self.ui.voice_combobox.blockSignals(True)
        self.ui.use_bark.blockSignals(True)
        self.ui.enable_tts.blockSignals(True)

        language = self.app.settings["tts_settings"]["language"]
        gender = self.app.settings["tts_settings"]["gender"]
        voice = self.app.settings["tts_settings"]["voice"]

        self.ui.voice_combobox.clear()

        self.ui.language_combobox.addItems(self.voices.keys())
        self.ui.language_combobox.setCurrentText(language)
        self.ui.gender_combobox.setCurrentText(gender)
        self.ui.voice_combobox.addItems(self.voices[language][gender])
        self.ui.voice_combobox.setCurrentText(voice)
        self.ui.use_bark.setChecked(self.app.settings["tts_settings"]["use_bark"])
        self.ui.enable_tts.setChecked(self.app.settings["tts_settings"]["enable_tts"])

        self.ui.language_combobox.blockSignals(False)
        self.ui.gender_combobox.blockSignals(False)
        self.ui.voice_combobox.blockSignals(False)
        self.ui.use_bark.blockSignals(False)
        self.ui.enable_tts.blockSignals(False)


    def language_changed(self, text):
        self.initialize_form()
        settings = self.app.settings
        settings["tts_settings"]["language"] = text
        settings["tts_settings"]["gender"] = self.ui.gender_combobox.currentText()
        settings["tts_settings"]["voice"] = self.ui.voice_combobox.currentText()
        self.app.settings = settings

    def voice_changed(self, text):
        self.initialize_form()
        settings = self.app.settings
        settings["tts_settings"]["voice"] = text
        self.app.settings = settings

    def gender_changed(self, text):
        self.initialize_form()
        settings = self.app.settings
        settings["tts_settings"]["gender"] = text
        settings["tts_settings"]["voice"] = self.ui.voice_combobox.currentText()
        self.app.settings = settings

    def use_bark_changed(self, val):
        self.initialize_form()
        settings = self.app.settings
        settings["tts_settings"]["use_bark"] = val
        self.app.settings = settings

    def enable_tts_changed(self, val):
        self.initialize_form()
        settings = self.app.settings
        settings["tts_settings"]["enable_tts"] = val
        self.app.settings = settings