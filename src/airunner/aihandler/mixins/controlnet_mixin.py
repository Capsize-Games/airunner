import os

from PIL import Image
from controlnet_aux.processor import Processor
from diffusers import StableDiffusionControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, \
    StableDiffusionControlNetInpaintPipeline, ControlNetModel
from airunner.enums import SignalCode, SDMode, ModelType, ModelStatus
from airunner.utils.clear_memory import clear_memory


RELOAD_CONTROLNET_IMAGE_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class ControlnetHandlerMixin:
    def __init__(self, *args, **kwargs):
        controlnet = self.settings["generator_settings"]["controlnet_image_settings"]["controlnet"]
        controlnet_item = self.controlnet_model_by_name(controlnet)
        self.controlnet = None
        self._controlnet_image = None
        self.controlnet_type = ""
        self.controlnet_guess_mode = None
        self.current_load_controlnet = False
        self.current_controlnet_type = None
        self.controlnet_loaded = False
        self.downloading_controlnet = False
        self.controlnet_type = controlnet_item["name"]
        signals = {
            SignalCode.CONTROLNET_LOAD_SIGNAL: self.on_load_controlnet_signal,
            SignalCode.CONTROLNET_UNLOAD_SIGNAL: self.on_unload_controlnet_signal,
        }
        for code, handler in signals.items():
            self.register(code, handler)

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
                self.do_load or
                self.sd_mode in RELOAD_CONTROLNET_IMAGE_CONSTS
        ):
            self.logger.debug("Getting controlnet image")
            self._controlnet_image = self.preprocess_for_controlnet(self.sd_request.drawing_pad_image)
        return self._controlnet_image

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

    def on_load_controlnet_signal(self, _message: dict):
        self.controlnet = self.load_controlnet()

    def on_unload_controlnet_signal(self, _message: dict):
        self.unload_controlnet()

    def load_controlnet_from_ckpt(self, pipeline):
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
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET,
                    "status": ModelStatus.LOADED,
                    "path": short_path
                }
            )
            return pipeline
        except Exception as e:
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET,
                    "status": ModelStatus.FAILED,
                    "path": short_path
                }
            )

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

    def load_controlnet(self):
        self.logger.debug(f"Loading controlnet {self.controlnet_type}")
        path = self.controlnet_path
        short_path = self.controlnet_model["path"]
        self.current_controlnet_type = self.controlnet_type
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.CONTROLNET,
                "status": ModelStatus.LOADING,
                "path": short_path
            }
        )
        try:
            controlnet = ControlNetModel.from_pretrained(
                path,
                torch_dtype=self.data_type,
                local_files_only=True,
                device_map="auto"
            )
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET,
                    "status": ModelStatus.LOADED,
                    "path": short_path
                }
            )
            return controlnet
        except Exception as e:
            self.logger.error(f"Error loading controlnet {e}")
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET,
                    "status": ModelStatus.FAILED,
                    "path": short_path
                }
            )
            return None
    def preprocess_for_controlnet(self, image):
        self.initialize_controlnet_processor()

        if self.processor is not None and image is not None:
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
        self.logger.error("No controlnet processor found")

    def initialize_controlnet_processor(self):
        controlnet = self.sd_request.generator_settings.controlnet_image_settings.controlnet
        controlnet_item = self.controlnet_model_by_name(controlnet)
        controlnet_type = controlnet_item["name"]
        if self.current_controlnet_type != controlnet_type or not self.processor:
            self.logger.debug("Loading controlnet processor " + controlnet_type)
            self.current_controlnet_type = controlnet_type
            self.load_controlnet_processor()

    def load_controlnet_processor(self):
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.CONTROLNET_PROCESSOR,
                "status": ModelStatus.LOADING,
                "path": self.current_controlnet_type
            }
        )
        try:
            self.processor = Processor(
                self.current_controlnet_type,
                local_files_only=True,
            )
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET_PROCESSOR,
                    "status": ModelStatus.LOADED,
                    "path": self.current_controlnet_type
                }
            )
        except Exception as e:
            self.logger.error(e)
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.CONTROLNET_PROCESSOR,
                    "status": ModelStatus.FAILED,
                    "path": self.current_controlnet_type
                }
            )
        self.logger.debug("Processor loaded")

    @property
    def do_load_controlnet(self) -> bool:
        return (
                (not self.controlnet_loaded and self.settings["controlnet_enabled"]) or
                (self.controlnet_loaded and self.settings["controlnet_enabled"])
        )

    @property
    def do_unload_controlnet(self) -> bool:
        return not self.settings["controlnet_enabled"] and (self.controlnet_loaded)

    def unload_controlnet(self):
        if self.controlnet:
            self.logger.debug("Unloading controlnet")
            self.clear_controlnet()

    def clear_controlnet(self):
        self.logger.debug("Clearing controlnet")
        self.controlnet = None
        self.processor = None
        if self.pipe:
            self.pipe.controlnet = None
        clear_memory()
        self.reset_applied_memory_settings()
        self.controlnet_loaded = False
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.CONTROLNET,
                "status": ModelStatus.UNLOADED,
                "path": ""
            }
        )
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.CONTROLNET_PROCESSOR,
                "status": ModelStatus.UNLOADED,
                "path": ""
            }
        )