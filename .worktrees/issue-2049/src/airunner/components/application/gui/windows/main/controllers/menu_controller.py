"""Menu construction and settings/legal dialog helpers for MainWindow."""

from __future__ import annotations

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.settings.gui.windows.settings.airunner_settings import (
    SettingsWindow,
)


class MenuController(MainWindowBase):
    """Build menus and show settings/legal dialogs."""

    def _add_legal_menu_items(self):
        """Add Terms, Privacy, and Age Agreement actions to the Help menu."""
        self.ui.menuAbout.addSeparator()
        self._add_legal_action(
            "actionAgeAgreement", "Age Restriction Policy", self._show_age_agreement
        )
        self._add_legal_action(
            "actionTermsOfService", "Terms of Service", self._show_terms_of_service
        )
        self._add_legal_action(
            "actionPrivacyPolicy", "Privacy Policy", self._show_privacy_policy
        )

    def _add_legal_action(self, attr: str, title: str, slot) -> None:
        """Append one legal document action to the Help menu."""
        action = QAction(title, self)
        action.triggered.connect(slot)
        self.ui.menuAbout.addAction(action)
        setattr(self, attr, action)

    def _add_download_models_menu_item(self):
        """Add Download Models and Privacy Settings actions to Tools."""
        self.ui.menuTools.addSeparator()
        self._add_tools_action(
            "actionDownloadModels",
            "Download Models...",
            "Download pre-configured models from HuggingFace",
            self._show_download_models_dialog,
        )
        self._add_tools_action(
            "actionPrivacySettings",
            "Privacy Settings...",
            "Manage external service connections and privacy options",
            self._show_privacy_settings,
        )

    def _add_tools_action(self, attr, title, tooltip, slot) -> None:
        """Append one action to the Tools menu."""
        action = QAction(title, self)
        action.setToolTip(tooltip)
        action.triggered.connect(slot)
        self.ui.menuTools.addAction(action)
        setattr(self, attr, action)

    def _show_privacy_settings(self):
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            PrivacyConsentDialog,
        )

        PrivacyConsentDialog(self).exec()

    def _show_download_models_dialog(self):
        from airunner.components.application.gui.dialogs.download_models_dialog import (
            show_download_models_dialog,
        )

        show_download_models_dialog(self)

    def _show_age_agreement(self):
        self._show_legal_document("Age Restriction Policy", "age")

    def _show_terms_of_service(self):
        self._show_legal_document("Terms of Service", "terms")

    def _show_privacy_policy(self):
        self._show_legal_document("Privacy Policy", "privacy")

    def _show_legal_document(self, title: str, document_type: str) -> None:
        from airunner.components.application.gui.dialogs.legal_document_dialog import (
            LegalDocumentDialog,
        )

        LegalDocumentDialog(self, title=title, document_type=document_type).exec()

    def _show_settings_window(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                prevent_always_on_top=False, exec=False
            )
            self.settings_window.show()
        elif not self.settings_window.isVisible():
            self.settings_window.show()
        self.settings_window.raise_()

    def _action_reset_settings(self):
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_settings()
            self.restart()
