import os
from functools import partial

from PyQt6.QtWidgets import QFileDialog

from airunner.utils import default_hf_cache_dir
from airunner.windows.custom_widget import CustomWidget


class PathsWidget(CustomWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, filename="paths")
        self.initialize_window()

    def initialize_window(self):
        elements = [
            "hf_cache",
            "model_base",
            "depth2img_model",
            "pix2pix_model",
            "outpaint_model",
            "upscale_model",
            "txt2vid_model",
            "embeddings",
            "lora",
            "image",
            "gif",
            "video",
        ]
        for element in elements:
            getattr(self, f"{element}_button").clicked.connect(
                partial(self.handle_browse_button, element))
            getattr(self, f"{element}_path").textChanged.connect(
                partial(self.set_value, f"path_settings.{element}_path"))
            val = getattr(self.settings_manager.path_settings, f"{element}_path")
            if element == "hf_cache" and val == "":
                val = default_hf_cache_dir()
            getattr(self, f"{element}_path").setText(val)

    def handle_browse_button(self, element):
        settings_option = getattr(self.settings_manager.path_settings, f"{element}_path")
        if not os.path.exists(settings_option):
            settings_option = self.settings_manager.path_settings.model_base_path
        if not os.path.exists(settings_option):
            # home directory
            settings_option = os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            None,
            "Select Directory",
            settings_option)
        getattr(self, f"{element}_path").setText(path)
        self.settings_manager.set_value(f"path_settings.{element}_path", path)

    def set_value(self, key, val):
        self.settings_manager.set_value(key, val)
