import os

import numpy as np
from PIL import (
    ImageDraw,
    ImageFont
)
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

        self.register(SignalCode.SAFETY_CHECKER_MODEL_LOAD_SIGNAL, self.on_safety_checker_model_load_signal)
        self.register(SignalCode.SAFETY_CHECKER_MODEL_UNLOAD_SIGNAL, self.on_safety_checker_model_unload_signal)
        self.register(SignalCode.FEATURE_EXTRACTOR_LOAD_SIGNAL, self.on_feature_extractor_load_signal)
        self.register(SignalCode.FEATURE_EXTRACTOR_UNLOAD_SIGNAL, self.on_feature_extractor_unload_signal)
        self.register(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, self.on_safety_checker_load_signal)

    @property
    def safety_checker_initialized(self) -> bool:
        try:
            return not self.use_safety_checker or (
                    self.safety_checker is not None and
                    self.feature_extractor is not None and
                    self.pipe.safety_checker is not None and
                    self.pipe.feature_extractor is not None
            )
        except AttributeError:
            pass
        return False

    @property
    def use_safety_checker(self):
        return self.settings["nsfw_filter"]

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

    @property
    def feature_extractor_ready(self) -> bool:
        return self.model_is_loaded(ModelType.FEATURE_EXTRACTOR)

    @property
    def safety_checker_ready(self) -> bool:
        return (self.pipe and ((
           self.use_safety_checker and
           self.feature_extractor and
           self.safety_checker
        ) or (
            not self.use_safety_checker
        )))

    def on_safety_checker_load_signal(self, _message: dict = None):
        self.load_nsfw_filter()

    def on_safety_checker_model_load_signal(self, data_: dict):
        self.__load_safety_checker_model()

    def on_safety_checker_model_unload_signal(self, data_: dict):
        self.__unload_safety_checker_model()

    def on_feature_extractor_load_signal(self, data_: dict):
        self.__load_feature_extractor_model()

    def on_feature_extractor_unload_signal(self, data_: dict):
        self.__unload_feature_extractor_model()

    def load_nsfw_filter(self):
        if self.use_safety_checker and self.safety_checker is None and "path" in self.safety_checker_model:
            self.__load_safety_checker_model()

        if self.use_safety_checker and self.feature_extractor is None and "path" in self.safety_checker_model:
            self.__load_feature_extractor_model()

    def remove_safety_checker_from_pipe(self):
        self.__remove_feature_extractor_from_pipe()
        self.__remove_safety_checker_from_pipe()

    def unload_safety_checker(self, data_: dict = None):
        self.__unload_safety_checker_model()
        self.__unload_feature_extractor_model()

    def unload_feature_extractor(self):
        self.feature_extractor = None
        clear_memory()
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED, "")

    def __unload_safety_checker_model(self):
        if self.pipe is not None:
            self.pipe.safety_checker = None
        self.safety_checker = None
        clear_memory()
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED, "")

    def __unload_feature_extractor_model(self):
        if self.pipe is not None:
            self.pipe.feature_extractor = None
        self.feature_extractor = None
        clear_memory()
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED, "")

    def __load_feature_extractor_model(self):
        feature_extractor = None
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADING, self.feature_extractor_path)
        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
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
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED, self.feature_extractor_path)
        except Exception as e:
            print(e)
            self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Unable to load feature extractor")
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED, self.safety_checker_model["path"])

    def check_and_mark_nsfw_images(self, images) -> bool:
        if not self.feature_extractor or not self.safety_checker:
            return images, [False] * len(images)

        safety_checker_input = self.feature_extractor(images, return_tensors="pt").to(self.device)
        _, has_nsfw_concepts = self.safety_checker(
            images=[np.array(img) for img in images],
            clip_input=safety_checker_input.pixel_values.to(self.device)
        )

        # Mark images as NSFW if NSFW content is detected
        for i, img in enumerate(images):
            if has_nsfw_concepts[i]:
                img = img.convert("RGBA")
                img.paste((0, 0, 0), (0, 0, img.size[0], img.size[1]))
                draw = ImageDraw.Draw(img)
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                draw.text(
                    (
                        self.settings["working_width"] / 2 - 30,
                        self.settings["working_height"] / 2
                    ),
                    "NSFW",
                    (255, 255, 255),
                    font=font
                )
                images[i] = img

        return images, has_nsfw_concepts

    def __load_safety_checker_model(self):
        self.logger.debug(f"Initializing safety checker")
        safety_checker = None
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING, self.safety_checker_model["path"])
        try:
            self.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
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
            self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Unable to load safety checker")
            self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.FAILED, self.safety_checker_model["path"])

    def __remove_feature_extractor_from_pipe(self):
        self.logger.debug("Removing feature extractor from pipe")
        if self.pipe is not None:
            self.pipe.feature_extractor = None
        if self.feature_extractor is not None:
            status = ModelStatus.READY
            path = self.feature_extractor_path
        else:
            status = ModelStatus.UNLOADED
            path = ""
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, status, path)

    def __remove_safety_checker_from_pipe(self):
        self.logger.debug("Removing safety checker from pipe")
        if self.pipe is not None:
            self.pipe.safety_checker = None
        if self.safety_checker is not None:
            status = ModelStatus.READY
            path = self.safety_checker_model["path"]
        else:
            status = ModelStatus.UNLOADED
            path = ""
        self.change_model_status(ModelType.SAFETY_CHECKER, status, path)
