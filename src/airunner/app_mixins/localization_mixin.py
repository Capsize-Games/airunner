"""Localization and setup-wizard helpers for App."""

from __future__ import annotations

import os
from typing import Dict, Optional

from PySide6.QtCore import QLocale, QTranslator

from airunner.app_installer import AppInstaller
from airunner.models.application_settings import (
    ApplicationSettings,
)
from airunner.models.path_settings import PathSettings
from airunner.enums import AVAILABLE_LANGUAGES
from airunner.enums import LANGUAGE_TO_LOCALE_MAP
from airunner.enums import LOCALE_TO_LANGUAGE_MAP
from airunner.enums import AvailableLanguage
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_DISABLE_SETUP_WIZARD


class LocalizationMixin:
    """Manage translations and the first-run setup wizard."""

    def on_update_locale_signal(self, data: dict) -> None:
        """Handle locale update signals."""
        self.set_translations(data)

    def set_translations(self, data: Optional[Dict] = None) -> None:
        """Set application translations based on language settings."""
        locale_language = None
        locale_language_string = (
            data.get("gui_language", None) if data else None
        )
        if locale_language_string:
            locale_language = LANGUAGE_TO_LOCALE_MAP[
                AvailableLanguage(locale_language_string)
            ]

        if not locale_language:
            # gui_language was moved from language_settings DB table to
            # QSettings by migration d2ab5f1c9a7e.
            from airunner.utils.settings.get_qsettings import get_qsettings

            qs = get_qsettings()
            qs.beginGroup("language")
            gui_language = qs.value("gui_language", None)
            qs.endGroup()
            if gui_language:
                try:
                    language = AvailableLanguage(gui_language)
                except ValueError:
                    language = AvailableLanguage.EN

                try:
                    locale_language = LANGUAGE_TO_LOCALE_MAP[language]
                except KeyError:
                    locale_language = LANGUAGE_TO_LOCALE_MAP.get(
                        AvailableLanguage.EN
                    )
        if not locale_language:
            locale_language = QLocale.system().language()
        if locale_language not in LANGUAGE_TO_LOCALE_MAP:
            locale_language = None
        if locale_language is not None and (
            LOCALE_TO_LANGUAGE_MAP[locale_language]
            not in AVAILABLE_LANGUAGES["gui_language"]
        ):
            locale_language = None
        if not locale_language:
            locale_language = QLocale.English

        self._load_translations(locale=QLocale(locale_language))

    @staticmethod
    def run_setup_wizard() -> None:
        """Run the application setup wizard if needed."""
        if AIRUNNER_DISABLE_SETUP_WIZARD:
            return

        application_settings = ApplicationSettings.objects.first()
        path_settings = PathSettings.objects.first()
        if path_settings is None:
            PathSettings.objects.create()
            path_settings = PathSettings.objects.first()
        if application_settings is None:
            ApplicationSettings.objects.create()
            application_settings = ApplicationSettings.objects.first()

        base_path = path_settings.base_path
        if (
            not os.path.exists(base_path)
            or application_settings.run_setup_wizard
        ):
            AppInstaller()

    def _load_translations(self, locale: Optional[QLocale] = None):
        """Load and install the appropriate translation file."""
        if not locale:
            locale = QLocale.system()

        translations_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "translations",
        )
        translations_dir = os.path.abspath(translations_dir)

        old_translator = getattr(self.app, "translator", None)
        if old_translator is not None:
            self.app.removeTranslator(old_translator)
            self.app.translator = None

        translator = QTranslator()
        language_map = {
            QLocale.English: "english",
            QLocale.Japanese: "japanese",
        }
        base_name = language_map.get(locale.language(), "english")
        qm_path = os.path.join(translations_dir, f"{base_name}.qm")
        if os.path.exists(qm_path) and translator.load(qm_path):
            self.app.installTranslator(translator)
            self.app.translator = translator
            self.retranslate_ui_signal()
            return

        if base_name == "english":
            self.app.translator = None
            return

        english_qm_path = os.path.join(translations_dir, "english.qm")
        fallback_translator = QTranslator()
        if os.path.exists(english_qm_path) and fallback_translator.load(
            english_qm_path
        ):
            self.app.installTranslator(fallback_translator)
            self.app.translator = fallback_translator
            self.retranslate_ui_signal()
        else:
            self.app.translator = None

    def retranslate_ui_signal(self) -> None:
        """Emit the signal used to retranslate all UI elements."""
        self.emit_signal(SignalCode.RETRANSLATE_UI_SIGNAL)