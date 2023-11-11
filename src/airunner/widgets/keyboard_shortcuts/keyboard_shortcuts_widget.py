import os

from PyQt6 import uic, QtCore

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.keyboard_shortcuts.templates.keyboard_shortcuts_ui import Ui_keyboard_shortcuts


class KeyboardShortcutsWidget(BaseWidget):
    widget_class_ = Ui_keyboard_shortcuts

    shortcuts = {
        "Generate": {
            "display_name": "F5",
            "key_value": QtCore.Qt.Key.Key_F5,
            "modifiers": QtCore.Qt.KeyboardModifier.NoModifier,
            "widget": None,
        },
        "Quit": {
            "display_name": "Ctrl+Q",
            "key_value": QtCore.Qt.Key.Key_Q,
            "modifiers": QtCore.Qt.KeyboardModifier.ControlModifier,
            "widget": None,
        },
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.initialize_ui()

    def initialize_ui(self):
        for key, value in self.shortcuts.items():
            widget = self.add_widget(key, value)
            self.shortcuts[key]["widget"] = widget

    def add_widget(self, key, value):
        widget = uic.loadUi(os.path.join(f"widgets/keyboard_shortcuts/templates/keyboard_shortcut_widget.ui"))
        widget.label.setText(key)
        widget.line_edit.setText(value["display_name"])
        widget.line_edit.mousePressEvent = lambda event: self.set_shortcut(key, widget.line_edit)
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        return widget

    def set_shortcut(self, key, line_edit):
        self.clear_shortcut_setting(key)
        line_edit.setText("Press any key to set shortcut")

    def clear_shortcut_setting(self, key=""):
        for k, v in self.shortcuts.items():
            if k != key:
                v["widget"].line_edit.setText(v["display_name"])
