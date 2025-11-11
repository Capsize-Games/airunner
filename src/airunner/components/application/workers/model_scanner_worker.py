import os

from airunner.components.art.data.ai_models import AIModels
from airunner.enums import SignalCode
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.components.application.workers.worker import Worker


class ModelScannerWorker(Worker, PipelineMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PipelineMixin.__init__(self)

    def handle_message(self, _message):
        self.scan_for_models()
        self.remove_missing_models()

    def scan_for_models(self):
        self.logger.debug("Scan for models")
        # look at model path and determine if we can import existing local models
        # first look at all files and folders inside of the model paths
        diffusers_folders = [
            "scheduler",
            "text_encoder",
            "tokenizer",
            "unet",
            "vae",
        ]
        models = []
        model_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
            )
        )
        self.logger.debug(f"Model path: {model_path}")
        if not os.path.exists(model_path):
            self.logger.debug(
                f"Model path does not exist, creating: {model_path}"
            )
            os.makedirs(model_path)

        # Check if model_path is empty
        try:
            entries = list(os.scandir(model_path))
            self.logger.debug(f"Found {len(entries)} entries in model path")
            if len(entries) == 0:
                self.logger.debug("Model path is empty")
        except Exception as e:
            self.logger.error(f"Error scanning model path: {e}")
            entries = []

        # find all folders inside of model_path, each of those folders is a model version
        print("model_path", model_path)
        with os.scandir(model_path) as dir_object:
            # check if dir_object is a directory
            for version_entry in dir_object:
                version = version_entry.name
                path = os.path.join(model_path, version)
                with os.scandir(path) as action_object:
                    for action_item in action_object:
                        action = action_item.name
                        if "controlnet_processors" in action_item.path:
                            continue
                        paths = [action_item.path]
                        for path in paths:
                            if not os.path.exists(path):
                                continue
                            if not os.path.isdir(path):
                                continue
                            with os.scandir(path) as file_object:
                                for file_item in file_object:
                                    model = AIModels()
                                    model.name = os.path.basename(
                                        file_item.path
                                    )
                                    model.path = file_item.path
                                    model.branch = "main"
                                    model.version = version
                                    model.category = "flux"
                                    model.pipeline_action = action
                                    model.enabled = True
                                    model.model_type = "art"
                                    model.is_default = False
                                    if (
                                        file_item.is_file()
                                    ):  # ckpt, safetensors, or gguf file
                                        if (
                                            file_item.name.endswith(".ckpt")
                                            or file_item.name.endswith(
                                                ".safetensors"
                                            )
                                            or file_item.name.endswith(".gguf")
                                        ):
                                            name = (
                                                file_item.name.replace(
                                                    ".ckpt", ""
                                                )
                                                .replace(".safetensors", "")
                                                .replace(".gguf", "")
                                            )
                                            model.name = name
                                        else:
                                            model = None
                                    elif (
                                        file_item.is_dir()
                                    ):  # diffusers folder
                                        is_diffusers_directory = True
                                        for (
                                            diffuser_folder
                                        ) in diffusers_folders:
                                            if not os.path.exists(
                                                os.path.join(
                                                    file_item.path,
                                                    diffuser_folder,
                                                )
                                            ):
                                                is_diffusers_directory = False
                                                model = None
                                        if is_diffusers_directory:
                                            model.name = file_item.name

                                    if model:
                                        self.logger.debug(
                                            f"Found model: {model.name} at {model.path}"
                                        )
                                        models.append(model)
        self.logger.debug(f"Total models found: {len(models)}")
        self.emit_signal(
            SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, {"models": models}
        )

    def remove_missing_models(self):
        # remove all models that are not in the model path
        model_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
            )
        )
        if not os.path.exists(model_path):
            self.logger.error(f"Model path does not exist: {model_path}")
            return
        existing_models = AIModels.objects.all()
        for model in existing_models:
            if not os.path.exists(model.path):
                self.logger.debug(f"Remove missing model {model.id}")
                AIModels.objects.delete(model.id)
                self.logger.debug(f"Removed missing model: {model.name}")
