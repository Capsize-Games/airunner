"""Window presentation and content helpers for MainWindow."""

from __future__ import annotations

import os
from functools import partial

from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner_common.settings import AIRUNNER_ART_ENABLED


class WindowPresentationController(MainWindowBase):
    """Own window sizing, title/icon, shortcuts, filters, and content."""

    def move_to_second_screen(self):
        screens = QGuiApplication.screens()
        if len(screens) > 1:
            self._move_to_screen_geometry(screens[1].availableGeometry())

    def _move_to_screen_geometry(self, geometry) -> None:
        """Move/resize the window to fill one screen geometry."""
        self.move(geometry.topLeft())
        self.resize(geometry.size())
        self.setMinimumSize(512, 512)
        self.setMaximumSize(
            max(geometry.width(), self.minimumWidth()),
            max(geometry.height(), self.minimumHeight()),
        )

    def on_keyboard_shortcuts_updated(self):
        self._set_keyboard_shortcuts()

    def _set_keyboard_shortcuts(self):
        quit_key = self.resource_store.first(
            "ShortcutKeys", filters={"display_name": "Quit"}
        )
        if quit_key is not None:
            key_sequence = QKeySequence(quit_key.key | quit_key.modifiers)
            self.ui.actionQuit.setShortcut(key_sequence)
            self.ui.actionQuit.setToolTip(
                f"{quit_key.display_name} ({quit_key.text})"
            )

    def _initialize_filter_actions(self):
        self.ui.menuFilters.clear()
        image_filters = self.resource_store.query("ImageFilter")
        try:
            for image_filter in image_filters:
                action = self.ui.menuFilters.addAction(image_filter.display_name)
                action.triggered.connect(
                    partial(self.display_filter_window, image_filter)
                )
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.warning(f"Error setting SD status text: {e}")

    @staticmethod
    def display_filter_window(image_filter):
        from airunner.components.art.gui.windows.filter_window.filter_window import (
            FilterWindow,
        )

        FilterWindow(image_filter.id)

    def _initialize_window(self):
        if getattr(self, "_state_restored", False):
            self.logger.debug("Skipping window initialization - state already restored")
            self.set_window_icon()
            self.set_window_title()
            return
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.logger.warning(
                "Could not get primary screen. Falling back to default size."
            )
            self.resize(1024, 768)
            self.setMinimumSize(512, 512)
            self.setMaximumSize(1024, 768)
        else:
            self._move_to_screen_geometry(screen.availableGeometry())
        self.set_window_icon()
        self.set_window_title()

    def set_window_icon(self):
        """Set the application window icon from the path settings."""
        self.setWindowIcon(
            QIcon(os.path.join(self.path_settings.base_path, "images/icon.png"))
        )

    def center(self):
        available_geometry = QGuiApplication.primaryScreen().availableGeometry()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(available_geometry.center())
        self.move(frame_geometry.topLeft())

    def set_window_title(self):
        self.setWindowTitle(self._window_title)

    def handle_unknown(self, message):
        from airunner.utils.application.log_hygiene import summarize_mapping_keys

        self.logger.error(
            "Unknown message code payload (%s)",
            summarize_mapping_keys(message, label="message"),
        )

    def clear_all_prompts(self):
        self.prompt = ""
        self.negative_prompt = ""
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot clear prompts."
            )
            return
        self.api.clear_prompts()

    def new_batch(self, index, image, data):
        new_batch = getattr(self.generator_tab_widget, "new_batch", None)
        if callable(new_batch):
            new_batch(index, image, data)

    def on_toggle_tool_signal(self, data):
        toggle_tool = getattr(self, "toggle_tool", None)
        if callable(toggle_tool):
            toggle_tool(data["tool"], data["active"])

    def on_retranslate_ui_signal(self):
        self.ui.retranslateUi(self)

    def show_update_message(self):
        if not self.api:
            self.logger.warning(
                "MainWindow: self.api is missing. Cannot display update message."
            )
            return
        self.api.application_status(f"New version available: {self.latest_version}")

    def show_update_popup(self):
        from airunner.components.update.gui.windows.update.update_window import (
            UpdateWindow,
        )

        self.update_popup = UpdateWindow()
