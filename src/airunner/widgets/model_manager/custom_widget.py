import os

from airunner.models.modeldata import ModelData
from airunner.service_locator import ServiceLocator
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.model_manager.model_widget import ModelWidget
from airunner.widgets.model_manager.templates.custom_ui import Ui_custom_model_widget
from airunner.workers.worker import Worker

from PyQt6 import QtWidgets
from airunner.aihandler.logger import Logger

logger = Logger(prefix="CustomModelWidget")


class ModelScannerWorker(Worker):
    def handle_message(self, _message):
        self.scan_for_models()

    def scan_for_models(self):
        self.logger.info("Scan for models")
        # look at model path and determine if we can import existing local models
        # first look at all files and folders inside of the model paths
        txt2img_model_path = self.path_settings["txt2img_model_path"]
        depth2img_model_path = self.path_settings["depth2img_model_path"]
        pix2pix_model_path = self.path_settings["pix2pix_model_path"]
        outpaint_model_path = self.path_settings["inpaint_model_path"]
        upscale_model_path = self.path_settings["upscale_model_path"]
        txt2vid_model_path = self.path_settings["txt2vid_model_path"]
        llm_casuallm_model_path = self.path_settings["llm_casuallm_model_path"]
        llm_seq2seq_model_path = self.path_settings["llm_seq2seq_model_path"]
        diffusers_folders = ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]
        models = []
        for key, model_path in {
            "txt2img": txt2img_model_path,
            "depth2img": depth2img_model_path,
            "pix2pix": pix2pix_model_path,
            "outpaint": outpaint_model_path,
            "upscale": upscale_model_path,
            "txt2vid": txt2vid_model_path,
            "casuallm": llm_casuallm_model_path,
            "seq2seq": llm_seq2seq_model_path,
        }.items():
            if not model_path or not os.path.exists(model_path):
                continue
            # find all folders inside of model_path, each of those folders is a model version
            with os.scandir(model_path) as dir_object:
                # check if dir_object is a directory
                logger.info(f"Scan for models {key} {model_path}")
                for entry in dir_object:
                    version = entry.name
                    with os.scandir(os.path.join(model_path, version)) as dir_object:
                        for entry in dir_object:
                            model = ModelData()
                            model.path = entry.path
                            model.branch = "main"
                            model.version = version
                            model.category = "stablediffusion"
                            model.enabled = True
                            model.pipeline_action = key
                            model.pipeline_class = ServiceLocator.get("get_pipeline_classname")(
                                model.pipeline_action, model.version, model.category
                            )

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
                                models.append(dict(
                                    name=model.name,
                                    path=model.path,
                                    branch=model.branch,
                                    version=model.version,
                                    category=model.category,
                                    pipeline_action=model.pipeline_action,
                                    enabled=model.enabled,
                                    is_default=False
                                ))

        self.emit("ai_models_save_or_update_signal", models)


class CustomModelWidget(BaseWidget):
    initialized = False
    widget_class_ = Ui_custom_model_widget
    model_widgets = []
    spacer = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_items_in_scrollarea()
        self.initialized = True
        self.model_scanner_worker = self.create_worker(ModelScannerWorker)
        self.model_scanner_worker.add_to_queue("scan_for_models")
    
    def action_button_clicked_scan_for_models(self):
        self.model_scanner_worker.add_to_queue("scan_for_models")
   
    def show_items_in_scrollarea(self, search=None):
        if self.spacer:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)
        for child in self.ui.scrollAreaWidgetContents.children():
            if isinstance(child, ModelWidget):
                child.deleteLater()
        if search:
            models = self.get_service("ai_models_find")(search, default=False)
        else:
            models = self.get_service("ai_models_find")(default=False)
        for model_widget in self.model_widgets:
            model_widget.deleteLater()
        self.model_widgets = []
        for index, model in enumerate(models):
            version = model['version']
            category = model['category']
            pipeline_action = model["pipeline_action"]
            pipeline_class = self.get_service("get_pipeline_classname")(
                pipeline_action, version, category)

            model_widget = ModelWidget(
                path=model["path"],
                branch=model["branch"],
                version=version,
                category=category,
                pipeline_action=pipeline_action,
                pipeline_class=pipeline_class,
            )

            model_widget.ui.name.setChecked(model["enabled"])

            self.ui.scrollAreaWidgetContents.layout().addWidget(
                model_widget)

            self.model_widgets.append(model_widget)
        
        if not self.spacer:
            self.spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def mode_type_changed(self, val):
        print("mode_type_changed", val)
    
    def toggle_all_toggled(self, val):
        print("toggle_all_toggled", val)
    
    def search_text_edited(self, val):
        val = val.strip()
        if val == "":
            val = None
        self.show_items_in_scrollarea(val)