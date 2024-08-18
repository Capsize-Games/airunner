import os

from airunner.aihandler.logger import Logger
from airunner.enums import SignalCode
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.workers.worker import Worker


class VAEScannerWorker(
    Worker,
    PipelineMixin
):
    def __init__(self, *args, **kwargs):
        Worker.__init__(self)
        PipelineMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)

    def handle_message(self, _message):
        self.scan_for_vae()

    def scan_for_vae(self):
        vae_model_path = self.settings["path_settings"]["vae_model_path"]
        vae_model_path = os.path.expanduser(vae_model_path)
        if not vae_model_path or not os.path.exists(vae_model_path):
            return
        # find all folders inside of model_path, each of those folders is a model version
        models = []
        with os.scandir(vae_model_path) as dir_object:
            # check if dir_object is a directory
            self.logger.debug(f"Scan for vae {vae_model_path}")
            for entry in dir_object:
                version = entry.name
                with os.scandir(os.path.join(vae_model_path, version)) as dir_object:
                    for entry in dir_object:
                        if entry.is_file():  # ckpt or safetensors file
                            if entry.name.endswith(".ckpt") or entry.name.endswith(".safetensors"):
                                name = entry.name.replace(".ckpt", "").replace(".safetensors", "")
                                model_name = name
                            else:
                                model_name = None

                        if model_name:
                            models.append({
                                'name': model_name,
                                'path': entry.path,
                                'branch': "main",
                                'version': version,
                                'category': "vae",
                                'is_default': False
                            })
        self.emit_signal(SignalCode.VAE_MODELS_SAVE_OR_UPDATE_SIGNAL, {"models": models})
