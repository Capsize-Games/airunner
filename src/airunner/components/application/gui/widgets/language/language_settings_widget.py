from PySide6.QtCore import Slot
from PySide6.QtCore import QSignalBlocker

from airunner.components.settings.data.language_settings import LanguageSettings
from airunner.components.application.gui.widgets.base_widget import BaseWidget

from airunner.components.application.gui.widgets.language.templates.language_settings_ui import (
    Ui_language_settings_widget,
)
from airunner.components.application.gui.windows.main.ai_model_mixin import AIModelMixin
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

        self._signals_connected = False
        self._connect_signals()

        # Use QSignalBlocker to safely block signals during setup
        with QSignalBlocker(self.ui.gui_language), QSignalBlocker(
            self.ui.user_language
        ), QSignalBlocker(self.ui.bot_language):
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
                try:
                    lang = AvailableLanguage(settings.gui_language)
                except ValueError:
                    lang = AvailableLanguage.EN
                try:
                    txt = LANGUAGE_DISPLAY_MAP[lang]
                except KeyError:
                    txt = LANGUAGE_DISPLAY_MAP[AvailableLanguage.EN]
                self.ui.gui_language.setCurrentText(txt)

                try:
                    lang = AvailableLanguage(settings.user_language)
                except ValueError:
                    lang = AvailableLanguage.EN
                txt = LANGUAGE_DISPLAY_MAP[lang]
                self.ui.user_language.setCurrentText(txt)

                try:
                    lang = AvailableLanguage(settings.bot_language)
                except ValueError:
                    lang = AvailableLanguage.EN
                txt = LANGUAGE_DISPLAY_MAP[lang]
                self.ui.bot_language.setCurrentText(txt)

    def _connect_signals(self):
        if not self._signals_connected:
            self.ui.gui_language.currentTextChanged.connect(
                self.on_gui_language_currentTextChanged
            )
            self.ui.user_language.currentTextChanged.connect(
                self.on_user_language_currentTextChanged
            )
            self.ui.bot_language.currentTextChanged.connect(
                self.on_bot_language_currentTextChanged
            )
            self._signals_connected = True

    def _disconnect_signals(self):
        if self._signals_connected:
            try:
                self.ui.gui_language.currentTextChanged.disconnect(
                    self.on_gui_language_currentTextChanged
                )
            except Exception:
                pass
            try:
                self.ui.user_language.currentTextChanged.disconnect(
                    self.on_user_language_currentTextChanged
                )
            except Exception:
                pass
            try:
                self.ui.bot_language.currentTextChanged.disconnect(
                    self.on_bot_language_currentTextChanged
                )
            except Exception:
                pass
            self._signals_connected = False

    def closeEvent(self, event):
        self._disconnect_signals()
        super().closeEvent(event)

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

        if key == "gui_language":
            self.api.update_locale(data)
