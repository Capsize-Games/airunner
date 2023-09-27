import os

from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.toolbar.toolbar import Ui_toolbar


class ToolBarWidget(BaseWidget):
    widget_class_ = Ui_toolbar
    icons = {
        "active_grid_area_button": "038-drag",
        "eraser_button": "014-eraser",
        "brush_button": "011-pencil",
        "grid_button": "032-pixels",
        "nsfw_button": "039-18",
        "focus_button": "037-focus",
        "settings_button": "settings",
    }
    tool_buttons = [
        "eraser",
        "brush",
        "active_grid_area",
    ]

    def icon_path(self, name):
        if name in self.icons:
            icon = self.icons[name]
            return {
                "light": os.path.join("src/icons", f"{icon}.png"),
                "dark": os.path.join("src/icons", f"{icon}-light.png")
            }
        return None

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet(self.app.css("toolbar_widget"))

    def initialize(self):
        # add a stretch to the bottom of side_toolbar_container which has a QVBoxLayout
        _index, self.active_grid_area_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("active_grid_area_button"),
            tooltip="Toggle Active Grid Area",
            checkable=True,
            checked=self.canvas.active_grid_area_selected,
            action="toggle_tool",
            tool="active_grid_area",
            row=0
        )
        _index, self.brush_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("brush_button"),
            tooltip="Toggle Pen Tool",
            checkable=True,
            checked=self.canvas.brush_selected,
            action="toggle_tool",
            tool="brush",
            row=1,
        )
        _index, self.eraser_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("eraser_button"),
            tooltip="Toggle Eraser Tool",
            checkable=True,
            checked=self.canvas.eraser_selected,
            action="toggle_tool",
            tool="eraser",
            row=2,
        )
        _index, self.focus_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("focus_button"),
            tooltip="Focus the canvas",
            tool="focus_button",
            row=3,
            callback=self.app.focus_button_clicked
        )
        _index, self.grid_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("grid_button"),
            checkable=True,
            checked=self.app.settings_manager.grid_settings.show_grid == True,
            tooltip="Toggle grid",
            tool="grid_button",
            row=4,
            callback=self.app.toggle_grid
        )
        _index, self.nsfw_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("nsfw_button"),
            checkable=True,
            checked=self.app.document.settings.nsfw_filter,
            tooltip="Toggle NSFW Filter",
            tool="nsfw_button",
            row=5,
            callback=self.toggle_nsfw_filter
        )
        _index, self.settings_button = self.app.api.add_toolbar_button(
            icon_path=self.icon_path("settings_button"),
            tooltip="Settings",
            tool="settings_button",
            row=6,
            callback=self.app.show_settings
        )
        self.set_nsfw_filter_tooltip()
        self.side_toolbar_container.layout().addStretch(1)

    def toggle_nsfw_filter(self):
        self.settings_manager.set_value("nsfw_filter", not self.app.settings_manager.nsfw_filter)
        self.app.canvas.update()
        self.set_nsfw_filter_tooltip()
        self.nsfw_button.setChecked(self.app.document.settings.nsfw_filter)

    def set_nsfw_filter_tooltip(self):
        nsfw_filter = self.app.settings_manager.nsfw_filter
        self.nsfw_button.setToolTip("Click to enable NSFW filter" if not nsfw_filter else "Click to disable NSFW filter")
