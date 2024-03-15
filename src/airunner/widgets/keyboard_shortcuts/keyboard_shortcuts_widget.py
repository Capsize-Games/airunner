import os

from PySide6.QtCore import Qt
from PySide6 import QtCore
from PySide6.QtWidgets import QSpacerItem, QSizePolicy

from airunner.settings import DEFAULT_SHORTCUTS
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.keyboard_shortcuts.templates.keyboard_shortcut_widget_ui import Ui_keyboard_shortcut_widget
from airunner.widgets.keyboard_shortcuts.templates.keyboard_shortcuts_ui import Ui_keyboard_shortcuts


class KeyboardShortcutsWidget(BaseWidget):
    widget_class_ = Ui_keyboard_shortcuts

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shortcuts = DEFAULT_SHORTCUTS
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.initialize_ui()

    def initialize_ui(self):
        for key, value in self.shortcuts.items():
            widget = self.add_widget(key, value)
            self.shortcuts[key]["widget"] = widget
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def add_widget(self, key, value):
        widget = Ui_keyboard_shortcut_widget()
        widget.label.setText(key)
        widget.line_edit.setText(value["text"])
        widget.line_edit.mousePressEvent = lambda event: self.set_shortcut(key, widget.line_edit)
        widget.line_edit.keyPressEvent = lambda event: self.get_shortcut(key, widget.line_edit, event)
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        return widget

    def set_shortcut(self, key, line_edit):
        self.clear_shortcut_setting(key)
        line_edit.setText("Press any key to set shortcut (esc to cancel)")

    def get_shortcut(self, key, line_edit, event):
        if event.key() == Qt.Key.Key_Escape:
            line_edit.setText(self.shortcuts[key]["text"])
            return
        self.shortcuts[key]["text"] = self.get_key_text(event)
        line_edit.setText(self.shortcuts[key]["text"])
        self.shortcuts[key]["key"] = event.key()

        # iterate over modifiers and store them as a list of strings
        self.shortcuts[key]["modifiers"] = [mod.value for mod in event.modifiers()]
        self.save_shortcuts()

    def get_key_text(self, event):
        text = ""
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            text += "Ctrl+"
        if event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
            text += "Alt+"
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
            text += "Shift+"
        key = event.key()
        if key >= QtCore.Qt.Key.Key_F1 and key <= QtCore.Qt.Key.Key_F24:
            text += f"F{key - QtCore.Qt.Key.Key_F1 + 1}"
        elif key == QtCore.Qt.Key.Key_Escape:
            text += "Escape"
        elif key == QtCore.Qt.Key.Key_Return:
            text += "Return"
        elif key == QtCore.Qt.Key.Key_Enter:
            text += "Enter"
        else:
            text += event.text()
        return text

    def save_shortcuts(self):
        settings = self.settings
        settings["shortcut_key_settings"] = self.shortcuts
        self.settings = settings

    def clear_shortcut_setting(self, key=""):
        for k, v in self.shortcuts.items():
            if k != key:
                v["widget"].line_edit.setText(v["text"])
