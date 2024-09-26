import os

import numpy as np
from PIL import (
    ImageDraw,
    ImageFont
)
from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
from transformers import AutoFeatureExtractor
from airunner.enums import SignalCode, ModelStatus, ModelType
from airunner.settings import SD_FEATURE_EXTRACTOR_PATH, BASE_PATH
from airunner.utils.clear_memory import clear_memory


class SafetyCheckerMixin:
    def __init__(self, *args, **kwargs):
        self.safety_checker = None
        self.feature_extractor = None
        self.feature_extractor_path = SD_FEATURE_EXTRACTOR_PATH
        self.__safety_checker_model_status = ModelStatus.UNLOADED
        self.__feature_extractor_model_status = ModelStatus.UNLOADED

    def __change_model_status(self, model, status):
        if model is ModelType.FEATURE_EXTRACTOR:
            self.__feature_extractor_model_status = status
            if self.__safety_checker_model_status is ModelStatus.LOADED and status is ModelStatus.LOADED:
                self.change_model_status(ModelType.SAFETY_CHECKER, status)
        elif model is ModelType.SAFETY_CHECKER:
            self.__safety_checker_model_status = status
            if status is ModelStatus.LOADED and self.__feature_extractor_model_status is not status:
                status = self.__feature_extractor_model_status
        self.change_model_status(model, status)

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
        return self.application_settings.nsfw_filter

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
        return self.__feature_extractor_model_status is ModelStatus.LOADED

    @property
    def safety_checker_ready(self) -> bool:
        return (self.pipe and ((
           self.use_safety_checker and
           self.feature_extractor and
           self.safety_checker
        ) or (
            not self.use_safety_checker
        )))

    def load_safety_checker(self):
        self.__change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        self.__load_safety_checker_model()
        self.__load_feature_extractor_model()

    def unload_safety_checker(self):
        self.__unload_safety_checker_model()
        self.__unload_feature_extractor_model()

    def unload_feature_extractor(self):
        self.feature_extractor = None
        self.clear_memory()
        self.__change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED)

    def __unload_feature_extractor_model(self):
        if self.pipe is not None:
            self.pipe.feature_extractor = None
        self.feature_extractor = None
        self.clear_memory()
        self.__change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.UNLOADED)

    def __unload_safety_checker_model(self):
        if self.pipe is not None:
            self.pipe.safety_checker = None
        self.safety_checker.to("cpu")
        del self.safety_checker
        self.safety_checker = None
        self.__change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED)
        self.clear_memory()

    def __load_feature_extractor_model(self):
        self.__change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADING)
        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
                os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art/models/SD 1.5/feature_extractor",
                        "openai/clip-vit-large-patch14/"
                    )
                ),
                local_files_only=True,
                torch_dtype=self.data_type,
                use_safetensors=True,
                device_map=self.device
            )
            self.__change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED)
        except Exception as e:
            print(e)
            self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Unable to load feature extractor")
            self.__change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED)

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
                font = ImageFont.load_default(50)  # load_default() does not support size argument

                # Text you want to center
                text = "NSFW"

                # Calculate the bounding box of the text
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Calculate the position to center the text line
                text_x = (img.width - text_width) // 2
                text_y = (img.height - text_height) // 2

                # Draw the text at the calculated position, ensuring the text line is centered
                draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

                images[i] = img

        return images, has_nsfw_concepts

    def __load_safety_checker_model(self):
        self.logger.debug(f"Initializing safety checker")
        safety_checker = None
        self.__change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        try:
            self.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                os.path.expanduser(
                    os.path.join(
                        self.path_settings.base_path,
                        "art/models/SD 1.5/safety_checker",
                        "CompVis/stable-diffusion-safety-checker/"
                    )
                ),
                local_files_only=True,
                torch_dtype=self.data_type,
                use_safetensors=False,
                device_map=self.device
            )
            self.__change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADED)
        except Exception as e:
            print(e)
            self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Unable to load safety checker")
            self.__change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.FAILED)
