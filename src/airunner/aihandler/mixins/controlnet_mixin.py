import os
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
    ModelStatus
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
        self.controlnet_guess_mode = None
        self.current_load_controlnet = False
        self.controlnet_loaded = False
        self.downloading_controlnet = False
        signals = {
            SignalCode.CONTROLNET_LOAD_SIGNAL: self.on_load_controlnet_signal,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL: self.on_unload_controlnet_signal,
            SignalCode.CONTROLNET_LOAD_MODEL_SIGNAL: self.on_controlnet_load_model_signal,
            SignalCode.CONTROLNET_UNLOAD_MODEL_SIGNAL: self.on_unload_controlnet_model_signal,
            SignalCode.CONTROLNET_PROCESSOR_LOAD_SIGNAL: self.on_controlnet_load_processor_signal,
            SignalCode.CONTROLNET_PROCESSOR_UNLOAD_SIGNAL: self.on_controlnet_unload_processor_signal,
        }
        for code, handler in signals.items():
            self.register(code, handler)

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
                f"Invalid action {self.sd_request.generator_settings.section} unable to get controlnet action diffuser")

    @property
    def controlnet_image(self):
        if (
                self._controlnet_image is None or
                self.sd_mode in RELOAD_CONTROLNET_IMAGE_CONSTS
        ):
            self.logger.debug("Getting controlnet image")
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
                self.settings["path_settings"]["controlnet_model_path"],
                controlnet_model["path"]
            )
        )
        return path

    def on_controlnet_load_model_signal(self, message: dict):
        self.__load_controlnet_model()

    def on_controlnet_unload_model_signal(self, message: dict):
        self.__unload_controlnet_model()

    def on_controlnet_load_processor_signal(self, message: dict):
        self.__load_controlnet_processor()

    def on_controlnet_unload_processor_signal(self, message: dict):
        self.__unload_controlnet_processor()

    def on_load_controlnet_signal(self, _message: dict):
        self.load_controlnet()

    def on_unload_controlnet_signal(self, _message: dict):
        self.__unload_controlnet()

    def on_unload_controlnet_model_signal(self, _message: dict):
        self.__unload_controlnet_model()

    def get_controlnet_image(self) -> Image.Image:
        controlnet_image = self.controlnet_image
        if controlnet_image:
            self.emit_signal(
                SignalCode.SD_CONTROLNET_IMAGE_GENERATED_SIGNAL,
                {
                    "image": controlnet_image
                }
            )
        else:
            self.logger.info("Controlnet image not generated")
        return controlnet_image

    def load_controlnet(self):
        self.__load_controlnet_model()
        self.__load_controlnet_processor()
        self.make_controlnet_memory_efficient()

    def apply_controlnet_to_pipe(self):
        self.__apply_controlnet_to_pipe()
        self.__apply_controlnet_processor_to_pipe()

    def remove_controlnet_from_pipe(self):
        self.__remove_controlnet_from_pipe()

    def __load_controlnet_model(self):
        self.logger.debug(f"Loading controlnet {self.controlnet_type} to {self.device}")

        path = self.controlnet_path
        short_path = self.controlnet_model["path"]
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING, short_path)
        try:
            self.controlnet = ControlNetModel.from_pretrained(
                path,
                torch_dtype=self.data_type,
                local_files_only=True,
                device=self.device,
            )
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.READY if not self.pipe else ModelStatus.LOADED, short_path)
            self.swap_pipeline()
        except Exception as e:
            self.logger.error(f"Error loading controlnet {e}")
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED, short_path)
            return None

    def __load_controlnet_processor(self):
        self.logger.debug("Loading controlnet processor")

        self.change_model_status(ModelType.CONTROLNET_PROCESSOR, ModelStatus.LOADING, self.controlnet_type)
        try:
            self.processor = Processor(
                self.controlnet_type
            )
            self.change_model_status(ModelType.CONTROLNET_PROCESSOR, ModelStatus.LOADED, self.controlnet_type)
        except Exception as e:
            self.logger.error(e)
            self.change_model_status(ModelType.CONTROLNET_PROCESSOR, ModelStatus.FAILED, self.controlnet_type)
        self.logger.debug("Processor loaded")

    def __load_controlnet_from_ckpt(self, pipeline):
        self.logger.debug("Loading controlnet from ckpt")
        short_path = self.controlnet_model["path"]
        try:
            pipeline = self.controlnet_action_diffuser(
                vae=pipeline.vae,
                text_encoder=pipeline.text_encoder,
                tokenizer=pipeline.tokenizer,
                unet=pipeline.unet,
                controlnet=self.controlnet,
                scheduler=pipeline.scheduler,
                safety_checker=self.safety_checker,
                feature_extractor=self.feature_extractor
            )
            self.controlnet_loaded = True
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED, short_path)
            return pipeline
        except Exception as e:
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED, short_path)

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
        self.logger.debug("Unloading controlnet")
        self.__clear_controlnet()

    def __clear_controlnet(self):
        self.logger.debug("Clearing controlnet")
        self.__unload_controlnet_model()
        self.__unload_controlnet_processor()
        self.controlnet_loaded = False

    def __unload_controlnet_model(self):
        self.controlnet = None
        if self.pipe:
            self.pipe.controlnet = None
        clear_memory()
        self.reset_applied_memory_settings()
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.UNLOADED, "")
        self.swap_pipeline()

    def __unload_controlnet_processor(self):
        self.processor = None
        clear_memory()
        self.change_model_status(ModelType.CONTROLNET_PROCESSOR, ModelStatus.UNLOADED, "")

    def __apply_controlnet_to_pipe(self):
        if self.pipe and hasattr(self.pipe, "controlnet") and self.pipe.controlnet is not None:
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED, self.controlnet_model["path"])

    def __apply_controlnet_processor_to_pipe(self):
        if self.pipe and hasattr(self.pipe, "processor") and self.pipe.processor is not None:
            self.change_model_status(ModelType.CONTROLNET_PROCESSOR, ModelStatus.LOADED, self.controlnet_type)

    def __remove_controlnet_from_pipe(self):
        if self.pipe and hasattr(self.pipe, "controlnet") and self.pipe.controlnet is not None:
            status = ModelStatus.READY
            path = self.controlnet_model["path"]
        else:
            status = ModelStatus.UNLOADED
            path = ""
        self.swap_pipeline()
        self.change_model_status(ModelType.CONTROLNET, status, path)
