import os
from PyQt6 import QtGui
from PyQt6.QtWidgets import QColorDialog
import qdarktheme


class ToolbarMixin:
    window = None
    settings_manager = None
    canvas = None
    history = None

    def initialize(self):
        self.window.eraser_button.clicked.connect(lambda: self.set_tool("eraser"))
        self.window.brush_button.clicked.connect(lambda: self.set_tool("brush"))
        self.window.active_grid_area_button.clicked.connect(lambda: self.set_tool("active_grid_area"))
        self.window.move_button.clicked.connect(lambda: self.set_tool("move"))
        # self.window.select_button.clicked.connect(lambda: self.set_tool("select"))
        self.window.primary_color_button.clicked.connect(self.set_primary_color)
        self.window.secondary_color_button.clicked.connect(self.set_secondary_color)
        self.window.grid_button.clicked.connect(self.toggle_grid)
        self.window.nsfw_button.clicked.connect(self.toggle_nsfw_filter)
        self.window.focus_button.clicked.connect(self.focus_button_clicked)
        # self.window.wordballoon_button.clicked.connect(self.word_balloon_button_clicked)
        self.set_button_colors()
        self.window.grid_button.setChecked(self.settings_manager.settings.show_grid.get() == True)
        self.window.nsfw_button.setChecked(self.settings_manager.settings.nsfw_filter.get() == True)
        if self.canvas.active_grid_area_selected:
            self.window.active_grid_area_button.setChecked(True)
        if self.canvas.eraser_selected:
            self.window.eraser_button.setChecked(True)
        if self.canvas.brush_selected:
            self.window.brush_button.setChecked(True)
        if self.canvas.move_selected:
            self.window.move_button.setChecked(True)
        if self.settings_manager.settings.snap_to_grid.get():
            self.window.grid_button.setChecked(True)
        if self.settings_manager.settings.nsfw_filter.get():
            self.window.nsfw_button.setChecked(True)
        self.window.darkmode_button.clicked.connect(self.toggle_darkmode)

        # remove word balloon button until next release
        self.window.wordballoon_button.setParent(None)

    def set_tool(self, tool):
        # uncheck all buttons that are not this tool
        if tool != "brush":
            self.window.brush_button.setChecked(False)
        if tool != "eraser":
            self.window.eraser_button.setChecked(False)
        if tool != "active_grid_area":
            self.window.active_grid_area_button.setChecked(False)
        if tool != "move":
            self.window.move_button.setChecked(False)
        # if tool != "select":
        #     self.window.select_button.setChecked(False)

        if self.settings_manager.settings.current_tool.get() != tool:
            self.settings_manager.settings.current_tool.set(tool)
        else:
            self.settings_manager.settings.current_tool.set(None)

        self.canvas.update_cursor()

    def set_primary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.primary_color.set(color.name())
            self.set_button_colors()

    def set_button_colors(self):
        # set self.window.primaryColorButton color
        self.window.primary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.primary_color.get()};"
        )
        self.window.secondary_color_button.setStyleSheet(
            f"background-color: {self.settings_manager.settings.secondary_color.get()};"
        )

    def set_secondary_color(self):
        # display a color picker
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings_manager.settings.secondary_color.set(color.name())
            self.set_button_colors()

    def toggle_grid(self, event):
        self.settings_manager.settings.show_grid.set(
            event
        )
        self.canvas.update()

    def toggle_nsfw_filter(self, val):
        self.settings_manager.settings.nsfw_filter.set(val)
        self.canvas.update()

    def focus_button_clicked(self):
        self.canvas.recenter()

    # def word_balloon_button_clicked(self):
    #     """
    #     Create and add a word balloon to the canvas.
    #     :return:
    #     """
    #     # create a word balloon
    #     word_balloon = Balloon()
    #     word_balloon.setGeometry(100, 100, 200, 100)
    #     word_balloon.set_tail_pos(QPointF(50, 100))
    #     # add the widget to the canvas
    #     self.history.add_event({
    #         "event": "add_widget",
    #         "layer_index": self.canvas.current_layer_index,
    #         "widgets": self.canvas.current_layer.widgets.copy(),
    #     })
    #     self.canvas.current_layer.widgets.append(word_balloon)
    #     self.show_layers()
    #     self.canvas.update()

    def toggle_darkmode(self):
        self.settings_manager.settings.dark_mode_enabled.set(not self.settings_manager.settings.dark_mode_enabled.get())
        self.set_stylesheet()

    def set_stylesheet(self):
        HERE = os.path.dirname(os.path.abspath(__file__))
        icons = {
            "darkmode_button": "weather-night",
            "move_button": "move",
            "active_grid_area_button": "stop",
            "eraser_button": "eraser",
            "brush_button": "pen",
            "grid_button": "grid",
            "nsfw_button": "underwear",
            "focus_button": "camera-focus",
            "undo_button": "undo",
            "redo_button": "redo",
            "new_layer": "file-add",
            "layer_up_button": "arrow-up",
            "layer_down_button": "arrow-down",
            "delete_layer_button": "delete"
        }
        if self.settings_manager.settings.dark_mode_enabled.get():
            qdarktheme.setup_theme("dark")
            icons["darkmode_button"] = "weather-sunny"
            for button, icon in icons.items():
                if icon != "weather-sunny":
                    icon = icon + "-light"
                getattr(self.window, button).setIcon(QtGui.QIcon(os.path.join(HERE, f"../src/icons/{icon}.png")))
        else:
            for button, icon in icons.items():
                getattr(self.window, button).setIcon(QtGui.QIcon(os.path.join(HERE, f"../src/icons/{icon}.png")))
            try:
                qdarktheme.setup_theme("light")
            except PermissionError:
                pass
