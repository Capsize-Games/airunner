from PyQt6.QtWidgets import QFileDialog

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

    def models_changed(self, key, model, value):
        model["enabled"] = True
        self.update_generator_model_dropdown()

    def handle_delete_model(self, model):
        self.emit("ai_model_delete_signal", model)
        self.show_items_in_scrollarea()
        self.update_generator_model_dropdown()

    def update_generator_model_dropdown(self):
        self.ui.generator_model_dropdown.clear()
        self.ui.generator_model_dropdown.addItems(self.settings["ai_models"])
    
    def handle_edit_model(self, model, index):
        self.toggle_model_form_frame(show=True)

        categories = self.get_service("ai_model_categories")()
        self.ui.model_form.category.clear()
        self.ui.model_form.category.addItems(categories)
        self.ui.model_form.category.setCurrentText(model.category)

        actions = self.get_service("ai_model_pipeline_actions")()
        self.ui.model_form.pipeline_action.clear()
        self.ui.model_form.pipeline_action.addItems(actions)
        self.ui.model_form.pipeline_action.setCurrentText(model.pipeline_action)

        self.ui.model_form.model_name.setText(model.name)
        pipeline_class = self.get_service("get_pipeline_classname")(
            model.pipeline_action, model.version, model.category)
        self.ui.model_form.pipeline_class_line_edit.setText(pipeline_class)
        self.ui.model_form.enabled.setChecked(True)
        self.ui.model_form.path_line_edit.setText(model.path)

        versions = self.get_service("ai_model_versions")()
        self.ui.model_form.versions.clear()
        self.ui.model_form.versions.addItems(versions)
        self.ui.model_form.versions.setCurrentText(model.version)