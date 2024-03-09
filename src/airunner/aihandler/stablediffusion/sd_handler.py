import io
import base64
import traceback

import numpy as np
from PyQt6.QtWidgets import QApplication
from pytorch_lightning import seed_everything
from typing import List
import requests
import torch
from PIL import Image, ImageDraw, ImageFont
from controlnet_aux.processor import Processor
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import download_from_original_stable_diffusion_ckpt
from diffusers.utils.torch_utils import randn_tensor
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
    AutoPipelineForText2Image,
    StableDiffusionDepth2ImgPipeline,
    AutoPipelineForInpainting,
    StableDiffusionInstructPix2PixPipeline,
    ControlNetModel,
    StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline
)
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from diffusers import (
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline
)
from transformers import AutoFeatureExtractor
from airunner.aihandler.base_handler import BaseHandler
from airunner.aihandler.stablediffusion.sd_request import SDRequest
from airunner.enums import (
    FilterType,
    HandlerType,
    SignalCode,
    Scheduler,
    SDMode,
    StableDiffusionVersion,
    Controlnet,
    EngineResponseCode
)
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.settings import AIRUNNER_ENVIRONMENT
from airunner.service_locator import ServiceLocator
from airunner.settings import CONFIG_FILES
from airunner.windows.main.lora_mixin import LoraMixin as LoraDataMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.utils import clear_memory, random_seed, create_worker, get_torch_device

