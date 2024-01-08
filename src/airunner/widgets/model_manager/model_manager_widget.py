import os
import threading

from PyQt6 import QtGui
from PyQt6 import uic
from PyQt6.QtWidgets import QFileDialog

from airunner.aihandler.download_civitai import DownloadCivitAI
from airunner.models.modeldata import ModelData
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.templates.model_manager_ui import Ui_model_manager


class ModelManagerWidget(BaseWidget):
    widget_class_ = Ui_model_manager
    is_modal = True
    current_model_form = None
    model_widgets = {
        "default": [],
        "custom": []
    }
    is_civitai = False
    current_model_data = None
    _current_model_object = None
    model_form = None

    @property
    def current_model_object(self):
        if not self._current_model_object:
            self._current_model_object = ModelData()
        return self._current_model_object

    def toggle_all_models(self, key, value):
        for model in self.model_widgets[key]:
            model.name.setChecked(value)

    def reset_form(self):
        self.toggle_model_download_form_elements_stage_1(show=True)
        self.toggle_model_download_form_elements_stage_2(show=False)
        self.toggle_model_download_form_elements_stage_3(show=False)
        self.toggle_model_form_frame(show=False)

    def cancel_download(self):
        self.download_civit_ai.cancel_download = True
        self.reset_form()

    def toggle_model_download_form_elements_stage_1(self, show=False):
        if show:
            self.import_tab.url_label.show()
            self.import_tab.import_url.show()
            self.import_tab.import_button.show()
        else:
            self.import_tab.url_label.hide()
            self.import_tab.import_url.hide()
            self.import_tab.import_button.hide()

    def toggle_model_download_form_elements_stage_2(self, show=False):
        if show:
            self.import_tab.model_version_label.show()
            self.import_tab.model_choices.show()
            self.import_tab.download_button.show()
            self.import_tab.cancel_download_save_button.show()
        else:
            self.import_tab.model_version_label.hide()
            self.import_tab.model_choices.hide()
            self.import_tab.download_button.hide()
            self.import_tab.cancel_download_save_button.hide()

    def toggle_model_download_form_elements_stage_3(self, show=False):
        if show:
            self.import_tab.downloading_label.show()
            self.import_tab.downloading_label.setText(f"Downloading {self.current_model_data['name']}")
            self.import_tab.download_progress_bar.show()
            self.import_tab.cancel_download_button.show()
        else:
            self.import_tab.downloading_label.hide()
            self.import_tab.download_progress_bar.hide()
            self.import_tab.cancel_download_button.hide()

    def browse_for_model_path(self):
        # get a path to a directory or file
        path = QFileDialog.getOpenFileName(
            self.template,
            "Select a model file",
            "",
            "Model files (*.ckpt *.safetensors)"
        )[0]
        self.ui.path_line_edit.setText(path)

    def browse_for_diffusers_path(self):
        # get a path to a directory or file
        path = QFileDialog.getExistingDirectory(
            self.template,
            "Select a diffusers directory",
            ""
        )
        self.ui.path_line_edit.setText(path)

    def handle_model_object_value_change(self, key, value):
        setattr(self.current_model_object, key, value)

    def add_new_model(self):
        self.save_model(self.current_model_object)

    def tab_changed(self, val):
        print("tab_changed", val)
