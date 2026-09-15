"""Window lifecycle, tray, splash, and shutdown handlers for MainWindow."""

from __future__ import annotations

import sys
from typing import Dict

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMenu

from airunner.app_installer import AppInstaller
from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.window_presentation_controller import (
    WindowPresentationController,
)
from airunner.components.application.gui.windows.main.controllers.window_state_persistence_controller import (
    WindowStatePersistenceController,
)


class WindowStateController(
    WindowStatePersistenceController, WindowPresentationController
):
    """Own window lifecycle, tray, splash, theme, and shutdown behavior."""

    def restart(self):
        self.save_state()
        self.close()
        from PySide6.QtCore import QProcess

        QProcess.startDetached(sys.executable, sys.argv)

    def toggle_window_visibility(self):
        """Toggle window visibility and update the menu text."""
        toggle_visibility_action = getattr(self, "toggle_visibility_action", None)
        tray_icon = getattr(self, "tray_icon", None)
        tray_menu = getattr(self, "tray_menu", None)
        if self.isVisible():
            self.hide()
            if toggle_visibility_action is not None:
                toggle_visibility_action.setText("Show Window")
        else:
            self.showNormal()
            self.activateWindow()
            if toggle_visibility_action is not None:
                toggle_visibility_action.setText("Hide Window")
        if tray_icon is not None and tray_menu is not None:
            tray_icon.setContextMenu(tray_menu)

    def handle_single_click(self):
        """Handle single-click on the tray icon."""
        from PySide6.QtGui import QAction, QCursor

        menu = QMenu()
        show_hide_text = "Hide Window" if self.isVisible() else "Show Window"
        show_action = QAction(show_hide_text, self)
        show_action.triggered.connect(self.toggle_window_visibility)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        menu.exec(QCursor.pos())

    def handle_double_click(self):
        """Handle double-click on the tray icon."""
        self.toggle_window_visibility()

    @staticmethod
    def on_write_file_signal(data: Dict):
        args = data["args"]
        message = args[0] if len(args) == 1 else args[1]
        with open("output.txt", "w") as f:
            f.write(message)

    def on_theme_changed_signal(self, data: Dict):
        self.set_stylesheet(template=data.get("template"))

    def _disable_aiart_gui_elements(self):
        for attr in ("center_widget", "menuFilters", "menuStable_Diffusion", "menuArt"):
            widget = getattr(self.ui, attr, None)
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        for attr in (
            "actionBrowse_AI_Runner_Path",
            "actionBrowse_Images_Path_2",
            "actionCut",
            "actionCopy",
            "actionPaste",
            "actionPrompt_Browser",
        ):
            action = getattr(self.ui, attr, None)
            if action is not None:
                action.deleteLater()

    @staticmethod
    def show_setup_wizard():
        AppInstaller(close_on_cancel=False)

    def _complete_launcher_splash_handoff(self) -> None:
        """Dismiss the launcher splash after the first show event."""
        api = self.refresh_api_reference() or getattr(self, "api", None)
        app = QApplication.instance()
        splash = getattr(api, "splash", None)
        if not api or not splash or not isinstance(app, QApplication):
            return
        from airunner.app_mixins.ui_runtime_mixin import UIRuntimeMixin

        UIRuntimeMixin._dismiss_splash_screen(api, self, app)
        self.raise_()
        self.activateWindow()
        self.logger.debug("Dismissed launcher splash after showEvent")

    def _handoff_launcher_splash(self) -> None:
        """Queue splash dismissal after the first show event returns."""
        if self._launcher_splash_dismissed:
            return
        api = getattr(self, "api", None)
        if not api or not getattr(api, "splash", None):
            return
        self._launcher_splash_dismissed = True
        QTimer.singleShot(0, self._complete_launcher_splash_handoff)
        self.logger.debug("Queued launcher splash dismissal from showEvent")

    def showEvent(self, event):
        """Override to update the tray menu text when window is shown."""
        super().showEvent(event)
        self._handoff_launcher_splash()
        self._update_tray_menu_text("Hide Window")
        self._initialize_window()
        self._initialize_filter_actions()
        self.initialized = True
        self._set_keyboard_shortcuts()
        self._schedule_main_window_loaded_signal()
        self._schedule_first_run_dialogs()

    def _update_tray_menu_text(self, text: str) -> None:
        """Refresh the tray visibility action text."""
        action = getattr(self, "toggle_visibility_action", None)
        tray_icon = getattr(self, "tray_icon", None)
        tray_menu = getattr(self, "tray_menu", None)
        if action is not None:
            action.setText(text)
            if tray_icon is not None and tray_menu is not None:
                tray_icon.setContextMenu(tray_menu)

    def _schedule_first_run_dialogs(self) -> None:
        """Queue the privacy consent and donation dialogs on first show."""
        if hasattr(self, "_donation_dialog_shown"):
            return
        self._donation_dialog_shown = True
        QTimer.singleShot(300, self._show_privacy_consent_dialog)
        QTimer.singleShot(500, self._show_donation_dialog)

    def _show_privacy_consent_dialog(self):
        """Show the privacy consent dialog on first launch."""
        from airunner.components.application.gui.dialogs.privacy_consent_dialog import (
            PrivacyConsentDialog,
        )

        PrivacyConsentDialog.show_if_needed(self)

    def _show_donation_dialog(self):
        """Show the donation dialog if appropriate."""
        from airunner.components.application.gui.dialogs.donation_dialog import (
            DonationDialog,
        )

        DonationDialog.show_if_appropriate(self)
