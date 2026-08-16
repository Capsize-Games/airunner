"""Startup and shutdown sequence for MainWindow."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.toggle_controller import (
    ToggleController,
)
from airunner.enums import SignalCode


class StartupController(ToggleController):
    """Own window construction, shutdown, and status-bar initialization."""

    def initialize_ui(self):
        total_started_at = time.perf_counter()
        self.logger.debug("Loading UI")
        self._setup_ui()
        self._prepare_startup_state()
        self._apply_styles_and_icons()
        self._restore_window_state()
        self._finish_ui_initialization()
        self.logger.info(
            "MainWindow initialize_ui completed in %.2fs",
            time.perf_counter() - total_started_at,
        )

    def _setup_ui(self) -> None:
        """Build the UI and lazy panel hosts."""
        started_at = time.perf_counter()
        self.ui.setupUi(self)
        self._create_left_sidebar_buttons()
        self._ensure_left_panel_host()
        self._phase("setup_ui", started_at)

    def _prepare_startup_state(self) -> None:
        """Build menus, icons, and restore the persisted tab state."""
        started_at = time.perf_counter()
        self._add_legal_menu_items()
        self._add_download_models_menu_item()
        self.icon_manager = self._build_icon_manager()
        if not self._art_enabled():
            self._disable_aiart_gui_elements()
        self._restore_startup_tab_state()
        self._phase("startup_state_prep", started_at)

    def _apply_styles_and_icons(self) -> None:
        """Apply the theme stylesheet and icon set."""
        started_at = time.perf_counter()
        self.set_stylesheet()
        self.icon_manager.set_icons()
        self._phase("styles_and_icons", started_at)

    def _restore_window_state(self) -> None:
        """Restore persisted window geometry and splitter state."""
        started_at = time.perf_counter()
        self.restore_state()
        self._phase("restore_state", started_at)

    def _finish_ui_initialization(self) -> None:
        """Apply splitters, status, and toggle state to finish startup."""
        started_at = time.perf_counter()
        self._apply_default_splitter_config()
        self._queue_deferred_panel_restores()
        self.status_widget = self._build_status_widget()
        self.statusBar().addPermanentWidget(self.status_widget)
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot clear status message."
            )
            return
        self.api.clear_status_message()
        self._phase("splitter_and_status", started_at)
        self._finish_widget_initialization()

    def _finish_widget_initialization(self) -> None:
        """Wire splitters/shortcuts and sync button states."""
        started_at = time.perf_counter()
        self.initialize_widget_elements()
        self._phase("initialize_widget_elements", started_at)
        self.last_tray_click_time = 0
        self.settings_window = None
        self.hide_center_tab_header()
        self._connect_splitter_moved()
        self.set_chat_button_checked()
        self._sync_left_panel_button_states()
        self._sync_sidebar_button_states()
        self._install_new_document_shortcut()

    def _phase(self, name: str, started_at: float) -> None:
        """Log one startup phase completion."""
        self.logger.info(
            "MainWindow startup phase %s completed in %.2fs",
            name,
            time.perf_counter() - started_at,
        )

    def _build_icon_manager(self):
        """Create the window icon manager."""
        from airunner.components.icons.managers.icon_manager import IconManager

        return IconManager(self.icons, self.ui)

    def _art_enabled(self) -> bool:
        """Return whether the art subsystem is enabled."""
        from airunner_common.settings import AIRUNNER_ART_ENABLED

        return AIRUNNER_ART_ENABLED

    def _restore_startup_tab_state(self) -> None:
        """Restore the persisted left/sidebar tab selection."""
        left_panel_page_index = self._saved_left_panel_tab_index()
        self.ui.left_panel_tab.blockSignals(True)
        self.ui.left_panel_tab.setCurrentIndex(left_panel_page_index)
        self.ui.left_panel_tab.blockSignals(False)

        sidebar_page_index = self._saved_sidebar_tab_index()
        self.ui.sidebar_tab.tabBar().hide()
        self.ui.sidebar_tab.blockSignals(True)
        self.ui.sidebar_tab.setCurrentIndex(sidebar_page_index)
        self.ui.sidebar_tab.blockSignals(False)
        self.ui.sidebar_tab.currentChanged.connect(
            self.on_sidebar_tab_current_changed
        )

    def _apply_default_splitter_config(self) -> None:
        """Apply the canvas-maximizing default splitter configuration."""
        from airunner.utils.widgets import load_splitter_settings

        default_splitter_config = {
            "main_window_splitter": {
                "index_to_maximize": self._center_splitter_index,
                "min_other_size": 50,
            },
            "center_splitter": {
                "index_to_maximize": self._canvas_panel_index,
                "min_other_size": 0,
            },
        }
        load_splitter_settings(
            self.ui,
            ["main_window_splitter", "center_splitter"],
            default_maximize_config=default_splitter_config,
            namespace="MainWindow",
        )

    def _queue_deferred_panel_restores(self) -> None:
        """Queue panel restores that must happen after the window is shown."""
        if self._sidebar_is_visible():
            self._restore_sidebar_page_after_startup = self._saved_sidebar_tab_index()
        if self._prompt_panel_is_visible():
            self._ensure_art_prompt_loaded()
        if self._left_panel_is_visible():
            self._restore_left_panel_page_after_startup = (
                self._saved_left_panel_tab_index()
            )

    def _build_status_widget(self):
        from airunner.components.application.gui.widgets.status.status_widget import (
            StatusWidget,
        )

        return StatusWidget()

    def _connect_splitter_moved(self) -> None:
        """Wire splitter move events to the layout refresh handler."""
        self.ui.main_window_splitter.splitterMoved.connect(
            self.on_splitter_changed_sizes
        )
        self.ui.center_splitter.splitterMoved.connect(self.on_splitter_changed_sizes)

    def _install_new_document_shortcut(self) -> None:
        """Install the Ctrl+N shortcut for the always-visible canvas."""
        from PySide6.QtGui import QAction, QKeySequence

        try:
            action_new_shortcut = QAction(self)
            action_new_shortcut.setShortcut(QKeySequence("Ctrl+N"))
            action_new_shortcut.triggered.connect(self._on_ctrl_n_pressed)
            self.addAction(action_new_shortcut)
            self._action_new_shortcut = action_new_shortcut
        except Exception:
            try:
                self.logger.debug("Could not create Ctrl+N QAction shortcut")
            except Exception:
                pass

    def initialize_widget_elements(self):
        self._set_tts_stt_button_states()
        if hasattr(self.ui, "actionSafety_Checker"):
            self.ui.actionSafety_Checker.blockSignals(True)
            self.ui.actionSafety_Checker.setChecked(
                self.application_settings.nsfw_filter
            )
            self.ui.actionSafety_Checker.blockSignals(False)
            self.set_nsfw_filter_tooltip()
        self.initialized = True

    def _set_tts_stt_button_states(self) -> None:
        """Set the TTS/STT toggle states from application settings."""
        for attr, enabled in (
            ("text_to_speech_button", self.application_settings.tts_enabled),
            ("speech_to_text_button", self.application_settings.stt_enabled),
        ):
            element = getattr(self.ui, attr, None)
            if element is None:
                continue
            element.blockSignals(True)
            element.setChecked(enabled or False)
            element.blockSignals(False)

    def closeEvent(self, event):
        event.ignore()
        self.handle_close()

    def handle_close(self):
        """Override close to minimize to tray instead of exiting."""
        self.quit()

    def quit(self):
        if self.quitting:
            return
        self.logger.debug("Quitting")
        if self._daemon_status_timer.isActive():
            self._daemon_status_timer.stop()
        self.save_state()
        self.quitting = True
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot quit application."
            )
            return
        self.emit_signal(SignalCode.SAVE_STATE, {})
        self.emit_signal(SignalCode.QUIT_APPLICATION, {})

    def handle_quit_application_signal(self):
        self.hide()
        QTimer.singleShot(0, QApplication.quit)

    def on_reset_paths_signal(self):
        self.reset_path_settings()

    def on_toggle_fullscreen_signal(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def hide_center_tab_header(self):
        """Hide the right-sidebar tab bar so it behaves like VS Code."""
        tab_widget = getattr(self.ui, "sidebar_tab", None)
        if tab_widget is not None:
            tab_widget.tabBar().hide()
