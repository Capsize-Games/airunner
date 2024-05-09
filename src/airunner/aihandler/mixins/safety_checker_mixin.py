import os

from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
from transformers import AutoFeatureExtractor
from airunner.enums import SignalCode, ModelStatus, ModelType
from airunner.settings import SD_FEATURE_EXTRACTOR_PATH
from airunner.utils.clear_memory import clear_memory


class SafetyCheckerMixin:
    def __init__(self, *args, **kwargs):
        self.safety_checker = None
        self.feature_extractor = None
        self.feature_extractor_path = SD_FEATURE_EXTRACTOR_PATH

    @property
    def safety_checker_model(self):
        try:
            return self.models_by_pipeline_action("safety_checker")[0]
        except IndexError:
            return None

    @property
    def text_encoder_model(self):
        try:
            return self.models_by_pipeline_action("text_encoder")[0]
        except IndexError:
            return None

    def unload_safety_checker(self, data_: dict = None):
        self._unload_safety_checker_model()
        self._unload_feature_extractor_model()

    def _unload_safety_checker_model(self):
        self.safety_checker = None
        clear_memory()
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED, "")

    def _unload_feature_extractor_model(self):
        self.feature_extractor = None
        clear_memory()
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED, "")

    def load_safety_checker(self, data_: dict = None):
        if self.use_safety_checker and self.safety_checker is None and "path" in self.safety_checker_model:
            self.safety_checker = self._load_safety_checker_model()

        if self.use_safety_checker and self.feature_extractor is None and "path" in self.safety_checker_model:
            self.feature_extractor = self._load_feature_extractor_model()

    def unload_feature_extractor(self):
        self.feature_extractor = None
        clear_memory()
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED, "")

    def is_ckpt_file(self, model_path) -> bool:
        if not model_path:
            self.logger.error("ckpt path is empty")
            return False
        return model_path.endswith(".ckpt")

    def is_safetensor_file(self, model_path) -> bool:
        if not model_path:
            self.logger.error("safetensors path is empty")
            return False
        return model_path.endswith(".safetensors")


    def _load_feature_extractor_model(self):
        feature_extractor = None
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADING, self.safety_checker_model["path"])
        try:
            feature_extractor = AutoFeatureExtractor.from_pretrained(
                os.path.expanduser(
                    os.path.join(
                        self.settings["path_settings"]["feature_extractor_model_path"],
                        f"{self.feature_extractor_path}/preprocessor_config.json"
                    )
                ),
                local_files_only=True,
                torch_dtype=self.data_type,
                use_safetensors=True,
                device_map=self.device
            )
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED, self.safety_checker_model["path"])
        except Exception as e:
            self.logger.error("Unable to load feature extractor")
            print(e)
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED, self.safety_checker_model["path"])
        return feature_extractor

    def _load_safety_checker_model(self):
        self.logger.debug(f"Initializing safety checker with {self.safety_checker_model}")
        safety_checker = None
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING, self.safety_checker_model["path"])
        try:
            safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                os.path.expanduser(
                    os.path.join(
                        self.settings["path_settings"]["safety_checker_model_path"],
                        "CompVis/stable-diffusion-safety-checker/"
                    )
                ),
                local_files_only=True,
                torch_dtype=self.data_type,
                use_safetensors=True,
                device_map=self.device
            )
            self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADED, self.safety_checker_model["path"])
        except Exception as e:
            print(e)
            self.send_error("Unable to load safety checker")
            self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.FAILED, self.safety_checker_model["path"])
        return safety_checker
