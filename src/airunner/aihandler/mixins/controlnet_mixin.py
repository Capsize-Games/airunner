import os
import threading
from controlnet_aux.processor import Processor
from diffusers.models.controlnet import ControlNetModel
from airunner.enums import (
    SDMode,
    ModelType,
    ModelStatus,
    HandlerState,
    ModelAction
)

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
        self.__requested_action = ModelAction.NONE
        self.__requested_action_lock = threading.Lock()

    def controlnet_handle_sd_state_changed_signal(self):
        if self.__requested_action is ModelAction.NONE:
            return
        if self.__requested_action is ModelAction.CLEAR:
            self.unload_controlnet()
        elif self.__requested_action is ModelAction.APPLY_TO_PIPE:
            self.apply_controlnet_to_pipe()

    @property
    def __controlnet_ready(self):
        return self.__controlnet_model_status in (
            ModelStatus.READY,
            ModelStatus.LOADED
        )

    @property
    def controlnet_type(self):
        controlnet = self.controlnet_image_settings.controlnet
        controlnet_item = self.controlnet_model_by_name(controlnet)
        controlnet_type = controlnet_item.name
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
        from diffusers.pipelines.controlnet.pipeline_controlnet import StableDiffusionControlNetPipeline
        from diffusers.pipelines.controlnet.pipeline_controlnet_img2img import StableDiffusionControlNetImg2ImgPipeline
        from diffusers.pipelines.controlnet.pipeline_controlnet_inpaint import StableDiffusionControlNetInpaintPipeline
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
        if self.application_settings.controlnet_enabled and (
            self._controlnet_image is None #or
            #self.sd_mode in RELOAD_CONTROLNET_IMAGE_CONSTS
        ):
            self._controlnet_image = self.__preprocess_for_controlnet(self.sd_request.drawing_pad_image)
        return self._controlnet_image

    @property
    def controlnet_model(self):
        controlnet_name = self.controlnet_image_settings.controlnet
        controlnet_model = self.controlnet_model_by_name(controlnet_name)
        return controlnet_model

    @property
    def controlnet_path(self):
        controlnet_model = self.controlnet_model
        version: str = self.generator_settings.version
        path: str = "diffusers/controlnet-canny-sdxl-1.0-small" if self.is_sd_xl else controlnet_model.path
        return os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "art/models",
            version,
            "controlnet",
            path
        ))

    def load_controlnet(self):
        if self.__controlnet_model_status in (
            ModelStatus.LOADED,
            ModelStatus.READY,
            ModelStatus.LOADING
        ):
            return
        self.logger.debug(f"Loading controlnet {self.controlnet_type} to {self.device}")
        self.__change_controlnet_model_status(ModelStatus.LOADING)
        try:
            params = dict(
                torch_dtype=self.data_type,
                local_files_only=True,
                device=self.device,
                use_safetensors=True,
                use_fp16=True
            )
            if self.is_sd_xl:
                params["variant"] = "fp16"
            self.controlnet = ControlNetModel.from_pretrained(self.controlnet_path, **params)
        except Exception as e:
            self.logger.error(f"Error loading controlnet {e}")
            self.__change_controlnet_model_status(ModelStatus.FAILED)
            return None
        self.logger.debug("Loading controlnet processor")
        try:
            self.processor = Processor(self.controlnet_type)
        except Exception as e:
            self.logger.error(e)
            self.__change_controlnet_model_status(ModelStatus.FAILED)
            return None
        self.logger.debug("Processor loaded")
        self.apply_controlnet_to_pipe()
        self.__change_controlnet_model_status(ModelStatus.LOADED)

    def unload_controlnet(self):
        if self.current_state is HandlerState.LOADING:
            self.__requested_action = ModelAction.CLEAR
            return
        self.logger.debug("Clearing controlnet")
        self.__change_controlnet_model_status(ModelStatus.LOADING)
        if self.pipe and hasattr(self.pipe, "controlnet"):
            del self.pipe.controlnet
            self.pipe.controlnet = None
        if self.pipe and hasattr(self.pipe, "processor"):
            del self.pipe.processor
            self.pipe.processor = None
        del self.controlnet
        del self.processor
        self.controlnet = None
        self.processor = None
        self.clear_memory()
        self.__change_controlnet_model_status(ModelStatus.UNLOADED)

        self.controlnet_loaded = False

    def apply_controlnet_to_pipe(self):
        if self.pipe and self.__controlnet_ready:
            self.pipe.controlnet = self.controlnet
            self.pipe.processor = self.processor
            self.__change_controlnet_model_status(ModelStatus.LOADED)
            self.__requested_action = ModelAction.NONE
        else:
            self.__requested_action = ModelAction.APPLY_TO_PIPE
            return

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
                        self.application_settings.working_width,
                        self.application_settings.working_height
                    ))
                return image
            else:
                self.logger.error("No image to process")
        else:
            self.logger.error("No controlnet processor found")

    def __change_controlnet_model_status(self, status):
        self.__controlnet_model_status = status
        self.change_model_status(ModelType.CONTROLNET, status, self.controlnet_model.path)
        if status is ModelStatus.LOADED:
            self.make_controlnet_memory_efficient()
        elif status in (ModelStatus.UNLOADED, ModelStatus.FAILED):
            self.clear_memory()
