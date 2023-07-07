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
        "settings_button": "settings"
    }

    def set_stylesheet(self):
        super().set_stylesheet()
        self.setStyleSheet("""
            QFrame {
                background-color: #121212;
                border-radius: 0px;
            }
        """)

    def initialize(self):
        self.eraser_button.clicked.connect(lambda: self.app.set_tool("eraser"))
        self.brush_button.clicked.connect(lambda: self.app.set_tool("brush"))
        self.active_grid_area_button.clicked.connect(lambda: self.app.set_tool("active_grid_area"))
        # self.move_button.clicked.connect(lambda: self.app.set_tool("move"))
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

        self.move_button.deleteLater()

    def set_tool(self, tool):
        # uncheck all buttons that are not this tool
        if tool != "brush":
            self.brush_button.setChecked(False)
        if tool != "eraser":
            self.eraser_button.setChecked(False)
        if tool != "active_grid_area":
            self.active_grid_area_button.setChecked(False)
        # if tool != "move":
        #     self.move_button.setChecked(False)
        # if tool != "select":
        #     self.select_button.setChecked(False)

    def toggle_nsfw_filter(self, val):
        self.app.settings_manager.settings.nsfw_filter.set(val)
        self.app.canvas.update()
        # change the tooltip
        self.nsfw_button.setToolTip("Click to enable NSFW filter" if not val else "Click to disable NSFW filter")
