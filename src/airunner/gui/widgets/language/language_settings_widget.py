from PySide6.QtCore import Slot

from airunner.data.models.language_settings import LanguageSettings
from airunner.gui.widgets.base_widget import BaseWidget

from airunner.gui.widgets.language.templates.language_settings_ui import (
    Ui_language_settings_widget,
)
from airunner.gui.windows.main.ai_model_mixin import AIModelMixin
from airunner.enums import (
    AvailableLanguage,
    LANGUAGE_DISPLAY_MAP,
    AVAILABLE_LANGUAGES,
)


class LanguageSettingsWidget(BaseWidget, AIModelMixin):
    widget_class_ = Ui_language_settings_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # create a reversed mapping of LANGUAGE_DISPLAY_MAP
        self.display_to_language_map = {
            v: k for k, v in LANGUAGE_DISPLAY_MAP.items()
        }

        self.ui.gui_language.blockSignals(True)
        self.ui.user_language.blockSignals(True)
        self.ui.bot_language.blockSignals(True)
        self.ui.gui_language.clear()
        self.ui.user_language.clear()
        self.ui.bot_language.clear()
        self.ui.gui_language.addItems(
            LANGUAGE_DISPLAY_MAP[lang]
            for lang in AVAILABLE_LANGUAGES["gui_language"]
        )
        self.ui.user_language.addItems(
            LANGUAGE_DISPLAY_MAP[lang]
            for lang in AVAILABLE_LANGUAGES["user_language"]
        )
        self.ui.bot_language.addItems(
            LANGUAGE_DISPLAY_MAP[lang]
            for lang in AVAILABLE_LANGUAGES["bot_language"]
        )
        settings = LanguageSettings.objects.first()
        if settings:
            self.ui.gui_language.setCurrentText(
                LANGUAGE_DISPLAY_MAP[AvailableLanguage(settings.gui_language)]
            )
            self.ui.user_language.setCurrentText(
                LANGUAGE_DISPLAY_MAP[AvailableLanguage(settings.user_language)]
            )
            self.ui.bot_language.setCurrentText(
                LANGUAGE_DISPLAY_MAP[AvailableLanguage(settings.bot_language)]
            )
        self.ui.gui_language.blockSignals(False)
        self.ui.user_language.blockSignals(False)
        self.ui.bot_language.blockSignals(False)

    @Slot(str)
    def on_gui_language_currentTextChanged(self, val: str):
        self.update_language_settings("gui_language", val)

    @Slot(str)
    def on_user_language_currentTextChanged(self, val: str):
        self.update_language_settings("user_language", val)

    @Slot(str)
    def on_bot_language_currentTextChanged(self, val: str):
        self.update_language_settings("bot_language", val)

    def update_language_settings(self, key: str, value: str):
        # convert value to AvailableLanguage enum
        value = self.display_to_language_map.get(value, value).value

        settings = LanguageSettings.objects.first()
        if not settings:
            default_language = AvailableLanguage.EN.value
            data = dict(
                gui_language=default_language,
                user_language=default_language,
                bot_language=default_language,
            )
            data.update({key: value})
            LanguageSettings.objects.create(**data)
        else:
            data = {}
            data[key] = value
            LanguageSettings.objects.update(settings.id, **data)
        settings = LanguageSettings.objects.first()

        data = dict(
            gui_language=settings.gui_language,
            user_language=settings.user_language,
            bot_language=settings.bot_language,
        )

        self.api.update_locale(data)
