from airunner.enums import Language
from airunner.settings import TRANSLATION_LANGUAGES, TRANSLATION_MODELS, MALE, FEMALE
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.translation_preferences.templates.translation_preferences_widget_ui import \
    Ui_translation_preferences


class TranslationPreferencesWidget(BaseWidget):
    widget_class_ = Ui_translation_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initialize_language_combobox()
        self.initialize_voice_combobox()
        self.initialize_translation_model_combobox()
        self.ui.translate_groupbox.blockSignals(True)
        self.ui.translate_groupbox.setChecked(self.translation_settings.enabled)
        self.ui.translate_groupbox.blockSignals(False)

    def initialize_language_combobox(self):
        self.ui.language_combobox.blockSignals(True)
        self.ui.language_combobox.clear()
        self.ui.language_combobox.addItems(TRANSLATION_LANGUAGES)
        self.ui.language_combobox.setCurrentText(self.translation_settings.language)
        self.ui.language_combobox.blockSignals(False)

    def initialize_voice_combobox(self):
        current_language = self.translation_settings.language
        gender = self.translation_settings.gender
        self.ui.voice_combobox.blockSignals(True)
        self.ui.male_radio_button.blockSignals(True)
        self.ui.female_radio_button.blockSignals(True)
        self.ui.voice_combobox.clear()
        self.ui.male_radio_button.setChecked(gender == MALE.value)
        self.ui.female_radio_button.setChecked(gender == FEMALE.value)
        self.ui.voice_combobox.setCurrentText(self.translation_settings.voice)
        self.ui.voice_combobox.blockSignals(False)
        self.ui.male_radio_button.blockSignals(False)
        self.ui.female_radio_button.blockSignals(False)

    def initialize_translation_model_combobox(self):
        self.ui.translation_model_combobox.blockSignals(True)
        self.ui.translation_model_combobox.clear()
        self.ui.translation_model_combobox.addItems(TRANSLATION_MODELS)
        for language in Language:
            if language.value == self.translation_settings.language:
                self.ui.translation_model_combobox.setCurrentText(self.translation_settings.translation_model)
                break
        self.ui.translation_model_combobox.setCurrentText(self.translation_settings.translation_model)
        self.ui.translation_model_combobox.blockSignals(False)

    def language_text_changed(self, val):
        self.update_translation_settings("language", val)
        self.initialize_voice_combobox()

    def voice_text_changed(self, val):
        self.update_translation_settings("voice", val)

    def translation_model_changed(self, val):
        self.update_translation_settings("translation_model", val)

    def toggle_translation(self, val):
        self.update_translation_settings("enabled", val)

    def male_clicked(self):
        self.initialize_voice_combobox()
        self.update_translation_settings("gender", MALE.value)

    def female_clicked(self):
        self.update_translation_settings("gender", FEMALE.value)
        self.initialize_voice_combobox()
