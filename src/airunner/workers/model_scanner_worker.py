import os

from airunner.data.models.settings_models import AIModels
from airunner.enums import SignalCode
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.workers.worker import Worker


class ModelScannerWorker(
    Worker,
    PipelineMixin
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PipelineMixin.__init__(self)

    def handle_message(self):
        self.scan_for_models()

    def scan_for_models(self):
        self.logger.debug("Scan for models")
        # look at model path and determine if we can import existing local models
        # first look at all files and folders inside of the model paths
        diffusers_folders = ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]
        models = []
        model_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path, "art/models",
            )
        )
        if not os.path.exists(model_path):
            self.logger.error(f"Model path does not exist: {model_path}")
            return
        # find all folders inside of model_path, each of those folders is a model version
        with os.scandir(model_path) as dir_object:
            # check if dir_object is a directory
            self.logger.debug(f"Scan for models {model_path}")
            for version_entry in dir_object:
                version = version_entry.name
                path = os.path.join(model_path, version)
                self.logger.debug(f"Scan directory {path}")
                with os.scandir(path) as action_object:
                    for action_item in action_object:
                        action = action_item.name
                        if "controlnet_processors" in action_item.path:
                            continue
                        with os.scandir(action_item.path) as file_object:
                            for file_item in file_object:
                                model = AIModels()
                                model.name = os.path.basename(file_item.path)
                                model.path = file_item.path
                                model.branch = "main"
                                model.version = version
                                model.category = "stablediffusion"
                                model.pipeline_action = action
                                model.enabled = True
                                model.model_type = "art"
                                model.is_default = False
                                if file_item.is_file():  # ckpt or safetensors file
                                    if file_item.name.endswith(".ckpt") or file_item.name.endswith(".safetensors"):
                                        name = file_item.name.replace(".ckpt", "").replace(".safetensors", "")
                                        model.name = name
                                    else:
                                        model = None
                                elif file_item.is_dir():  # diffusers folder
                                    is_diffusers_directory = True
                                    for diffuser_folder in diffusers_folders:
                                        if not os.path.exists(os.path.join(file_item.path, diffuser_folder)):
                                            is_diffusers_directory = False
                                            model = None
                                    if is_diffusers_directory:
                                        model.name = file_item.name

                                if model:
                                    models.append(model)
        self.emit_signal(SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, {"models": models})
