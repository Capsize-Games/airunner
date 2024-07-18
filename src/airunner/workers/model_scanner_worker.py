import os

from airunner.aihandler.logger import Logger
from airunner.enums import SignalCode
from airunner.models.modeldata import ModelData
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.workers.worker import Worker


class ModelScannerWorker(
    Worker,
    PipelineMixin
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        PipelineMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)

    def handle_message(self, _message):
        self.scan_for_models()

    def scan_for_models(self):
        self.logger.debug("Scan for models")
        # look at model path and determine if we can import existing local models
        # first look at all files and folders inside of the model paths
        txt2img_model_path = self.settings["path_settings"]["txt2img_model_path"]
        depth2img_model_path = self.settings["path_settings"]["depth2img_model_path"]
        pix2pix_model_path = self.settings["path_settings"]["pix2pix_model_path"]
        inpaint_model_path = self.settings["path_settings"]["inpaint_model_path"]
        upscale_model_path = self.settings["path_settings"]["upscale_model_path"]
        txt2vid_model_path = self.settings["path_settings"]["txt2vid_model_path"]
        llm_causallm_model_path = self.settings["path_settings"]["llm_causallm_model_path"]
        llm_seq2seq_model_path = self.settings["path_settings"]["llm_seq2seq_model_path"]
        embeddings_model_path = self.settings["path_settings"]["embeddings_model_path"]
        diffusers_folders = ["scheduler", "text_encoder", "tokenizer", "unet", "vae"]
        models = []
        for key, model_path in {
            "txt2img": txt2img_model_path,
            "depth2img": depth2img_model_path,
            "pix2pix": pix2pix_model_path,
            "outpaint": inpaint_model_path,
            "upscale": upscale_model_path,
            "txt2vid": txt2vid_model_path,
            "causallm": llm_causallm_model_path,
            "seq2seq": llm_seq2seq_model_path,
            "embeddings": embeddings_model_path
        }.items():
            model_path = os.path.expanduser(model_path)
            if not model_path or not os.path.exists(model_path):
                continue
            # find all folders inside of model_path, each of those folders is a model version
            with os.scandir(model_path) as dir_object:
                # check if dir_object is a directory
                self.logger.debug(f"Scan for models {key} {model_path}")
                for entry in dir_object:
                    version = entry.name
                    path = os.path.join(model_path, version)
                    self.logger.debug(f"Scan directory {path}")
                    with os.scandir(path) as dir_object:
                        for entry in dir_object:
                            model = ModelData()
                            model.path = entry.path
                            model.branch = "main"
                            model.version = version
                            model.category = "stablediffusion"
                            model.enabled = True
                            model.pipeline_action = key
                            model.pipeline_class = self.get_pipeline_classname(
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
                                models.append({
                                    'name': model.name,
                                    'path': model.path,
                                    'branch': model.branch,
                                    'version': model.version,
                                    'category': model.category,
                                    'pipeline_action': model.pipeline_action,
                                    'enabled': model.enabled,
                                    'is_default': False
                                })
        self.emit_signal(SignalCode.AI_MODELS_SAVE_OR_UPDATE_SIGNAL, {"models": models})
