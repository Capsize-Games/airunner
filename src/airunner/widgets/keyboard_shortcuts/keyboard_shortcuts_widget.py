import os

from PySide6.QtCore import Qt
from PySide6 import QtCore
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QWidget

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

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_ui()

    def initialize_ui(self):
        for key, value in self.shortcuts.items():
            self.add_widget(key, value)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def add_widget(self, key, value):
        widget = QWidget()
        ui = Ui_keyboard_shortcut_widget()
        ui.setupUi(widget)
        ui.label.setText(key)
        ui.line_edit.setText(value["text"])
        ui.line_edit.mousePressEvent = lambda event: self.set_shortcut(key, ui.line_edit)
        ui.line_edit.keyPressEvent = lambda event: self.get_shortcut(key, ui.line_edit, event)
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        self.shortcuts[key]["widget"] = ui
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

        # Check for each modifier and store them as a list of strings
        modifiers = []
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Control")
        if event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & QtCore.Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Meta")

        self.shortcuts[key]["modifiers"] = modifiers
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
        print("TODO: save_shortcuts")

    def clear_shortcut_setting(self, key=""):
        for k, v in self.shortcuts.items():
            if k != key:
                v["widget"].line_edit.setText(v["text"])


