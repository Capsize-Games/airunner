import os
import threading
import time
from queue import Queue

from PIL import Image
from controlnet_aux.processor import Processor
from diffusers.pipelines.controlnet.pipeline_controlnet import StableDiffusionControlNetPipeline
from diffusers.pipelines.controlnet.pipeline_controlnet_img2img import StableDiffusionControlNetImg2ImgPipeline
from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint import StableDiffusionControlNetInpaintPipeline
from diffusers.models.controlnet import ControlNetModel
from airunner.enums import (
    SignalCode,
    SDMode,
    ModelType,
    ModelStatus, StableDiffusionVersion, HandlerState, ModelAction
)
from airunner.utils.clear_memory import clear_memory

RELOAD_CONTROLNET_IMAGE_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class ControlnetHandlerMixin:
    def __init__(self):
        self.controlnet = None
        self.processor = None
        self._controlnet_image = None
        self.controlnet_loaded = False
        self.downloading_controlnet = False
        self.__controlnet_model_status = ModelStatus.UNLOADED
        self.__controlnet_processor_status = ModelStatus.UNLOADED
        self.__requested_action = ModelAction.NONE
        self.__requested_action_lock = threading.Lock()

    @property
    def requested_action(self):
        with self.__requested_action_lock:
            return self.__requested_action

    @requested_action.setter
    def requested_action(self, action):
        with self.__requested_action_lock:
            self.__requested_action = action

    def controlnet_handle_sd_state_changed_signal(self, _data=None):
        if self.__requested_action is ModelAction.NONE:
            return
        if self.__requested_action is ModelAction.CLEAR:
            self.clear_controlnet()
        elif self.__requested_action is ModelAction.APPLY_TO_PIPE:
            self.apply_controlnet_to_pipe()

    @property
    def __controlnet_ready(self):
        return self.__controlnet_model_status in (
            ModelStatus.READY, ModelStatus.LOADED
        ) and self.__controlnet_processor_status in (
            ModelStatus.READY, ModelStatus.LOADED
        )

    @property
    def controlnet_type(self):
        controlnet = self.sd_request.generator_settings.controlnet_image_settings.controlnet
        controlnet_item = self.controlnet_model_by_name(controlnet)
        controlnet_type = controlnet_item["name"]
        return controlnet_type

    @property
    def controlnet_model(self):
        name = self.controlnet_type
        model = self.controlnet_model_by_name(name)
        if not model:
            raise ValueError(f"Unable to find controlnet model {name}")
        return model.path

    @property
    def controlnet_action_diffuser(self):
        if self.sd_request.is_txt2img:
            return StableDiffusionControlNetPipeline
        elif self.sd_request.is_img2img:
            return StableDiffusionControlNetImg2ImgPipeline
        elif self.sd_request.is_outpaint:
            return StableDiffusionControlNetInpaintPipeline
        else:
            raise ValueError(
                f"Invalid action {self.sd_request.section} unable to get controlnet action diffuser")

    @property
    def controlnet_image(self):
        if self.settings["controlnet_enabled"] and (
                self._controlnet_image is None or
                self.sd_mode in RELOAD_CONTROLNET_IMAGE_CONSTS
        ):
            self._controlnet_image = self.__preprocess_for_controlnet(self.sd_request.drawing_pad_image)
        return self._controlnet_image

    @property
    def controlnet_model(self):
        controlnet_name = self.settings["generator_settings"]["controlnet_image_settings"]["controlnet"]
        controlnet_model = self.controlnet_model_by_name(controlnet_name)
        return controlnet_model

    @property
    def controlnet_path(self):
        controlnet_model = self.controlnet_model
        path = os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["base_path"],
                "art/models",
                self.settings["generator_settings"]["version"],
                "controlnet",
                controlnet_model["path"]
            )
        )
        return path

    def on_load_controlnet_signal(self, _message: dict=None):
        self.__load_controlnet()

    def on_unload_controlnet_signal(self, _message: dict=None):
        self.__unload_controlnet()

    def __stop_controlnet_queue_watcher(self):
        self.running = False
        self._controlnet_queue_watcher_thread.join()

    def get_controlnet_image(self) -> Image.Image:
        controlnet_image = self.controlnet_image
        if controlnet_image:
            self.emit_signal(
                SignalCode.SD_CONTROLNET_IMAGE_GENERATED_SIGNAL,
                {
                    "image": controlnet_image
                }
            )
        return controlnet_image

    def __load_controlnet(self):
        self.__load_controlnet_model()
        self.__load_controlnet_processor()
        self.apply_controlnet_to_pipe()

    def apply_controlnet_to_pipe(self):
        if self.pipe and self.__controlnet_ready:
            self.__apply_controlnet_to_pipe()
            self.__apply_controlnet_processor_to_pipe()
            self.__change_controlnet_model_status(ModelStatus.LOADED)
            self.requested_action = ModelAction.NONE
        else:
            self.requested_action = ModelAction.APPLY_TO_PIPE
            return

    def __load_controlnet_model(self):
        if self.__controlnet_model_status in (
            ModelStatus.LOADED, ModelStatus.READY, ModelStatus.LOADING
        ):
            return
        self.logger.debug(f"Loading controlnet {self.controlnet_type} to {self.device}")
        self.__change_controlnet_model_status(ModelStatus.LOADING)

        path = self.controlnet_path
        is_sd_xl = self.settings["generator_settings"]["version"] == StableDiffusionVersion.SDXL1_0.value

        if is_sd_xl:
            path = os.path.expanduser(
                os.path.join(
                    self.settings["path_settings"]["base_path"],
                    "art/models",
                    self.settings["generator_settings"]["version"],
                    "controlnet",
                    "diffusers/controlnet-canny-sdxl-1.0"
                )
            )

        try:
            params = dict(
                torch_dtype=self.data_type,
                local_files_only=True,
                device=self.device,
                use_safetensors=True,
                use_fp16=True
            )
            if is_sd_xl:
                params["variant"] = "fp16"
            self.controlnet = ControlNetModel.from_pretrained(path, **params)
            self.__change_controlnet_model_status(ModelStatus.READY)

        except Exception as e:
            self.logger.error(f"Error loading controlnet {e}")
            self.__change_controlnet_model_status(ModelStatus.FAILED)
            return None

    def __load_controlnet_processor(self):
        if self.__controlnet_processor_status in (
            ModelStatus.LOADED, ModelStatus.READY, ModelStatus.LOADING
        ):
            return

        self.logger.debug("Loading controlnet processor")

        self.__change_controlnet_processor_status(ModelStatus.LOADING)
        try:
            self.processor = Processor(self.controlnet_type)
            self.__change_controlnet_processor_status(ModelStatus.LOADED)
        except Exception as e:
            self.logger.error(e)
            self.__change_controlnet_processor_status(ModelStatus.FAILED)
        self.logger.debug("Processor loaded")

    def __preprocess_for_controlnet(self, image):
        if self.processor is not None:
            if image is not None:
                self.logger.debug("Controlnet: Processing image")
                try:
                    image = self.processor(image)
                except ValueError as e:
                    self.logger.error(f"Error processing image: {e}")
                    image = None

                if image is None:
                    image = image.resize((
                        self.settings["working_width"],
                        self.settings["working_height"]
                    ))
                return image
            else:
                self.logger.error("No image to process")
        else:
            self.logger.error("No controlnet processor found")

    def __unload_controlnet(self):
        self.clear_controlnet()

    def clear_controlnet(self):
        if self.current_state is not HandlerState.READY:
            self.requested_action = ModelAction.CLEAR
            return

        self.logger.debug("Clearing controlnet")
        self.__unload_controlnet_processor()
        self.__unload_controlnet_model()
        self.controlnet_loaded = False

    def __change_controlnet_model_status(self, status):
        self.__controlnet_model_status = status
        self.change_model_status(ModelType.CONTROLNET, status, self.controlnet_model["path"])

    def __change_controlnet_processor_status(self, status):
        self.__controlnet_processor_status = status
        self.change_model_status(ModelType.CONTROLNET_PROCESSOR, status, self.controlnet_type)

    def __unload_controlnet_model(self):
        self.__change_controlnet_model_status(ModelStatus.UNLOADED)
        self.controlnet = None
        if self.pipe:
            self.pipe.controlnet = None
        clear_memory()
        self.reset_applied_memory_settings()

    def __apply_controlnet_to_pipe(self):
        self.pipe.controlnet = self.controlnet

    def __apply_controlnet_processor_to_pipe(self):
        self.pipe.processor = self.processor
        self.__change_controlnet_processor_status(ModelStatus.LOADED)

    def __unload_controlnet_processor(self):
        self.processor = None
        if self.pipe:
            self.pipe.processor = None
        self.__change_controlnet_processor_status(ModelStatus.UNLOADED)
        clear_memory()
