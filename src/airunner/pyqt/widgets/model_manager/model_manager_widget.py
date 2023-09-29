import os
from functools import partial
import threading

from PyQt6 import QtGui
from PyQt6 import uic
from PyQt6.QtWidgets import QFileDialog

from airunner.aihandler.download_civitai import DownloadCivitAI
from airunner.data.models import AIModel
from airunner.models.modeldata import ModelData
from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.data.db import session
from airunner.pyqt.widgets.model_manager.templates.model_manager_ui import Ui_model_manager


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
    icons = {
        "toolButton": "010-view",
        "edit_button": "settings",
        "delete_button": "006-trash",
    }

    def set_stylesheet(self):
        for key in self.model_widgets.keys():
            for model_widget in self.model_widgets[key]:
                for button, icon in self.icons.items():
                    getattr(model_widget, button).setIcon(
                        QtGui.QIcon(
                            os.path.join(f"src/icons/{icon}{'-light' if self.is_dark else ''}.png")
                        )
                    )

    @property
    def current_model_object(self):
        if not self._current_model_object:
            self._current_model_object = ModelData()
        return self._current_model_object

    def models_changed(self, key, model, value):
        model.enabled = True
        self.settings_manager.update_model(model)
        self.update_generator_model_dropdown()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # load tabs
        self.default_tab = uic.loadUi("pyqt/widgets/model_manager/templates/default.ui")
        self.custom_tab = uic.loadUi("pyqt/widgets/model_manager/templates/custom.ui")
        self.import_tab = uic.loadUi("pyqt/widgets/model_manager/templates/import.ui")
        self.ui.tabs.addTab(self.default_tab, "Default")
        self.ui.tabs.addTab(self.custom_tab, "Custom")
        self.ui.tabs.addTab(self.import_tab, "Import")
        self.default_tab.toggle_all.clicked.connect(partial(self.toggle_all_models, "default"))
        self.custom_tab.toggle_all.clicked.connect(partial(self.toggle_all_models, "custom"))

        self.show_items_in_scrollarea()
        self.custom_tab.scan_for_models_button.clicked.connect(self.scan_for_models)

        self.import_tab.import_button.clicked.connect(self.import_models)
        self.import_tab.download_button.clicked.connect(self.download_model)

        self.import_tab.cancel_download_button.clicked.connect(self.cancel_download)
        self.import_tab.cancel_download_save_button.clicked.connect(self.reset_form)
        self.toggle_model_download_form_elements_stage_1(show=True)
        self.toggle_model_download_form_elements_stage_2()
        self.toggle_model_download_form_elements_stage_3()

        self.set_stylesheet()

    def toggle_all_models(self, key, value):
        for model in self.model_widgets[key]:
            model.name.setChecked(value)

    def scan_for_models(self):
        # look at model path and determine if we can import existing local models
        # first look at all files and folders inside of the model paths
        base_model_path = self.settings_manager.path_settings.model_base_path
        depth2img_model_path = self.settings_manager.path_settings.depth2img_model_path
        pix2pix_model_path = self.settings_manager.path_settings.pix2pix_model_path
        outpaint_model_path = self.settings_manager.path_settings.outpaint_model_path
        upscale_model_path = self.settings_manager.path_settings.upscale_model_path
        txt2vid_model_path = self.settings_manager.path_settings.txt2vid_model_path
        diffusers_folders = ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]
        for key, model_path in {
            "txt2img": base_model_path,
            "depth2img": depth2img_model_path,
            "pix2pix": pix2pix_model_path,
            "outpaint": outpaint_model_path,
            "upscale": upscale_model_path,
            "txt2vid": txt2vid_model_path
        }.items():
            if not model_path or not os.path.exists(model_path):
                continue
            with os.scandir(model_path) as dir_object:
                for entry in dir_object:
                    model = ModelData()
                    model.path = entry.path
                    model.branch = "main"
                    model.version = "SD 1.5"
                    model.category = "stablediffusion"
                    model.enabled = True
                    model.pipeline_action = key
                    model.pipeline_class = self.settings_manager.get_pipeline_classname(
                        model.pipeline_action, model.version, model.category)

                    if entry.is_file():  # ckpt or safetensors file
                        if entry.name.endswith(".ckpt") or entry.name.endswith(".safetensors"):
                            name = entry.name.replace(".ckpt", "").replace(".safetensors", "")
                            model.name = name
                        else:
                            model = None
                    elif entry.is_dir():  # diffusers folder
                        is_diffusers_directory = True
                        for diffuser_folder in diffusers_folders:
                            if not os.path.exists(os.path.join(entry.path, diffuser_folder)):
                                is_diffusers_directory = False
                                model = None
                        if is_diffusers_directory:
                            model.name = entry.name

                    if model:
                        self.save_model(model)

        self.show_items_in_scrollarea()
        self.update_generator_model_dropdown()

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

    def toggle_model_form_frame(self, show=False):
        if show and not self.model_form:
            self.model_form = uic.loadUi("pyqt/widgets/model_manager/model_form.ui")
            self.import_tab.model_form_frame.layout().addWidget(self.model_form)
        elif not show:
            self.import_tab.model_form_frame.layout().removeWidget(self.model_form)
            self.model_form = None

    def model_version_changed(self, index):
        self.set_model_form_data()

    def download_path(self, file):
        path = self.settings_manager.path_settings.model_base_path
        file_name = file["name"]
        return f"{path}/{file_name}"

    def download_model(self):
        self.toggle_model_form_frame(show=False)
        self.toggle_model_download_form_elements_stage_1(show=False)
        self.toggle_model_download_form_elements_stage_2(show=False)
        self.toggle_model_download_form_elements_stage_3(show=True)
        self.download_civit_ai = DownloadCivitAI()

        # get value from import_widget.model_choices
        download_url, file, model_version = self.import_tab.model_choices.currentData()
        file_path = self.download_path(file)
        size_kb = file["sizeKB"]
        self.add_new_model()
        thread = threading.Thread(target=self.download_model_thread, args=(download_url, file_path, size_kb))
        thread.start()

    def download_model_thread(self, download_url, file_path, size_kb):
        self.download_civit_ai.download_model(download_url, file_path, size_kb, self.download_callback)

    def download_callback(self, current_size, total_size):
        current_size = int(current_size / total_size * 100)
        self.import_tab.download_progress_bar.setValue(current_size)
        if current_size >= total_size:
            self.reset_form()
            self.settings_manager.add_model(self.current_model_data)
            self.show_items_in_scrollarea()

    def import_models(self):
        url = self.import_tab.import_url.text()
        try:
            model_id = url.split("/")[4]
        except IndexError:
            return

        self.toggle_model_download_form_elements_stage_1(show=False)
        self.toggle_model_download_form_elements_stage_2(show=True)

        data = DownloadCivitAI.get_json(model_id)
        self.current_model_data = data
        self.is_civitai = "civitai.com" in url
        model_name = data["name"]
        model_versions = data["modelVersions"]
        self.toggle_model_form_frame(show=True)
        self.import_tab.model_choices.clear()
        for model_version in model_versions:
            version_name = model_version["name"]
            download_url = model_version["downloadUrl"]
            sd_model_version = model_version["baseModel"]
            file = model_version["files"][0]
            url = file["url"]
            download_choice = f"{model_name} - {version_name} - {sd_model_version}"
            self.import_tab.model_choices.addItem(download_choice, (download_url, file, model_version))

        self.import_tab.model_choices.currentIndexChanged.connect(self.model_version_changed)

        self.current_model_object.url = url

        self.set_model_form_data()

    def set_model_form_data(self):
        try:
            download_url, file, model_version = self.import_tab.model_choices.currentData()
        except TypeError:
            return
        model_version_name = model_version["name"]

        categories = self.settings_manager.model_categories()
        self.model_form.category.clear()
        self.model_form.category.addItems(categories)
        category = "stablediffusion"
        self.model_form.category.setCurrentText(category)
        actions = self.settings_manager.pipeline_actions

        self.model_form.pipeline_action.clear()
        self.model_form.pipeline_action.addItems(actions)
        pipeline_action = "txt2img"
        if "inpaint" in model_version_name:
            pipeline_action = "outpaint"
        self.model_form.pipeline_action.setCurrentText(pipeline_action)

        self.model_form.model_name.setText(self.current_model_data["name"])
        version = model_version["baseModel"]
        pipeline_class = self.settings_manager.get_pipeline_classname(pipeline_action, version, category)
        versions = self.settings_manager.versions
        self.model_form.versions.clear()
        self.model_form.versions.addItems(versions)
        self.model_form.versions.setCurrentText(version)
        self.model_form.pipeline_class_line_edit.setText(pipeline_class)
        self.model_form.enabled.setChecked(True)

        # path is the download path of the model
        path = self.download_path(file)
        self.model_form.path_line_edit.setText(path)

        if self.is_civitai:
            self.model_form.branch_label.hide()
            self.model_form.branch_line_edit.hide()

    def show_items_in_scrollarea(self):
        models = self.settings_manager.models.all()
        for key in self.model_widgets.keys():
            for model_widget in self.model_widgets[key]:
                model_widget.deleteLater()
        self.model_widgets = {
            "default": [],
            "custom": []
        }
        for index, model in enumerate(models):
            version = model.version
            category = model.category
            pipeline_action = model.pipeline_action

            model_widget = uic.loadUi("pyqt/widgets/model_manager/templates/model.ui")
            model_widget.path.setText(model.path)
            model_widget.branch.setText(model.branch)
            model_widget.version.setText(version)
            model_widget.category.setText(category)
            model_widget.pipeline_action.setText(pipeline_action)
            if version == "" or category == "":
                continue
            pipeline_class = self.settings_manager.get_pipeline_classname(
                pipeline_action, version, category)
            model_widget.pipeline_class.setText(pipeline_class)
            model_widget.name.setText(model.name)

            key = "default" if model.default else "custom"

            if key == "default":
                model_widget.delete_button.hide()
                model_widget.edit_button.deleteLater()
                model_widget.toolButton.deleteLater()
            else:
                model_widget.edit_button.clicked.connect(
                    partial(
                        self.handle_edit_model,
                        model,
                        index
                    )
                )
                model_widget.delete_button.clicked.connect(
                    partial(self.handle_delete_model, model)
                )
                model_widget.toolButton.clicked.connect(partial(self.toggle_details, model_widget))

            model_widget.name.setChecked(model.enabled)
            model_widget.name.stateChanged.connect(
                partial(
                    self.models_changed,
                    key,
                    model
                )
            )

            self.hide_details(model_widget)

            if key == "default":
                self.default_tab.scrollAreaWidgetContents.layout().addWidget(model_widget)
            elif key == "custom":
                self.custom_tab.scrollAreaWidgetContents.layout().addWidget(model_widget)

            self.model_widgets[key].append(model_widget)

    def toggle_details(self, model_widget):
        details_are_shown = getattr(model_widget, "details_are_shown", False)
        if details_are_shown:
            self.hide_details(model_widget)
        else:
            self.show_details(model_widget)

    def show_details(self, model_widget):
        model_widget.details_are_shown = True
        for i in range(model_widget.details.layout().count()):
            model_widget.details.layout().itemAt(i).widget().show()

    def hide_details(self, model_widget):
        model_widget.details_are_shown = False
        for i in range(model_widget.details.layout().count()):
            model_widget.details.layout().itemAt(i).widget().hide()

    def handle_edit_model(self, model, index):
        print("edit button clicked", index)
        self.toggle_model_form_frame(show=True)

        categories = self.app.settings_manager.model_categories
        self.model_form.category.clear()
        self.model_form.category.addItems(categories)
        self.model_form.category.setCurrentText(model.category)

        actions = self.settings_manager.pipeline_actions
        self.model_form.pipeline_action.clear()
        self.model_form.pipeline_action.addItems(actions)
        self.model_form.pipeline_action.setCurrentText(model.pipeline_action)

        self.model_form.model_name.setText(model.name)
        pipeline_class = self.settings_manager.get_pipeline_classname(
            model.pipeline_action, model.version, model.category)
        self.model_form.pipeline_class_line_edit.setText(pipeline_class)
        self.model_form.enabled.setChecked(True)
        self.model_form.path_line_edit.setText(model.path)

        versions = self.settings_manager.versions
        self.model_form.versions.clear()
        self.model_form.versions.addItems(versions)
        self.model_form.versions.setCurrentText(model.version)

    def handle_delete_model(self, model):
        self.settings_manager.delete_model(model)
        self.show_items_in_scrollarea()
        self.update_generator_model_dropdown()

    def update_generator_model_dropdown(self):
        self.app.generator_tab_widget.update_available_models()

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

    def save_model(self, model):
        model_exists = session.query(AIModel).filter_by(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action
        ).first()
        if not model_exists:
            new_model = AIModel(
                name=model.name,
                path=model.path,
                branch=model.branch,
                version=model.version,
                category=model.category,
                pipeline_action=model.pipeline_action,
                enabled=model.enabled,
                default=False
            )
            session.add(new_model)
            session.commit()