#from airunner.scripts.realesrgan.main import RealESRGAN
from airunner.workers.worker import Worker

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)
RELOAD_CONTROLNET_IMAGE_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class LatentsWorker(Worker):
    def __init__(self, prefix="LatentsWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.HANDLE_LATENTS_SIGNAL, self.on_handle_latents_signal)

    def on_handle_latents_signal(self, data: dict):
        latents = data.get("latents")
        sd_request = data.get("sd_request")
        # convert latents to PIL image
        latents = latents[0].detach().cpu().numpy().astype(np.uint8)  # convert to uint8
        latents = latents.transpose(1, 2, 0)
        image = Image.fromarray(latents)
        image = image.resize((self.settings["working_width"], self.settings["working_height"]))
        image = image.convert("RGBA")
        self.emit(
            SignalCode.SD_IMAGE_GENERATED_SIGNAL,
            {
                "images": [image],
                "action": sd_request.generator_settings.section,
                "outpaint_box_rect": sd_request.active_rect,
            }
        )


class SDHandler(
    BaseHandler,
    MergeMixin,
    LoraMixin,
    MemoryEfficientMixin,
    EmbeddingMixin,
    CompelMixin,
    SchedulerMixin,
    # Data Mixins
    LoraDataMixin,
    EmbeddingDataMixin,
    PipelineMixin,
    ControlnetModelMixin,
    AIModelMixin,
):
    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LoraDataMixin.__init__(self)
        EmbeddingDataMixin.__init__(self)
        PipelineMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        LoraMixin.__init__(self)
        CompelMixin.__init__(self)
        SchedulerMixin.__init__(self)
        self.logger.debug("Loading Stable Diffusion model runner...")
        self.safety_checker_model = self.models_by_pipeline_action("safety_checker")[0]
        self.text_encoder_model = self.models_by_pipeline_action("text_encoder")[0]
        self.inpaint_vae_model = self.models_by_pipeline_action("inpaint_vae")[0]
        self.handler_type = HandlerType.DIFFUSER
        self._previous_model: str = ""
        self.cross_attention_kwargs_scale: float = 1.0
        self._initialized: bool = False
        self._reload_model: bool = False
        self.current_model_branch = None
        self.state = None
        self._local_files_only = True
        self.lora_loaded = False
        self.loaded_lora = []
        self._settings = None
        self._action = None
        self.embeds_loaded = False
        self._compel_proc = None
        self.current_prompt = None
        self.current_negative_prompt = None
        self._model = None
        self.requested_data = None
        self._allow_online_mode = None
        self.current_load_controlnet = False
        self.processor = None
        self.current_controlnet_type = None
        self.controlnet_loaded = False
        self.attempt_download = False
        self.latents_set = False
        self.downloading_controlnet = False
        self._controlnet_image = None
        self._latents = None
        self.txt2img = None
        self.img2img = None
        self.pix2pix = None
        self.outpaint = None
        self.depth2img = None
        self.tokenizer = None
        self._safety_checker = None
        self._controlnet = None
        self.options: dict = {}
        self.current_model: str = ""
        self.seed: int = 42
        self.batch_size: int = 1
        self.use_prompt_converter: bool = True
        self.depth_map = None
        self.model_data = None
        self.model_version: str = ""
        self.use_tiled_vae: bool = False
        self.use_accelerated_transformers: bool = False
        self.use_torch_compile: bool = False
        self.is_sd_xl: bool = False
        self.is_sd_xl_turbo: bool = False
        self.is_turbo: bool = False
        self.use_compel: bool = False
        self.controlnet_guess_mode = None
        self.filters = None
        self.original_model_data = None
        self.denoise_strength = None
        self.face_enhance: bool = False
        self.allow_online_mode: bool = False
        self.controlnet_type: str = ""
        self.initialized: bool = False
        self.reload_model: bool = False
        self.local_files_only: bool = False
        self.extra_args = None
        self.do_set_seed: bool = True
        self._controlnet_image = None
        self.is_dev_env = AIRUNNER_ENVIRONMENT == "dev"
        self.latents = None
        self.sd_mode = None
        self.safety_checker = None
        self.feature_extractor = None
        self.reload_prompts = False
        self.moved_to_cpu = False
        self.data = {
            "action": "txt2img",
        }
        signals = {
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_stablediffusion_signal,
            SignalCode.SD_MOVE_TO_CPU_SIGNAL: self.on_move_to_cpu,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
        }
        for code, handler in signals.items():
            self.register(code, handler)

        torch.backends.cuda.matmul.allow_tf32 = self.settings["memory_settings"]["use_tf32"]
        self.controlnet_type = "canny"
        self.sd_mode = SDMode.DRAWING
        self.loaded = False
        self.loading = False
        self.sd_request = None
        self.sd_request = SDRequest(model_data=self.model)
        self.sd_request.parent = self
        self.running = True
        self.do_generate = False
        self._generator = None
        self.do_interrupt = False
        self.latents_worker = create_worker(LatentsWorker)


    def on_interrupt_process_signal(self):
        self.do_interrupt = True

    @property
    def device(self):
        return get_torch_device()

    @property
    def do_load(self):
        return (
            self.sd_mode not in SKIP_RELOAD_CONSTS or
            not self.initialized
        )

    @property
    def controlnet_model(self):
        name = self.controlnet_type
        model = self.controlnet_model_by_name(name)
        if not model:
            raise ValueError(f"Unable to find controlnet model {name}")
        return model.path

    @property
    def allow_online_when_missing_files(self) -> bool:
        """
        This settings prevents the application from going online when a file is missing.
        :return:
        """
        if self._allow_online_mode is None:
            self._allow_online_mode = self.allow_online_mode
        return self._allow_online_mode

    @property
    def cuda_error_message(self) -> str:
        return (
            f"VRAM too low for "
            f"{self.settings['working_width']}x{self.settings['working_height']} "
            f"resolution. Potential solutions: try again, use a different model, "
            f"restart the application, use a smaller size, upgrade your GPU."
        )

    @property
    def is_pipe_loaded(self) -> bool:
        if self.sd_request.is_txt2img:
            return self.txt2img is not None
        elif self.sd_request.is_img2img:
            return self.img2img is not None
        elif self.sd_request.is_pix2pix:
            return self.pix2pix is not None
        elif self.sd_request.is_outpaint:
            return self.outpaint is not None
        elif self.sd_request.is_depth2img:
            return self.depth2img is not None

    @property
    def pipe(self):
        try:
            if self.sd_request.is_txt2img:
                return self.txt2img
            elif self.sd_request.is_img2img:
                return self.img2img
            elif self.sd_request.is_outpaint:
                return self.outpaint
            elif self.sd_request.is_depth2img:
                return self.depth2img
            elif self.sd_request.is_pix2pix:
                return self.pix2pix
            else:
                self.logger.warning(f"Invalid action unable to get pipe")
                return None
        except Exception as e:
            self.logger.error(f"Error getting pipe {e}")
            return None

    @pipe.setter
    def pipe(self, value):
        if self.sd_request.is_txt2img:
            self.txt2img = value
        elif self.sd_request.is_img2img:
            self.img2img = value
        elif self.sd_request.is_outpaint:
            self.outpaint = value
        elif self.sd_request.is_depth2img:
            self.depth2img = value
        elif self.sd_request.is_pix2pix:
            self.pix2pix = value

    @property
    def cuda_is_available(self) -> bool:
        if self.settings["memory_settings"]["enable_model_cpu_offload"]:
            return False
        return torch.cuda.is_available()

    @property
    def model(self):
        name = self.settings["generator_settings"]["model"]
        model = ServiceLocator.get("ai_model_by_name")(name)
        return model

    @property
    def model_path(self):
        return self.model["path"]

    @property
    def is_ckpt_model(self) -> bool:
        return self.is_ckpt_file(self.model_path)

    @property
    def is_safetensors(self) -> bool:
        return self.is_safetensor_file(self.model_path)

    @property
    def is_single_file(self) -> bool:
        return self.is_ckpt_model or self.is_safetensors

    @property
    def data_type(self):
        if self.sd_request.memory_settings.use_enable_sequential_cpu_offload:
            return torch.float32
        elif self.sd_request.memory_settings.enable_model_cpu_offload:
            return torch.float16
        data_type = torch.float16 if self.cuda_is_available else torch.float
        return data_type

    @property
    def has_internet_connection(self) -> bool:
        try:
            _response = requests.get('https://huggingface.co/')
            return True
        except requests.ConnectionError:
            return False

    @property
    def controlnet_action_diffuser(self):
        if self.sd_request.is_txt2img:
            return StableDiffusionControlNetPipeline
        elif self.sd_request.is_img2img:
            return StableDiffusionControlNetImg2ImgPipeline
        elif self.sd_request.is_outpaint:
            return StableDiffusionControlNetInpaintPipeline
        else:
            raise ValueError(f"Invalid action {self.sd_request.generator_settings.section} unable to get controlnet action diffuser")

    @property
    def controlnet_image(self):
        if (
            self._controlnet_image is None or
            self.do_load or
            self.sd_mode in RELOAD_CONTROLNET_IMAGE_CONSTS
        ):
            self.logger.debug("Getting controlnet image")
            controlnet_image = self.preprocess_for_controlnet(self.sd_request.drawing_pad_image)
            self._controlnet_image = controlnet_image
            # settings = self.settings
            # settings["controlnet_image_settings"]["controlnet_image_base64"] = controlnet_image
            # self.settings = settings
        # self.emit(SignalCode.CONTROLNET_IMAGE_GENERATED_SIGNAL, {
        #     'image': self._controlnet_image,
        #     'data': {
        #         'controlnet_image': self._controlnet_image
        #     }
        # })
        return self._controlnet_image

    def preprocess_for_controlnet(self, image):
        if image is None:
            return

        if self.current_controlnet_type != self.controlnet_type or not self.processor:
            self.logger.debug("Loading controlnet processor " + self.controlnet_type)
            self.current_controlnet_type = self.controlnet_type
            self.processor = Processor(self.controlnet_type)
        if self.processor:
            self.logger.debug("Controlnet: Processing image")
            image = self.processor(image)
            image = image.resize((self.settings["working_width"], self.settings["working_height"]))
            return image
        self.logger.error("No controlnet processor found")

    @property
    def do_load_controlnet(self) -> bool:
        return (
            (not self.controlnet_loaded and self.settings["generator_settings"]["enable_controlnet"]) or
            (self.controlnet_loaded and self.settings["generator_settings"]["enable_controlnet"])
        )

    @property
    def do_unload_controlnet(self) -> bool:
        return not self.settings["generator_settings"]["enable_controlnet"] and (self.controlnet_loaded)

    @property
    def do_reuse_pipeline(self) -> bool:
        return (
            (self.sd_request.is_txt2img and self.txt2img is None and self.img2img) or
            (self.sd_request.is_img2img and self.img2img is None and self.txt2img) or
            (
                (
                    (self.sd_request.is_txt2img and self.txt2img) or
                    (self.sd_request.is_img2img and self.img2img)
                ) and
                (
                    self.do_load_controlnet or self.do_unload_controlnet
                )
            )
        )

    @property
    def do_load_compel(self) -> bool:
        return self.pipe and (
            (
                self.use_compel and (self.prompt_embeds is None or self.negative_prompt_embeds is None)
            ) or
            self.reload_prompts or
            self.do_load
        )

    @staticmethod
    def apply_filters(image, filters):
        for image_filter in filters:
            filter_type = FilterType(image_filter["filter_name"])
            if filter_type is FilterType.PIXEL_ART:
                scale = 4
                colors = 24
                for option in image_filter["options"]:
                    option_name = option["name"]
                    val = option["value"]
                    if option_name == "scale":
                        scale = val
                    elif option_name == "colors":
                        colors = val
                width = image.width
                height = image.height
                image = image.quantize(colors)
                image = image.resize((int(width / scale), int(height / scale)), resample=Image.NEAREST)
                image = image.resize((width, height), resample=Image.NEAREST)
        return image

    @staticmethod
    def is_ckpt_file(model) -> bool:
        if not model:
            raise ValueError("ckpt path is empty")
        return model.endswith(".ckpt")

    @staticmethod
    def is_safetensor_file(model) -> bool:
        if not model:
            raise ValueError("safetensors path is empty")
        return model.endswith(".safetensors")

    @staticmethod
    def is_pytorch_error(e) -> bool:
        return "PYTORCH_CUDA_ALLOC_CONF" in str(e)

    def on_do_generate_signal(self):
        self.do_generate = True

    def run(self):
        self.do_set_seed = (
            not self.initialized or
            (
                self.sd_request and
                self.sd_request.generator_settings and
                self.settings is not None and
                self.sd_request.generator_settings.seed != self.settings["generator_settings"]["seed"]
            )
        )

        cur_prompt = self.sd_request.generator_settings.prompt
        cur_neg_prompt = self.sd_request.generator_settings.negative_prompt
        if (
            self.settings["generator_settings"]["prompt"] != cur_prompt or
            self.settings["generator_settings"]["negative_prompt"] != cur_neg_prompt
        ):
            self.latents = None
            self.latents_set = False
            self.reload_prompts = True

        response = None
        if not self.loaded and self.loading:
            if self.initialized and self.pipe:
                self.loaded = True
                self.loading = False
        elif not self.loaded and not self.loading:
            self.loading = True
            response = self.generator_sample()
            self.initialized = True
        elif self.loaded and not self.loading and self.do_generate:
            import traceback
            traceback.print_stack()
            self.do_interrupt = False
            response = self.generator_sample()
            # Set random seed if random seed is true
            if self.settings and self.settings["generator_settings"]["random_seed"]:
                seed = self.settings["generator_settings"]["seed"]
                while seed == self.sd_request.generator_settings.seed:
                    seed = random_seed()
                settings = self.settings
                settings["generator_settings"]["seed"] = seed
                self.settings = settings

        if response is not None:
            nsfw_content_detected = response["nsfw_content_detected"]

            if nsfw_content_detected:
                self.emit(
                    SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL,
                    response
                )
            else:
                response["action"] = self.sd_request.generator_settings.section
                response["outpaint_box_rect"] = self.sd_request.active_rect

                self.emit(SignalCode.ENGINE_DO_RESPONSE_SIGNAL, {
                    'code': EngineResponseCode.IMAGE_GENERATED,
                    'message': response
                })

    def has_pipe(self) -> bool:
        return self.pipe is not None

    def pipe_on_cpu(self) -> bool:
        return self.pipe.device.type == "cpu"

    def is_pipe_on_cpu(self) -> bool:
        return self.has_pipe() and self.pipe_on_cpu()

    def on_move_to_cpu(self, message: dict = None):
        message = message or {}
        if not self.is_pipe_on_cpu() and self.has_pipe():
            self.logger.debug("Moving model to CPU")
            self.pipe = self.pipe.to("cpu")
            self.moved_to_cpu = True
            clear_memory()
        if "callback" in message:
            message["callback"]()

    def initialize(self):
        if (
            self.initialized is False or
            self.reload_model is True or
            self.pipe is None
        ):
            self.send_model_loading_message(self.current_model)
            if self.reload_model:
                self.reset_applied_memory_settings()
            if not self.sd_request.is_upscale and self.do_load or not self.initialized:
                self.load_model()
            self.reload_model = False

    def controlnet(self):
        if (
            self._controlnet is None or
            self.current_controlnet_type != self.controlnet_type
        ):
            self._controlnet = self.load_controlnet()
        return self._controlnet

    def generator(self, device=None, seed=None):
        if self._generator is None:
            device = self.device if not device else device
            if seed is None:
                seed = int(self.settings["generator_settings"]["seed"])
            self._generator = torch.Generator(device=device).manual_seed(seed)
        return self._generator

    def send_error(self, message):
        self.emit(SignalCode.LOG_ERROR_SIGNAL, message)

    def error_handler(self, error):
        message = str(error)
        if (
            "got an unexpected keyword argument 'image'" in message and
            self.sd_request.generator_settings.section in ["outpaint", "pix2pix", "depth2img"]
        ):
            message = f"This model does not support {self.sd_request.generator_settings.section}"
        traceback.print_exc()
        self.logger.error(error)
        self.emit(SignalCode.LOG_ERROR_SIGNAL, message)

    def initialize_safety_checker(self, local_files_only=True):
        self.logger.debug(f"Initializing safety checker with {self.safety_checker_model}")
        try:
            return StableDiffusionSafetyChecker.from_pretrained(
                self.safety_checker_model["path"],
                local_files_only=local_files_only,
                torch_dtype=self.data_type
            )
        except OSError:
            if local_files_only:
                return self.initialize_safety_checker(local_files_only=False)
            else:
                self.send_error("Unable to load safety checker")
                return None

    def initialize_feature_extractor(self, local_files_only=True):
        try:
            return AutoFeatureExtractor.from_pretrained(
                self.safety_checker_model["path"],
                local_files_only=local_files_only,
                torch_dtype=self.data_type
            )
        except OSError:
            if local_files_only:
                return self.initialize_feature_extractor(local_files_only=False)
            else:
                self.send_error("Unable to load feature extractor")
                return None

    def load_safety_checker(self):
        if self.safety_checker is None and "path" in self.safety_checker_model:
            self.safety_checker = self.initialize_safety_checker()

        if self.feature_extractor is None and "path" in self.safety_checker_model:
            self.feature_extractor = self.initialize_feature_extractor()

    def do_sample(self):
        self.emit(SignalCode.LOG_STATUS_SIGNAL, "Generating image")
        self.emit(SignalCode.VISION_CAPTURE_LOCK_SIGNAL)
        try:
            output = self.call_pipe()
        except Exception as e:
            error_message = str(e)
            if self.is_pytorch_error(e):
                error_message = self.cuda_error_message
            elif "Scheduler.step() got an unexpected keyword argument" in str(e):
                error_message = "Invalid scheduler"
                self.clear_scheduler()
            self.log_error(error_message)
            output = None
        return self.process_sample(output)

    def process_sample(self, output):
        nsfw_content_detected = None
        images = None
        if output:
            try:
                images = output.images
            except AttributeError:
                self.logger.error("Unable to get images from output")
            if self.sd_request.action_has_safety_checker:
                try:
                    nsfw_content_detected = output.nsfw_content_detected
                except AttributeError:
                    self.logger.error("Unable to get nsfw_content_detected from output")
        self.emit(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL)
        return images, nsfw_content_detected

    def generate_latents(self):
        self.logger.debug("Generating latents")

        width_scale = self.settings["working_width"] / self.settings["working_width"]
        height_scale = self.settings["working_height"] / self.settings["working_height"]
        latent_width = int(self.pipe.unet.config.sample_size * width_scale)
        latent_height = int(self.pipe.unet.config.sample_size * height_scale)

        batch_size = self.batch_size
        return randn_tensor(
            (
                batch_size,
                self.pipe.unet.config.in_channels,
                latent_height,
                latent_width,
            ),
            device=torch.device(self.device),
            dtype=self.data_type,
            generator=self.generator(torch.device(self.device)),
        )

    def call_pipe(self):
        """
        Generate an image using the pipe
        :return:
        """
        if self.pipe:
            try:
                return self.pipe(
                    **self.data,
                    callback_on_step_end=self.interrupt_callback
                )
            except Exception as e:
                if str(e) == "Interrupted":
                    self.final_callback()
                    return
                self.error_handler("Something went wrong during generation")
                return

    def interrupt_callback(self, pipe, i, t, callback_kwargs):
        if self.do_interrupt:
            self.do_interrupt = False
            raise Exception("Interrupted")
        return callback_kwargs

    def sample_diffusers_model(self):
        self.logger.debug("sample_diffusers_model")
        try:
            return self.do_sample()
        except Exception as e:
            if self.is_pytorch_error(e):
                self.log_error(self.cuda_error_message)
            else:
                self.log_error(e, "Something went wrong while generating image")
                return None, None

    def on_start_auto_image_generation_signal(self):
        # self.sd_mode = SDMode.DRAWING
        # self.generator_sample()
        pass

    def on_sd_cancel_signal(self):
        print("on_sd_cancel_signal")

    def on_stop_auto_image_generation_signal(self):
        #self.sd_mode = SDMode.STANDARD
        pass

    def generate(self):
        error_message = ""
        try:
            images, nsfw_content_detected = self.sample_diffusers_model()
            return self.image_handler(
                images,
                self.requested_data,
                nsfw_content_detected
            )
        except TypeError as e:
            error_message = f"TypeError during generation"
            self.log_error(e, error_message)
            error = e
        except Exception as e:
            error = e
            if self.is_pytorch_error(e):
                error = self.cuda_error_message
                clear_memory()
                self.reset_applied_memory_settings()
            else:
                error_message = f"Error during generation"
                traceback.print_exc()

        if error:
            self.initialized = False
            self.reload_model = True
            if not self.has_internet_connection:
                self.log_error("Please check your internet connection and try again.")
            else:
                self.log_error(error, error_message)
            self.scheduler_name = ""
            self.local_files_only = True

        self.final_callback()

    def image_handler(
        self,
        images: List[Image.Image],
        data: dict,
        nsfw_content_detected: List[bool] = None
    ):
        self.final_callback()
        if images is None:
            return

        if data is not None:
            data["original_model_data"] = self.original_model_data or {}
        has_nsfw = True in nsfw_content_detected if nsfw_content_detected is not None else False

        if images:
            tab_section = "stablediffusion"
            data["tab_section"] = tab_section

            do_base64 = data.get("do_base64", False)

            if not has_nsfw:
                # apply filters and convert to base64 if requested
                has_filters = self.filters is not None and len(self.filters) > 0
                if has_filters or do_base64:
                    for i, image in enumerate(images):
                        if has_filters:
                            image = self.apply_filters(image, self.filters)
                        if do_base64:
                            img_byte_arr = io.BytesIO()
                            image.save(img_byte_arr, format='PNG')
                            img_byte_arr = img_byte_arr.getvalue()
                            image = base64.encodebytes(img_byte_arr).decode('ascii')
                        images[i] = image
            else:
                for i, is_nsfw in enumerate(nsfw_content_detected):
                    if is_nsfw:
                        has_nsfw = True
                        image = images[i]
                        image = image.convert("RGBA")
                        draw = ImageDraw.Draw(image)
                        font = ImageFont.truetype("arial", 15)
                        draw.text((0, 0), "NSFW", (255, 255, 255), font=font)
                        if do_base64:
                            img_byte_arr = io.BytesIO()
                            image.save(img_byte_arr, format='PNG')
                            img_byte_arr = img_byte_arr.getvalue()
                            image = base64.encodebytes(img_byte_arr).decode('ascii')
                        images[i] = image
        return dict(
            images=images,
            data=data,
            nsfw_content_detected=has_nsfw,
        )

    def final_callback(self):
        self.emit(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": self.sd_request.generator_settings.steps,
            "total": self.sd_request.generator_settings.steps,
        })
        self.latents_set = True

    def callback(self, step: int, _time_step, latents):
        res = {
            "step": step,
            "total": self.sd_request.generator_settings.steps
        }
        self.emit(SignalCode.SD_PROGRESS_SIGNAL, res)
        QApplication.processEvents()
        if self.latents_set is False:
            self.latents = latents
        return {}

    def on_unload_stablediffusion_signal(self):
        self.unload()

    def unload(self):
        self.unload_model()
        self.unload_tokenizer()
        clear_memory()

    def unload_model(self):
        self.logger.debug("Unloading model")
        self.pipe = None

    def unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        self.tokenizer = None

    def process_upscale(self, data: dict):
        self.logger.debug("Processing upscale")
        image = self.sd_request.generator_settings.input_image
        results = []
        if image:
            self.move_pipe_to_cpu()
            results = RealESRGAN(
                input=image,
                output=None,
                model_name='RealESRGAN_x4plus',
                denoise_strength=self.denoise_strength,
                face_enhance=self.face_enhance,
            ).run()
            clear_memory()
        else:
            self.log_error("No image found, unable to upscale")
        # check if results is a list
        if not isinstance(results, list):
            return [results]
        return results

    def do_upscale(self, data):
        images = self.process_upscale(data)
        return self.image_handler(images, self.requested_data, None)

    def load_generator_arguments(self):
        requested_model = self.settings["generator_settings"]["model"]
        model_changed = (self.model["name"] is not None and self.model["name"] != requested_model)
        if model_changed:  # model change
            self.logger.debug(f"Model changed clearing debugger: {self.model['name']} != {requested_model}")
            self.reload_model = True
            self.clear_scheduler()
            self.clear_controlnet()

        if self.settings["generator_settings"]["enable_controlnet"]:
            controlnet_image = self.controlnet_image
        else:
            controlnet_image = None

        """
        Set a reference to pipe
        """
        is_txt2img = self.sd_request.is_txt2img
        is_img2img = self.sd_request.is_img2img
        is_outpaint = self.sd_request.is_outpaint
        self.data = self.sd_request(
            model_data=self.model,
            extra_options={},
            callback=self.callback,
            cross_attention_kwargs_scale=(
                not self.sd_request.is_pix2pix and
                len(self.available_lora) > 0 and
                len(self.loaded_lora) > 0
            ),
            latents=self.latents,
            device=self.device,
            do_load=self.do_load,
            generator=self.generator(),
            model_changed=model_changed,
            prompt_embeds=self.prompt_embeds,
            negative_prompt_embeds=self.negative_prompt_embeds,
            controlnet_image=controlnet_image
        )
        pipe = None
        if self.pipe is None:
            if self.sd_request.is_txt2img and not is_txt2img:
                if is_img2img:
                    pipe = self.img2img
                elif is_outpaint:
                    pipe = self.outpaint
                if pipe is not None:
                    pipeline_class_ = StableDiffusionPipeline
                    if self.sd_request.generator_settings.enable_controlnet:
                        pipeline_class_ = StableDiffusionControlNetPipeline
                    self.pipe = pipeline_class_(**pipe.components)
            elif self.sd_request.is_img2img and not is_img2img:
                if is_txt2img:
                    pipe = self.txt2img
                elif is_outpaint:
                    pipe = self.outpaint
                if pipe is not None:
                    pipeline_class_ = StableDiffusionImg2ImgPipeline
                    if self.sd_request.generator_settings.enable_controlnet:
                        pipeline_class_ = StableDiffusionControlNetImg2ImgPipeline
                    self.pipe = pipeline_class_(**pipe.components)
            elif self.sd_request.is_outpaint and not is_outpaint:
                if is_txt2img:
                    pipe = self.txt2img
                elif is_img2img:
                    pipe = self.img2img
                if pipe is not None:
                    pipeline_class_ = StableDiffusionInpaintPipeline
                    if self.sd_request.generator_settings.enable_controlnet:
                        pipeline_class_ = StableDiffusionControlNetInpaintPipeline
                    self.pipe = pipeline_class_(**pipe.components)

        self.requested_data = self.data
        self.model_version = self.sd_request.generator_settings.version
        self.is_sd_xl = self.model_version == StableDiffusionVersion.SDXL1_0.value or self.is_sd_xl_turbo
        self.is_sd_xl_turbo = self.model_version == StableDiffusionVersion.SDXL_TURBO.value
        self.is_turbo = self.model_version == StableDiffusionVersion.SD_TURBO.value
        self.use_compel = (
           not self.sd_request.memory_settings.use_enable_sequential_cpu_offload and
           not self.is_sd_xl and
           not self.is_sd_xl_turbo and
           not self.is_turbo
        )
        self.controlnet_type = self.options.get(
            "controlnet",
            Controlnet.CANNY.value
        ).lower()
        self.controlnet_type = self.controlnet_type.replace(" ", "_")
        self.generator().manual_seed(self.sd_request.generator_settings.seed)
        seed_everything(self.seed)

    def generator_sample(self):
        """
        Called from sd_generate_worker, kicks off the generation process.
        :param data:
        :return:
        """
        action = self.settings["generator_settings"]["section"]
        if (self.sd_request.generator_settings and action != self.sd_request.generator_settings.section) or self.reload_model:
            self._prompt_embeds = None
            self._negative_prompt_embeds = None

        if (
            (self.controlnet_loaded and not self.settings["generator_settings"]["enable_controlnet"]) or
            (not self.controlnet_loaded and self.settings["generator_settings"]["enable_controlnet"])
        ):
            self.initialized = False

        self.load_generator_arguments()

        if self.do_load:
            self.prepare_scheduler()
            self.prepare_model()
            self.initialize()

        self.change_scheduler()

        if self.pipe and self.moved_to_cpu:
            self.apply_memory_efficient_settings()
            self.moved_to_cpu = False

        if self.pipe and self.do_load:
            """
            Reload prompt embeds.
            """
            self.apply_memory_efficient_settings()
            # move pipe components to device and initialize text encoder for clip skip
            self.pipe.to(self.data_type)
            self.pipe.vae.to(self.data_type)
            self.pipe.text_encoder.to(self.data_type)
            self.pipe.unet.to(self.data_type)

            try:
                self.add_lora_to_pipe()
            except Exception as _e:
                self.error_handler("Selected LoRA are not supported with this model")
                self.reload_model = True

        if self.do_load_compel:
            self.reload_prompts = False
            self.prompt_embeds = None
            self.negative_prompt_embeds = None
            self.load_prompt_embeds(
                self.pipe,
                prompt=self.sd_request.generator_settings.prompt,
                negative_prompt=self.sd_request.generator_settings.negative_prompt
            )
            self.data = self.sd_request.initialize_prompt_embeds(
                prompt_embeds=self.prompt_embeds,
                negative_prompt_embeds=self.negative_prompt_embeds,
                args=self.data
            )

        # ensure only prompt OR prompt_embeds are used
        if "prompt" in self.data and "prompt_embeds" in self.data:
            del self.data["prompt"]

        if "negative_prompt" in self.data and "negative_prompt_embeds" in self.data:
            del self.data["negative_prompt"]

        self.do_set_seed = False

        if self.sd_request.is_upscale:
            return self.do_upscale(self.data)

        if not self.pipe:
            self.logger.error("pipe is None")
            return

        if not self.do_generate:
            return

        self.do_generate = False

        is_img2img = self.sd_request.is_img2img

        kwargs = dict(
            vae=self.pipe.vae,
            text_encoder=self.pipe.text_encoder,
            tokenizer=self.pipe.tokenizer,
            unet=self.pipe.unet,
            scheduler=self.pipe.scheduler,
            safety_checker=self.safety_checker,
            feature_extractor=self.feature_extractor
        )

        if self.sd_request.is_img2img:
            if "image" not in self.data or self.data["image"] is None:
                self.data = self.sd_request.disable_img2img(self.data)
                is_img2img = False
                if self.sd_request.generator_settings.enable_controlnet:
                    kwargs["controlnet"] = self.pipe.controlnet
                    self.pipe = StableDiffusionControlNetPipeline(**kwargs)

        if self.sd_request.generator_settings.enable_controlnet:
            if "control_image" not in self.data or self.data["control_image"] is None:
                self.data = self.sd_request.disable_controlnet(self.data)
                if is_img2img:
                    self.pipe = StableDiffusionImg2ImgPipeline(**kwargs)
                else:
                    self.pipe = StableDiffusionPipeline(**kwargs)

        self.emit(
            SignalCode.LOG_STATUS_SIGNAL,
            f"Generating media"
        )

        return self.generate()

    def log_error(self, error, message=None):
        message = str(error) if not message else message
        traceback.print_exc()
        self.error_handler(message)

    def load_controlnet_from_ckpt(self, pipeline):
        self.logger.debug("Loading controlnet from ckpt")
        pipeline = self.controlnet_action_diffuser(
            vae=pipeline.vae,
            text_encoder=pipeline.text_encoder,
            tokenizer=pipeline.tokenizer,
            unet=pipeline.unet,
            controlnet=self.controlnet(),
            scheduler=pipeline.scheduler,
            safety_checker=self.safety_checker,
            feature_extractor=self.feature_extractor
        )
        self.controlnet_loaded = True
        return pipeline

    def load_controlnet(self, local_files_only: bool = None):
        controlnet_name = self.settings["generator_settings"]["controlnet_image_settings"]["controlnet"]
        controlnet_model = self.controlnet_model_by_name(controlnet_name)
        self.logger.debug(f"Loading controlnet {self.controlnet_type} self.controlnet_model {controlnet_model}")
        self._controlnet = None
        self.current_controlnet_type = self.controlnet_type
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        try:
            controlnet = ControlNetModel.from_pretrained(
                controlnet_model["path"],
                torch_dtype=self.data_type,
                local_files_only=local_files_only
            )
        except Exception as e:
            if "We couldn't connect to 'https://huggingface.co'" in str(e) and local_files_only is True:
                self.logger.error("Failed to load controlnet from local files, trying to load from huggingface")
                return self.load_controlnet(local_files_only=False)
            self.logger.error(f"Error loading controlnet {e}")
            return None
        # self.load_controlnet_scheduler()
        return controlnet

    def unload_unused_models(self):
        self.logger.debug("Unloading unused models")
        for action in [
            "txt2img",
            "img2img",
            "pix2pix",
            "outpaint",
            "depth2img",
            "_controlnet",
            "safety_checker",
        ]:
            val = getattr(self, action)
            if val:
                val.to("cpu")
                setattr(self, action, None)
                del val
        clear_memory()
        self.reset_applied_memory_settings()

    def pipeline_class(self):
        if self.settings["generator_settings"]["enable_controlnet"]:
            if self.sd_request.is_img2img:
                pipeline_classname_ = StableDiffusionControlNetImg2ImgPipeline
            elif self.sd_request.is_txt2img:
                pipeline_classname_ = StableDiffusionControlNetPipeline
            elif self.sd_request.generator_settings.section == "outpaint":
                pipeline_classname_ = StableDiffusionControlNetInpaintPipeline
            else:
                pipeline_classname_ = StableDiffusionControlNetPipeline
        elif self.sd_request.generator_settings.section == "depth2img":
            pipeline_classname_ = StableDiffusionDepth2ImgPipeline
        elif self.sd_request.generator_settings.section == "outpaint":
            pipeline_classname_ = AutoPipelineForInpainting
        elif self.sd_request.generator_settings.section == "pix2pix":
            pipeline_classname_ = StableDiffusionInstructPix2PixPipeline
        elif self.sd_request.is_img2img:
            pipeline_classname_ = StableDiffusionImg2ImgPipeline
        else:
            pipeline_classname_ = StableDiffusionPipeline
        return pipeline_classname_

    def load_model(self):
        self.logger.debug("Loading model")
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        kwargs = {}

        already_loaded = self.do_reuse_pipeline and not self.reload_model

        # move all models except for our current action to the CPU
        if not already_loaded or self.reload_model:
            self.unload_unused_models()
        elif self.pipe is None and self.do_reuse_pipeline or self.pipe and self.do_load_controlnet != self.current_load_controlnet:
            self.reuse_pipeline(self.do_load_controlnet)

        self.current_load_controlnet = self.do_load_controlnet

        if self.pipe is None or self.reload_model:
            self.logger.debug(f"Loading model from scratch {self.reload_model}")
            self.reset_applied_memory_settings()
            self.send_model_loading_message(self.model_path)

            if self.settings["generator_settings"]["enable_controlnet"]:
                kwargs["controlnet"] = self.controlnet()

            self.load_safety_checker()

            if self.is_single_file:
                try:
                    self.logger.debug(f"Loading ckpt file {self.model_path}")
                    self.pipe = self.download_from_original_stable_diffusion_ckpt()
                    self.pipe.scheduler = self.load_scheduler(config=self.pipe.scheduler.config)
                except OSError as e:
                    self.handle_missing_files(self.sd_request.generator_settings.section)
            else:
                self.logger.debug(f"Loading model `{self.model['name']}` `{self.model_path}`")
                scheduler = self.load_scheduler()
                if scheduler:
                    kwargs["scheduler"] = scheduler

                pipeline_classname_ = self.pipeline_class()

                self.pipe = pipeline_classname_.from_pretrained(
                    self.model_path,
                    torch_dtype=self.data_type,
                    safety_checker=self.safety_checker,
                    feature_extractor=self.feature_extractor,
                    **kwargs
                )

            if self.settings["nsfw_filter"] is False:
                self.pipe.safety_checker = None
                self.pipe.feature_extractor = None

            if self.pipe is None:
                self.emit(SignalCode.LOG_ERROR_SIGNAL, "Failed to load model")
                return

            old_model_path = self.current_model
            self.current_model = self.model_path
            self.current_model = old_model_path

            # if self.is_outpaint:
            #     self.logger.debug("Initializing vae for inpaint / outpaint")
            #     self.pipe.vae = AsymmetricAutoencoderKL.from_pretrained(
            #         self.inpaint_vae_model["path"],
            #         torch_dtype=self.data_type
            #     )

            self.controlnet_loaded = self.settings["generator_settings"]["enable_controlnet"]

    def get_pipeline_action(self, action=None):
        action = self.sd_request.generator_settings.section if not action else action
        if action == "txt2img" and self.sd_request.is_img2img:
            action = "img2img"
        return action

    def download_from_original_stable_diffusion_ckpt(self, local_files_only=True):
        pipe = None
        kwargs = {
            "checkpoint_path_or_dict": self.model_path,
            "device": self.device,
            "scheduler_type": Scheduler.DDIM.value.lower(),
            "from_safetensors": self.is_safetensors,
            "local_files_only": local_files_only,
            "extract_ema": False,
            "config_files": CONFIG_FILES,
            "pipeline_class": self.pipeline_class(),
            "load_safety_checker": False,
            "safety_checker": self.safety_checker,
            "feature_extractor": self.feature_extractor,
        }
        if self.settings["generator_settings"]["enable_controlnet"]:
            kwargs["controlnet"] = self.controlnet()
        try:
            pipe = download_from_original_stable_diffusion_ckpt(
                **kwargs
            )
        except ValueError:
            if local_files_only:
                # missing required files, attempt again with online access
                return self.download_from_original_stable_diffusion_ckpt(
                    local_files_only=False
                )
        except Exception as e:
            self.logger.error(f"Failed to load model from ckpt: {e}")
        return pipe

    def clear_controlnet(self):
        self.logger.debug("Clearing controlnet")
        self._controlnet = None
        clear_memory()
        self.reset_applied_memory_settings()
        self.controlnet_loaded = False

    def reuse_pipeline(self, do_load_controlnet, local_files_only=True):
        self.logger.debug("Reusing pipeline")
        pipe = None
        if self.sd_request.is_txt2img:
            pipe = self.img2img if self.txt2img is None else self.txt2img
        elif self.sd_request.is_img2img:
            pipe = self.txt2img if self.img2img is None else self.img2img
        if pipe is None:
            self.logger.warning("Failed to reuse pipeline")
            self.clear_controlnet()
            return
        kwargs = pipe.components

        # either load from a pretrained model or from a pipe
        if do_load_controlnet:
            self.controlnet_loaded = True
            pipe = self.load_controlnet_from_ckpt(pipe)
            kwargs["controlnet"] = self.controlnet()
        else:
            if "controlnet" in kwargs:
                del kwargs["controlnet"]
            #self.clear_controlnet()

            if self.is_single_file:
                if self.model_version == "SDXL 1.0":
                    pipeline_class_ = StableDiffusionXLPipeline
                else:
                    pipeline_class_ = StableDiffusionPipeline

                pipe = pipeline_class_.from_single_file(
                    self.model_path,
                    local_files_only=local_files_only
                )
                return pipe
            else:
                components = pipe.components
                if "controlnet" in components:
                    del components["controlnet"]
                components["controlnet"] = self.controlnet()

                pipe = AutoPipelineForText2Image.from_pretrained(
                    self.model_path,
                    **components
                )

        if self.sd_request.is_txt2img:
            self.txt2img = pipe
            self.img2img = None
        elif self.sd_request.is_img2img:
            self.img2img = pipe
            self.txt2img = None

    def send_model_loading_message(self, model_name):
        if self.attempt_download:
            if self.downloading_controlnet:
                message = f"Downloading controlnet model"
            else:
                message = f"Downloading model {model_name}"
        else:
            message = f"Loading model {model_name}"
        self.emit(SignalCode.LOG_STATUS_SIGNAL, message)

    def prepare_model(self):
        self.logger.debug("Prepare model")
        self._previous_model = self.current_model
        if self.is_single_file:
            self.current_model = self.model
        else:
            self.current_model = self.model_path
            self.current_model_branch = self.model["branch"]

        if self.do_unload_controlnet:
            self.unload_controlnet()

    def unload_controlnet(self):
        if self.pipe:
            self.logger.debug("Unloading controlnet")
            self.pipe.controlnet = None
        self.controlnet_loaded = False

    def handle_missing_files(self, action):
        if not self.attempt_download:
            if self.is_ckpt_model or self.is_safetensors:
                self.logger.debug("Required files not found, attempting download")
            else:
                traceback.print_exc()
                self.logger.debug("Model not found, attempting download")
            # check if we have an internet connection
            if self.allow_online_when_missing_files:
                self.emit(SignalCode.LOG_STATUS_SIGNAL, "Downloading model files")
                self.local_files_only = False
            else:
                self.send_error("Required files not found, enable online access to download")
                return None
            self.attempt_download = True
            if action == "controlnet":
                self.downloading_controlnet = True
            return self.generator_sample()
        else:
            self.local_files_only = True
            self.attempt_download = False
            self.downloading_controlnet = False
            if self.is_ckpt_model or self.is_safetensors:
                self.log_error("Unable to download required files, check internet connection")
            else:
                self.log_error("Unable to download model, check internet connection")
            self.initialized = False
            return None
