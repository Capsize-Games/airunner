"""Keyboard shortcuts and prompt helpers for MainWindow."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Slot

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.enums import SignalCode


class InputController(MainWindowBase):
    """Own keyboard shortcuts and prompt-persistence behavior."""

    def _set_tab_index(self, tab_widget):
        """Legacy compatibility stub for removed center-tab navigation."""
        del tab_widget

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        try:
            event_modifiers = self._modifier_value(event.modifiers())
            for shortcut in self.shortcut_keys:
                shortcut_modifiers = int(getattr(shortcut, "modifiers", 0) or 0)
                if shortcut.key != event.key():
                    continue
                if shortcut_modifiers != event_modifiers:
                    continue
                for signal in SignalCode:
                    if signal.value == shortcut.signal:
                        self.emit_signal(signal)
                        return
        except Exception:
            self.logger.exception("Failed to process keyboard shortcut")

    def key_text(self, key_name):
        for shortcutkey in self.shortcut_keys:
            if shortcutkey.name == key_name:
                return shortcutkey.text
        return ""

    @Slot()
    def _on_ctrl_n_pressed(self):
        """Create a new art document for the always-visible canvas."""
        if not self.api or not hasattr(self.api, "art"):
            return
        canvas = getattr(self.api.art, "canvas", None)
        if canvas is None:
            self._ensure_canvas_loaded()
            canvas = getattr(self.api.art, "canvas", None)
        if canvas is not None:
            canvas.new_document()

    def on_save_stablediffusion_prompt_signal(self, data: Dict):
        self.create_saved_prompt(
            {
                "prompt": data["prompt"],
                "negative_prompt": data["negative_prompt"],
                "secondary_prompt": data["secondary_prompt"],
                "secondary_negative_prompt": data["secondary_negative_prompt"],
            }
        )

    def create_saved_prompt(self, data: Dict):
        """Persist a Stable Diffusion prompt in the SavedPrompt table."""
        self.resource_store.create(
            "SavedPrompt",
            {
                "prompt": data.get("prompt"),
                "negative_prompt": data.get("negative_prompt"),
                "secondary_prompt": data.get("secondary_prompt"),
                "secondary_negative_prompt": data.get("secondary_negative_prompt"),
            },
        )
        self.logger.info("Saved Stable Diffusion prompt")

    def set_path_settings(self, key, val):
        self.update_path_settings(**{key: val})

    def show_settings_path(self, name, default_path=None):
        # Browser navigation was removed with the old agent system.
        del name, default_path
