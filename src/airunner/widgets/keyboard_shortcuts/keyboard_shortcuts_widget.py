from PySide6.QtCore import Qt
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QWidget

from airunner.data.models.settings_models import ShortcutKeys
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.keyboard_shortcuts.templates.keyboard_shortcut_widget_ui import Ui_keyboard_shortcut_widget
from airunner.widgets.keyboard_shortcuts.templates.keyboard_shortcuts_ui import Ui_keyboard_shortcuts


class KeyboardShortcutsWidget(BaseWidget):
    widget_class_ = Ui_keyboard_shortcuts

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.shortcut_key_widgets = [None for _i in range(len(self.shortcut_keys))]
        self.pressed_keys = set()

    def showEvent(self, event):
        super().showEvent(event)
        self.initialize_ui()

    def initialize_ui(self):
        for index, shortcut_key in enumerate(self.shortcut_keys):
            self.add_widget(index, shortcut_key)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def add_widget(self, index: int, shortcut_key: ShortcutKeys):
        widget = QWidget()
        ui = Ui_keyboard_shortcut_widget()
        ui.setupUi(widget)
        ui.label.setText(shortcut_key.display_name)
        ui.line_edit.setText(shortcut_key.text)
        ui.line_edit.mousePressEvent = lambda event: self.set_shortcut(index, ui.line_edit)
        ui.line_edit.keyReleaseEvent = lambda event: self.get_shortcut(shortcut_key, ui.line_edit, event, index)
        self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
        self.shortcut_key_widgets[index] = ui
        return widget

    def set_shortcut(self, key, line_edit):
        self.clear_shortcut_setting(key)
        line_edit.setText("Press any key to set shortcut (esc to cancel)")

    def get_shortcut(self, shortcut_key: ShortcutKeys, line_edit, event, index):
        if event.isAutoRepeat():
            return

        if event.type() == QtCore.QEvent.Type.KeyPress:
            self.pressed_keys.add(event.key())
        elif event.type() == QtCore.QEvent.Type.KeyRelease:
            self.pressed_keys.discard(event.key())

        # Check if all keys are released
        if not self.pressed_keys:
            if event.key() in [
                QtCore.Qt.Key.Key_Control,
                QtCore.Qt.Key.Key_Shift,
                QtCore.Qt.Key.Key_Alt,
                QtCore.Qt.Key.Key_Meta
            ]:
                return
            if event.key() == Qt.Key.Key_Escape:
                line_edit.setText(shortcut_key.text)
                return

            shortcut_key.text = self.get_key_text(event)
            shortcut_key.key = event.key()
            shortcut_key.modifiers = event.modifiers().value

            session = self.db_handler.get_db_session()
            session.add(shortcut_key)


            # clear existing key if it exists
            existing_keys = session.query(ShortcutKeys).filter(
                ShortcutKeys.text == shortcut_key.text,
                ShortcutKeys.id != shortcut_key.id
            ).all()
            for existing_key in existing_keys:
                existing_key.text = ""
                existing_key.key = 0
                existing_key.modifiers = 0
                session.add(existing_key)

            for i, widget in enumerate(self.shortcut_key_widgets):
                if i == index:
                    continue
                if widget.line_edit.text() == shortcut_key.text:
                    widget.line_edit.setText("")

            line_edit.setText(shortcut_key.text)
            session.commit()
            session.close()

            self.pressed_keys.clear()
            self.emit_signal(SignalCode.KEYBOARD_SHORTCUTS_UPDATED)

    def get_key_text(self, event):
        key_sequence = QtGui.QKeySequence(event.key() | event.modifiers().value)
        return key_sequence.toString(QtGui.QKeySequence.SequenceFormat.NativeText)

    def save_shortcuts(self):
        session = self.db_handler.get_db_session()
        for k, v in enumerate(self.shortcut_keys):
            # Ensure v.modifiers is a list
            if not isinstance(v.modifiers, list):
                v.modifiers = []
            session.query(ShortcutKeys).filter(ShortcutKeys.id == v.id).update({
                "text": v.text,
                "key": v.key,
                "modifiers": ",".join(v.modifiers)  # Convert list to comma-separated string
            })
        session.commit()
        session.close()

    def clear_shortcut_setting(self, key=""):
        for index, v in enumerate(self.shortcut_keys):
            if v.key != key:
                self.shortcut_key_widgets[index].line_edit.setText(v.text)
