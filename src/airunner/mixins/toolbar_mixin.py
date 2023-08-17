from functools import partial

from PyQt6.QtWidgets import QColorDialog
import webbrowser
from airunner.windows.about import AboutWindow
from airunner.windows.model_merger import ModelMerger
from airunner.windows.settings import SettingsWindow


class ToolbarMixin:
    def initialize(self):
        self.toolbar_widget.initialize()
        self.actionAbout.triggered.connect(self.show_about)
        self.actionModel_Merger.triggered.connect(self.show_model_merger)
        self.actionHuggingface_Cache_manager.triggered.connect(self.show_hf_cache_manager)
        self.actionBug_report.triggered.connect(lambda: webbrowser.open(
            "https://github.com/Capsize-Games/airunner/issues/new?assignees=&labels=&template=bug_report.md&title="))
        self.actionReport_vulnerability.triggered.connect(
            lambda: webbrowser.open("https://github.com/Capsize-Games/airunner/security/advisories/new"))
        self.actionDiscord.triggered.connect(lambda: webbrowser.open("https://discord.gg/PUVDDCJ7gz"))
        self.actionInvert.triggered.connect(self.do_invert)
        self.actionFilm.triggered.connect(self.do_film)
        self.actionSettings.triggered.connect(self.show_settings)

        self.actionModel_Manager_2.triggered.connect(partial(self.show_section, "model_manager"))
        self.actionControlNet.triggered.connect(partial(self.show_section, "controlnet"))
        self.actionPrompt_Builder.triggered.connect(partial(self.show_section, "prompt_builder"))
        self.actionEmbeddings.triggered.connect(partial(self.show_section, "embeddings"))
        self.actionLoRA.triggered.connect(partial(self.show_section, "lora"))
        self.actionPen.triggered.connect(partial(self.show_section, "pen"))
        self.actionStableDiffusion.triggered.connect(partial(self.show_section, "stable_diffusion"))
        self.actionKandinsky.triggered.connect(partial(self.show_section, "kandinsky"))
        self.actionShap_E.triggered.connect(partial(self.show_section, "shapegif"))

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

    def show_hf_cache_manager(self):
        import subprocess
        import platform
        import os
        path = self.settings_manager.settings.hf_cache_path.get()
        if path == "":
            from airunner.utils import default_hf_cache_dir
            path = default_hf_cache_dir()
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", os.path.realpath(path)])
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", os.path.realpath(path)])
        else:
            subprocess.Popen(["xdg-open", os.path.realpath(path)])


    def show_about(self):
        AboutWindow(self.settings_manager, app=self)

    def toggle_grid(self, event):
        self.settings_manager.settings.show_grid.set(
            event
        )
        self.canvas.update()

    def focus_button_clicked(self):
        self.canvas.recenter()

    def toggle_darkmode(self):
        self.set_stylesheet()
