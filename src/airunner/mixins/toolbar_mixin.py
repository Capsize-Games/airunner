import os
from PyQt6 import QtGui
from PyQt6.QtWidgets import QColorDialog
import qdarktheme
import webbrowser
from airunner.windows.about import AboutWindow
from airunner.windows.advanced_settings import AdvancedSettings
from airunner.windows.extensions import ExtensionsWindow
from airunner.windows.grid_settings import GridSettings
from airunner.windows.preferences import PreferencesWindow


class ToolbarMixin:
    def initialize(self):
        self.window.eraser_button.clicked.connect(lambda: self.set_tool("eraser"))
        self.window.brush_button.clicked.connect(lambda: self.set_tool("brush"))
        self.window.active_grid_area_button.clicked.connect(lambda: self.set_tool("active_grid_area"))
        self.window.move_button.clicked.connect(lambda: self.set_tool("move"))
        # self.window.select_button.clicked.connect(lambda: self.set_tool("select"))
        self.window.grid_button.clicked.connect(self.toggle_grid)
        self.window.nsfw_button.clicked.connect(self.toggle_nsfw_filter)
        self.window.focus_button.clicked.connect(self.focus_button_clicked)
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
        self.window.actionGrid.triggered.connect(self.show_grid_settings)
        self.window.actionPreferences.triggered.connect(self.show_preferences)
        self.window.actionAbout.triggered.connect(self.show_about)
        self.window.actionCanvas_color.triggered.connect(self.show_canvas_color)
        self.window.actionAdvanced.triggered.connect(self.show_advanced)
        self.window.actionBug_report.triggered.connect(lambda: webbrowser.open(
            "https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title="))
        self.window.actionReport_vulnerability.triggered.connect(
            lambda: webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new"))
        self.window.actionDiscord.triggered.connect(lambda: webbrowser.open("https://discord.gg/PUVDDCJ7gz"))
        self.window.actionExtensions.triggered.connect(self.show_extensions)
        self.window.actionInvert.triggered.connect(self.do_invert)

    def do_invert(self):
        self.canvas.invert_image()
        self.canvas.update()

    def show_extensions(self):
        self.extensions_window = ExtensionsWindow(self.settings_manager)

    def show_canvas_color(self):
        # show a color widget dialog and set the canvas color
        color = QColorDialog.getColor()
        if color.isValid():
            color = color.name()
            self.settings_manager.settings.canvas_color.set(color)
            self.canvas.set_canvas_color()

    def show_about(self):
        AboutWindow(self.settings_manager)

    def show_grid_settings(self):
        GridSettings(self.settings_manager)

    def show_preferences(self):
        PreferencesWindow(self.settings_manager, app=self)

    def show_advanced(self):
        AdvancedSettings(self.settings_manager)

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
