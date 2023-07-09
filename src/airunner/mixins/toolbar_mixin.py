from PyQt6.QtWidgets import QColorDialog
import webbrowser
from airunner.windows.about import AboutWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.settings import SettingsWindow


class ToolbarMixin:
    def initialize(self):
        self.toolbar_widget.initialize()
        # self.select_button.clicked.connect(lambda: self.set_tool("select"))
        self.actionAbout.triggered.connect(self.show_about)
        self.actionModel_Merger.triggered.connect(self.show_model_merger)
        self.actionBug_report.triggered.connect(lambda: webbrowser.open(
            "https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title="))
        self.actionReport_vulnerability.triggered.connect(
            lambda: webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new"))
        self.actionDiscord.triggered.connect(lambda: webbrowser.open("https://discord.gg/PUVDDCJ7gz"))
        self.actionInvert.triggered.connect(self.do_invert)
        self.actionFilm.triggered.connect(self.do_film)
        self.actionSettings.triggered.connect(self.show_settings)
        # self.initialize_toolbar_extensions()  # TODO: Extensions

    """
    TODO: Extensions
    def initialize_toolbar_extensions(self):
        self.actionExtensions.triggered.connect(self.show_extensions)
    
    def show_extensions(self):
        self.extensions_window = ExtensionsWindow(self.settings_manager)
    """

    def show_settings(self):
        SettingsWindow(self.settings_manager, app=self)

    def do_invert(self):
        self.history.add_event({
            "event": "apply_filter",
            "layer_index": self.canvas.current_layer_index,
            "images": self.canvas.image_data_copy(self.canvas.current_layer_index),
        })
        self.canvas.invert_image()
        self.canvas.update()

    def do_film(self):
        self.canvas.film_filter()

    def show_canvas_color(self):
        # show a color widget dialog and set the canvas color
        color = QColorDialog.getColor()
        if color.isValid():
            color = color.name()
            self.settings_manager.settings.canvas_color.set(color)
            self.canvas.set_canvas_color()

    def show_model_merger(self):
        ModelMerger(self.settings_manager, app=self)

    def show_about(self):
        AboutWindow(self.settings_manager, app=self)

    def set_tool(self, tool):
        self.toolbar_widget.set_tool(tool)
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

    def focus_button_clicked(self):
        self.canvas.recenter()

    def toggle_darkmode(self):
        self.set_stylesheet()
