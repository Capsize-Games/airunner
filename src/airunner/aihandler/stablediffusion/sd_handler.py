import io
import base64
import os
import random
import traceback
import numpy as np
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication
from typing import List
import torch
from PIL import (
    Image,
    ImageDraw,
    ImageFont
)
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import download_from_original_stable_diffusion_ckpt
from diffusers.utils.torch_utils import randn_tensor
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionXLPipeline,
    AutoPipelineForText2Image,
    StableDiffusionDepth2ImgPipeline,
    AutoPipelineForInpainting,
    StableDiffusionInstructPix2PixPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline
)
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from diffusers import (
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,

)
from transformers import AutoFeatureExtractor
from airunner.aihandler.base_handler import BaseHandler
from airunner.aihandler.mixins.controlnet_mixin import ControlnetHandlerMixin
from airunner.aihandler.mixins.model_mixin import ModelMixin
from airunner.aihandler.mixins.safety_checker_mixin import SafetyCheckerMixin
from airunner.aihandler.stablediffusion.sd_request import SDRequest
from airunner.enums import (
    FilterType,
    HandlerType,
    SignalCode,
    Scheduler,
    SDMode,
    StableDiffusionVersion,
    EngineResponseCode, ModelStatus, ModelType
)
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.windows.main.lora_mixin import LoraMixin as LoraDataMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.utils.clear_memory import clear_memory
from airunner.utils.random_seed import random_seed
from airunner.utils.create_worker import create_worker
from airunner.utils.get_torch_device import get_torch_device
from airunner.workers.worker import Worker

