from functools import partial

from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QSize, QObject
from PyQt6.QtWidgets import QPushButton, QGridLayout


class AIRunnerAPI(QObject):
    window = None
    tracked_buttons = {}

    @property
    def app(self):
        return self.window

    def __init__(self, *args, **kwargs):
        self.window = kwargs.pop("window")
        super().__init__(*args, **kwargs)

    def add_toolbar_button(
        self,
        **kwargs
    ):
        return self.add_button(
            section="toolbar",
            maximum_size=(40, 40),
            icon_size=(24, 24),
            flat=True,
            column=0,
            **kwargs
        )

    def add_button(
        self,
        section: str,
        icon_path=None,
        tooltip=None,
        text=None,
        callback=None,
        flat=True,
        minimum_size=None,
        maximum_size=None,
        icon_size=None,
        checkable=False,
        checked=False,
        row=None,
        column=None,
        **kwargs
    ):
        button = QPushButton()

        if tooltip:
            button.setToolTip(tooltip)

        if text:
            button.setText(text)

        if minimum_size:
            button.setMinimumSize(*minimum_size)

        if maximum_size:
            button.setMaximumSize(*maximum_size)

        button.setCheckable(checkable)
        if checkable:
            button.setChecked(checked)

        button.setFlat(flat)
        button.clicked.connect(partial(self.handle_click, button, callback))
        self.set_icon(button, icon_path, icon_size)

        self.add_widget_to_section(section, button, row, column)

        index = id(button)
        self.tracked_buttons[index] = {
            "button": button,
            "kwargs": kwargs,
            "icon_path": icon_path,
            "icon_size": icon_size
        }

        return index, button

    def add_widget_to_section(self, section, widget, row=None, column=None):
        if section == "toolbar":
            # add widget to front of toolbar
            if row is not None and column is not None and self.window.toolbar_widget.side_toolbar_container.layout() is QGridLayout:
                self.window.toolbar_widget.side_toolbar_container.layout().addWidget(widget, row, column)
            else:
                self.window.toolbar_widget.side_toolbar_container.layout().addWidget(widget)

    def handle_click(self, button, callback=None):
        if callback:
            callback()
        index = id(button)
        self.window.button_clicked_signal.emit(self.tracked_buttons[index]["kwargs"])

    def remove_button(self, button):
        self.tracked_buttons.remove(button)
        button.deleteLater()

    def update_icons(self):
        for button_id, data in self.tracked_buttons.items():
            icon_path = data["icon_path"]
            button = self.tracked_buttons[button_id]["button"]
            icon_size = data["icon_size"]
            self.set_icon(button, icon_path, icon_size)

    def set_icon(self, button, icon_path, icon_size):
        if icon_path:
            theme = "dark" if self.window.is_dark else "light"
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_path[theme]),
                           QtGui.QIcon.Mode.Normal,
                           QtGui.QIcon.State.Off)
            button.setIcon(icon)
            if icon_size:
                button.setIconSize(QSize(*icon_size))
