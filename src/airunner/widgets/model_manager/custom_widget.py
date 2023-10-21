import os

from airunner.data.models import AIModel
from airunner.models.modeldata import ModelData
from airunner.utils import get_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.custom_ui import Ui_custom_model_widget


class CustomModelWidget(BaseWidget):
    initialized = False
    widget_class_ = Ui_custom_model_widget
    model_widgets = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()
        self.scan_for_models()
        self.initialized = True

    def action_button_clicked_scan_for_models(self):
        self.scan_for_models()

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

    def save_model(self, model):
        session = get_session()
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
                is_default=False
            )
            session.add(new_model)
            session.commit()

    def show_items_in_scrollarea(self, search=None):
        session = get_session()
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        if search:
            models = session.query(AIModel).filter_by(is_default=False).filter(AIModel.name.like(f"%{search}%")).all()
        else:
            models = session.query(AIModel).filter_by(is_default=False).all()
        for model_widget in self.model_widgets:
            model_widget.deleteLater()
        self.model_widgets = []
        for index, model in enumerate(models):
            version = model.version
            category = model.category
            pipeline_action = model.pipeline_action
            pipeline_class = self.settings_manager.get_pipeline_classname(
                pipeline_action, version, category)

            model_widget = ModelWidget(
                path=model.path,
                branch=model.branch,
                version=version,
                category=category,
                pipeline_action=pipeline_action,
                pipeline_class=pipeline_class,
                # prompts=model.prompts,
            )

            model_widget.ui.name.setChecked(model.enabled)

            self.ui.scrollAreaWidgetContents.layout().addWidget(
                model_widget)

            self.model_widgets.append(model_widget)

    def models_changed(self, key, model, value):
        model.enabled = True
        self.settings_manager.update_model(model)
        self.update_generator_model_dropdown()

    def handle_delete_model(self, model):
        self.settings_manager.delete_model(model)
        self.show_items_in_scrollarea()
        self.update_generator_model_dropdown()

    def update_generator_model_dropdown(self):
        if self.initialized:
            self.app.refresh_available_models()

    def handle_edit_model(self, model, index):
        print("edit button clicked", index)
        self.toggle_model_form_frame(show=True)

        categories = self.app.settings_manager.model_categories
        self.ui.model_form.category.clear()
        self.ui.model_form.category.addItems(categories)
        self.ui.model_form.category.setCurrentText(model.category)

        actions = self.settings_manager.pipeline_actions
        self.ui.model_form.pipeline_action.clear()
        self.ui.model_form.pipeline_action.addItems(actions)
        self.ui.model_form.pipeline_action.setCurrentText(model.pipeline_action)

        self.ui.model_form.model_name.setText(model.name)
        pipeline_class = self.settings_manager.get_pipeline_classname(
            model.pipeline_action, model.version, model.category)
        self.ui.model_form.pipeline_class_line_edit.setText(pipeline_class)
        self.ui.model_form.enabled.setChecked(True)
        self.ui.model_form.path_line_edit.setText(model.path)

        versions = self.settings_manager.versions
        self.ui.model_form.versions.clear()
        self.ui.model_form.versions.addItems(versions)
        self.ui.model_form.versions.setCurrentText(model.version)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_toggled(self, val):
        print("toggle_all_toggled", val)
    
    def search_text_edited(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)