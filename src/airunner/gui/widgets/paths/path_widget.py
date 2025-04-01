import os

from PySide6.QtWidgets import QFileDialog
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.paths.templates.path_ui import Ui_path_widget


class PathWidget(BaseWidget):
    widget_class_ = Ui_path_widget

    @property
    def title(self):
        return self.property("title")

    @property
    def description(self):
        return self.property("description")

    @property
    def path_name(self):
        return self.property("path_name")

    @property
    def path(self):
        return getattr(self.path_settings, self.path_name)

    def showEvent(self, event):
        super().showEvent(event)
        self.ui.title_label.setText(self.title)
        self.ui.description_label.setText(self.description)
        path = self.path
        if self.path_name == "hf_cache" and path == "":
            path = self.path_settings.hf_cache_path
        obj = getattr(self.ui, f"path")
        obj.setText(path)

    def action_path_changed(self, text):
        self.set_path(text)

    def action_button_clicked(self):
        path = self.path
        if not os.path.exists(path):
            path = self.path_settings.model_base_path
        if not os.path.exists(path):
            path = os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            None, "Select Directory", path)
        if path != "":
            self.set_path(path)

    def auto_discover(self):
        if self.path_name == "hf_cache_path":
            return

        home = os.path.expanduser("~")

        base_path = self.path_settings.base_path
        if base_path == "":
            base_path = os.path.join(home, "airunner")

        models_path = os.path.join(base_path, "models")

        folder_path = os.path.join(models_path, self.path_name)
        self.set_path(folder_path)

    def set_path(self, path):
        self.ui.path.setText(path)
        self.update_path_settings(self.path_name, path)
