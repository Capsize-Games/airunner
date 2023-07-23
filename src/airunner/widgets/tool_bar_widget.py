from functools import partial

from airunner.widgets.base_widget import BaseWidget


class ToolBarWidget(BaseWidget):
    name = "toolbar"
    icons = {
        # "move_button": "013-move-selector",
        "active_grid_area_button": "038-drag",
        "eraser_button": "014-eraser",
        "brush_button": "011-pencil",
        "grid_button": "032-pixels",
        "nsfw_button": "039-18",
        "focus_button": "037-focus",
        "settings_button": "settings",
        # "move_button": "013-move-selector",
        # "select_button": "040-select",
        # "crop_button": "001-crop",
        # "zoom_button": "015-zoom-in",
    }
    tool_buttons = [
        "eraser",
        "brush",
        "active_grid_area",
        # "move",
        # "select",
        # "crop",
        # "zoom"
    ]

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet(self.app.css("toolbar_widget"))

    def initialize(self):
        for button_name in self.tool_buttons:
            button = getattr(self, f"{button_name}_button")
            button.clicked.connect(partial(self.set_tool, button_name))

        self.grid_button.clicked.connect(self.app.toggle_grid)
        self.nsfw_button.clicked.connect(self.toggle_nsfw_filter)
        self.focus_button.clicked.connect(self.app.focus_button_clicked)
        self.grid_button.setChecked(self.settings_manager.settings.show_grid.get() == True)
        self.nsfw_button.setChecked(self.settings_manager.settings.nsfw_filter.get() == True)
        self.settings_button.clicked.connect(self.app.show_settings)
        if self.canvas.active_grid_area_selected:
            self.active_grid_area_button.setChecked(True)
        if self.canvas.eraser_selected:
            self.eraser_button.setChecked(True)
        if self.canvas.brush_selected:
            self.brush_button.setChecked(True)
        # if self.canvas.move_selected:
        #     self.move_button.setChecked(True)
        if self.settings_manager.settings.snap_to_grid.get():
            self.grid_button.setChecked(True)
        self.toggle_nsfw_filter(self.app.settings_manager.settings.nsfw_filter.get())

        self.crop_button.deleteLater()
        self.move_button.deleteLater()
        self.select_button.deleteLater()
        self.zoom_button.deleteLater()

    def set_tool(self, tool):
        # uncheck all buttons that are not currently selected
        for button_name in self.tool_buttons:
            button = getattr(self, f"{button_name}_button")
            if tool != button_name:
                button.setChecked(False)
            elif tool == button_name and not button.isChecked():
                tool = None
        self.app.settings.current_tool.set(tool)
        self.app.canvas.update_cursor()

    def toggle_nsfw_filter(self, val):
        self.app.settings_manager.settings.nsfw_filter.set(val)
        self.app.canvas.update()
        # change the tooltip
        self.nsfw_button.setToolTip("Click to enable NSFW filter" if not val else "Click to disable NSFW filter")