SKIP_RELOAD_CONSTS = (
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
        self.emit_signal(
            SignalCode.SD_IMAGE_GENERATED_SIGNAL,
            {
                "images": [image],
                "action": sd_request.generator_settings.section,
                "outpaint_box_rect": sd_request.active_rect,
            }
        )
        self.sd_request = None


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
    ControlnetHandlerMixin,
    SafetyCheckerMixin,
    ModelMixin,
):
    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LoraDataMixin.__init__(self)
        EmbeddingDataMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        LoraMixin.__init__(self)
        CompelMixin.__init__(self)
        SchedulerMixin.__init__(self)
        MemoryEfficientMixin.__init__(self)
        ControlnetHandlerMixin.__init__(self)
        SafetyCheckerMixin.__init__(self)
        ModelMixin.__init__(self)
        PipelineMixin.__init__(self)
        self.logger.debug("Loading Stable Diffusion model runner...")
        self.handler_type = HandlerType.DIFFUSER
        self._previous_model = ""
        self.safety_checker_status = ModelStatus.UNLOADED
        self.cross_attention_kwargs_scale: float = 1.0
        self._initialized = False
        self._reload_model = False
        self.current_model_branch = None
        self.state = None
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
        self.generator_request_data = None
        self._allow_online_mode = None
        self.processor = None
        self.attempt_download = False
        self.latents_set = False
        self._latents = None
        self._safety_checker = None
        self.current_model = ""
        self.seed = 42
        self.batch_size = 1
        self.use_prompt_converter = True
        self.depth_map = None
        self.model_data = None
        self.model_version = ""
        self.use_tiled_vae = False
        self.use_accelerated_transformers = False
        self.use_torch_compile = False
        self.is_sd_xl = False
        self.is_sd_xl_turbo = False
        self.is_turbo = False
        self.use_compel = False
        self.filters = None
        self.original_model_data = None
        self.denoise_strength = None
        self.face_enhance = False
        self.allow_online_mode = False
        self.initialized = False
        self.reload_model = False
        self.extra_args = None
        self.latents = None
        self.sd_mode = None
        self.reload_prompts = False
        self.moved_to_cpu = False
        self.cur_prompt = ""
        self.cur_neg_prompt = ""
        self.data = {
            "action": "txt2img",
        }
        signals = {
            SignalCode.UNLOAD_SAFETY_CHECKER_SIGNAL: self.unload_safety_checker,
            SignalCode.LOAD_SAFETY_CHECKER_SIGNAL: self.load_safety_checker,
            SignalCode.SD_CANCEL_SIGNAL: self.on_sd_cancel_signal,
            SignalCode.SD_UNLOAD_SIGNAL: self.on_unload_stablediffusion_signal,
            SignalCode.SD_LOAD_SIGNAL: self.on_load_stablediffusion_signal,
            SignalCode.SD_MOVE_TO_CPU_SIGNAL: self.on_move_to_cpu,
            SignalCode.START_AUTO_IMAGE_GENERATION_SIGNAL: self.on_start_auto_image_generation_signal,
            SignalCode.STOP_AUTO_IMAGE_GENERATION_SIGNAL: self.on_stop_auto_image_generation_signal,
            SignalCode.DO_GENERATE_SIGNAL: self.on_do_generate_signal,
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.CHANGE_SCHEDULER_SIGNAL: self.on_change_scheduler_signal,
        }
        for code, handler in signals.items():
            self.register(code, handler)

        torch.backends.cuda.matmul.allow_tf32 = self.settings["memory_settings"]["use_tf32"]

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

    def on_change_scheduler_signal(self, data=None):
        print("CHANGE SCHEDULER")
        self.load_scheduler()

    @property
    def inpaint_vae_model(self):
        try:
            return self.models_by_pipeline_action("inpaint_vae")[0]
        except IndexError:
            return None

    def on_unload_stablediffusion_signal(self, _message):
        self.unload()

    def on_load_stablediffusion_signal(self, message):
        self.load()
        self.load_safety_checker()

    def on_start_auto_image_generation_signal(self, _message: dict):
        # self.sd_mode = SDMode.DRAWING
        # self.generator_sample()
        pass

    def on_sd_cancel_signal(self, _message: dict):
        print("on_sd_cancel_signal")

    def on_stop_auto_image_generation_signal(self, _message: dict):
        #self.sd_mode = SDMode.STANDARD
        pass

    def on_interrupt_process_signal(self, _message: dict):
        self.do_interrupt = True

    @property
    def device(self):
        return get_torch_device(self.settings["memory_settings"]["default_gpu"]["sd"])

    @property
    def do_load(self):
        return (
            self.sd_mode not in SKIP_RELOAD_CONSTS or
            not self.initialized
        )

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
    def cuda_is_available(self) -> bool:
        if self.settings["memory_settings"]["enable_model_cpu_offload"]:
            return False
        return torch.cuda.is_available()

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

    def ai_model_by_name(self, name):
        try:
            return [model for model in self.settings["ai_models"] if model["name"] == name][0]
        except Exception as e:
            self.logger.error(f"Error finding model by name: {name}")

    def ai_model_by_path(self, path):
        try:
            return [model for model in self.settings["ai_models"] if model["path"] == path][0]
        except Exception as e:
            self.logger.error(f"Error finding model by path: {path}")

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
    def is_pytorch_error(e) -> bool:
        return "PYTORCH_CUDA_ALLOC_CONF" in str(e)

    def on_do_generate_signal(self, message: dict):
        self.do_generate = True
        self.generator_request_data = message

    def run(self):
        if (
            self.settings["generator_settings"]["prompt"] != self.cur_prompt or
            self.settings["generator_settings"]["negative_prompt"] != self.cur_neg_prompt
        ):
            self.cur_prompt = self.settings["generator_settings"]["prompt"]
            self.cur_neg_prompt = self.settings["generator_settings"]["negative_prompt"]

            self.sd_request.generator_settings.parse_prompt(
                self.settings["nsfw_filter"],
                self.settings["generator_settings"]["prompt"],
                self.settings["generator_settings"]["negative_prompt"]
            )

            self.latents = None
            self.latents_set = False
            self.reload_prompts = True

        response = None
        if not self.loaded and self.loading:
            if self.initialized and self.pipe:
                self.loaded = True
                self.loading = False
        elif self.loaded:
            response = self.generator_sample()
            self.initialized = True
        elif self.loaded and not self.loading and self.do_generate:
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

            # if nsfw_content_detected:
            #     self.emit_signal(
            #         SignalCode.SD_NSFW_CONTENT_DETECTED_SIGNAL,
            #         response
            #     )
            # else:
            response["action"] = self.sd_request.generator_settings.section
            response["outpaint_box_rect"] = self.sd_request.active_rect

            self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
                'code': EngineResponseCode.IMAGE_GENERATED,
                'message': response
            })

    def on_move_to_cpu(self, message: dict = None):
        message = message or {}
        if not self.is_pipe_on_cpu() and self.has_pipe():
            self.logger.debug("Moving model to CPU")
            self.pipe = self.pipe.to("cpu")
            self.moved_to_cpu = True
            clear_memory()
        if "callback" in message:
            message["callback"]()

    def send_error(self, message):
        self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, message)

    def error_handler(self, error):
        message = str(error)
        if (
            "got an unexpected keyword argument 'image'" in message and
            self.sd_request.generator_settings.section in ["outpaint", "pix2pix", "depth2img"]
        ):
            message = f"This model does not support {self.sd_request.generator_settings.section}"
        traceback.print_exc()
        self.logger.error(error)
        self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, message)

    @Slot(object)
    def load_generator_arguments(self):
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        model_changed = self.handle_model_changed()

        # Set a reference to pipe
        is_txt2img = self.sd_request.is_txt2img
        is_img2img = self.sd_request.is_img2img
        is_outpaint = self.sd_request.is_outpaint
        controlnet_image = self.get_controlnet_image()
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
            controlnet_image=controlnet_image,
            generator_request_data=self.generator_request_data
        )

        pipe = None
        pipeline_class_ = None

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
            pipeline_class_ = StableDiffusionInpaintPipeline
            if self.sd_request.generator_settings.enable_controlnet:
                pipeline_class_ = StableDiffusionControlNetInpaintPipeline

        if pipe is not None and pipeline_class_ is not None:
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
        controlnet = self.settings["generator_settings"]["controlnet_image_settings"]["controlnet"]
        controlnet_item = self.controlnet_model_by_name(controlnet)
        self.controlnet_type = controlnet_item["name"]
        self.generator().manual_seed(self.sd_request.generator_settings.seed)
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)

    def log_error(self, error, message=None):
        message = str(error) if not message else message
        traceback.print_exc()
        self.error_handler(message)

