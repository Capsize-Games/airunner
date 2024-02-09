import io
import base64
import re
import traceback
from pytorch_lightning import seed_everything
from io import BytesIO
from typing import List
import PIL
import imageio
import numpy as np
import requests
import torch

from PIL import Image, ImageDraw, ImageFont

from controlnet_aux.processor import Processor
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import \
    download_from_original_stable_diffusion_ckpt
from diffusers.pipelines.text_to_video_synthesis.pipeline_text_to_video_zero import CrossFrameAttnProcessor
from diffusers.utils.torch_utils import randn_tensor
from torchvision import transforms
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline, AutoPipelineForText2Image, \
    StableDiffusionDepth2ImgPipeline, AutoPipelineForInpainting, StableDiffusionInstructPix2PixPipeline
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from diffusers import StableDiffusionControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, StableDiffusionControlNetInpaintPipeline, AsymmetricAutoencoderKL
from diffusers import ConsistencyDecoderVAE
from transformers import AutoFeatureExtractor
from airunner.aihandler.base_handler import BaseHandler

from airunner.enums import FilterType, HandlerType, SignalCode
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.aihandler.mixins.txttovideo_mixin import TexttovideoMixin
from airunner.aihandler.settings import AIRUNNER_ENVIRONMENT
from airunner.windows.main.layer_mixin import LayerMixin
from airunner.windows.main.lora_mixin import LoraMixin as LoraDataMixin
from airunner.windows.main.embedding_mixin import EmbeddingMixin as EmbeddingDataMixin
from airunner.windows.main.pipeline_mixin import PipelineMixin
from airunner.windows.main.controlnet_model_mixin import ControlnetModelMixin
from airunner.windows.main.ai_model_mixin import AIModelMixin
from airunner.utils import clear_memory
#from airunner.scripts.realesrgan.main import RealESRGAN

torch.backends.cuda.matmul.allow_tf32 = True


class SDHandler(
    BaseHandler,
    MergeMixin,
    LoraMixin,
    MemoryEfficientMixin,
    EmbeddingMixin,
    TexttovideoMixin,
    CompelMixin,
    SchedulerMixin,

    # Data Mixins
    LayerMixin,
    LoraDataMixin,
    EmbeddingDataMixin,
    PipelineMixin,
    ControlnetModelMixin,
    AIModelMixin,
):
    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LayerMixin.__init__(self)
        LoraDataMixin.__init__(self)
        EmbeddingDataMixin.__init__(self)
        PipelineMixin.__init__(self)
        ControlnetModelMixin.__init__(self)
        AIModelMixin.__init__(self)
        self.logger.info("Loading Stable Diffusion model runner...")
        self.safety_checker_model = self.models_by_pipeline_action("safety_checker")[0]
        self.text_encoder_model = self.models_by_pipeline_action("text_encoder")[0]
        self.inpaint_vae_model = self.models_by_pipeline_action("inpaint_vae")[0]
        self.register(SignalCode.SD_CANCEL_SIGNAL, self.on_sd_cancel_signal)
        self.register(SignalCode.SD_UNLOAD_SIGNAL, self.on_unload_stablediffusion_signal)
        self.register(SignalCode.SD_MOVE_TO_CPU_SIGNAL, self.on_move_to_cpu)
        self.handler_type = HandlerType.DIFFUSER
        self._current_model: str = ""
        self._previous_model: str = ""
        self._initialized: bool = False
        self._current_sample = 0
        self._reload_model: bool = False
        self.do_cancel = False
        self.current_model_branch = None
        self.state = None
        self._local_files_only = True
        self.lora_loaded = False
        self.loaded_lora = []
        self._settings = None
        self._action = None
        self.embeds_loaded = False
        self._compel_proc = None
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
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
        self.downloading_controlnet = False
        self.safety_checker_model = ""
        self.text_encoder_model = ""
        self.inpaint_vae_model = ""
        self._controlnet_image = None
        self._latents = None
        self.txt2img = None
        self.img2img = None
        self.pix2pix = None
        self.outpaint = None
        self.depth2img = None
        self.txt2vid = None
        self.tokenizer = None
        self._safety_checker = None
        self._controlnet = None
        self.data = {
            "action": "txt2img",
        }

    @property
    def allow_online_mode(self):
        return self.options.get("allow_online_mode", False)

    @property
    def vae_path(self):
        return self.options.get("vae_path", "openai/consistency-decoder")

    @property
    def controlnet_model(self):
        name = self.controlnet_type
        if self.is_vid2vid:
            name = "openpose"
        model = self.controlnet_model_by_name(name)
        if not model:
            raise ValueError(f"Unable to find controlnet model {name}")
        return model.path

    @property
    def controlnet_type(self):
        if self.is_vid2vid:
            return "openpose"

        controlnet_type = self.options.get("controlnet", None).lower()
        if not controlnet_type:
            controlnet_type = "canny"
        return controlnet_type.replace(" ", "_")

    @property
    def allow_online_when_missing_files(self):
        """
        This settings prevents the application from going online when a file is missing.
        :return:
        """
        if self._allow_online_mode is None:
            self._allow_online_mode = self.allow_online_mode
        return self._allow_online_mode

    @property
    def local_files_only(self):
        return self._local_files_only

    @local_files_only.setter
    def local_files_only(self, value):
        self.logger.info("Setting local_files_only to %s" % value)
        self._local_files_only = value

    @property
    def initialized(self):
        return self._initialized

    @initialized.setter
    def initialized(self, value):
        self._initialized = value

    @property
    def reload_model(self):
        return self._reload_model

    @reload_model.setter
    def reload_model(self, value):
        self._reload_model = value

    @property
    def current_sample(self):
        return self._current_sample

    @current_sample.setter
    def current_sample(self, value):
        self._current_sample = value

    def has_pipe(self):
        return self.pipe is not None

    def pipe_on_cpu(self):
        return self.pipe.device.type == "cpu"

    def is_pipe_on_cpu(self):
        return self.has_pipe() and self.pipe_on_cpu()

    def on_move_to_cpu(self, message: dict = None):
        message = message or {}
        if not self.is_pipe_on_cpu() and self.has_pipe():
            self.logger.info("Moving model to CPU")
            self.pipe = self.pipe.to("cpu")
            clear_memory()
        if "callback" in message:
            message["callback"]()

    @property
    def options(self):
        return self.data.get("options", {})

    @property
    def seed(self):
        return int(self.options.get(f"seed", 42)) + self.current_sample

    @property
    def deterministic_seed(self):
        return self.options.get("deterministic_seed", None)

    @property
    def deterministic_style(self):
        return self.options.get("deterministic_style", None)

    @property
    def batch_size(self):
        return self.options.get("batch_size", 1)

    @property
    def prompt_data(self):
        return self.options.get(f"prompt_data", PromptData(file_name="prompts"))

    @property
    def prompt(self):
        prompt = self.options.get(f"prompt", "")
        self.requested_data[f"prompt"] = prompt
        return prompt

    @property
    def negative_prompt(self):
        negative_prompt = self.options.get(f"negative_prompt", "")
        self.requested_data[f"negative_prompt"] = negative_prompt
        return negative_prompt

    @property
    def use_prompt_converter(self):
        return True

    @property
    def guidance_scale(self):
        return self.options.get(f"scale", 7.5)

    @property
    def image_guidance_scale(self):
        return self.options.get(f"image_guidance_scale", 1.5)

    @property
    def height(self):
        return self.options.get(f"height", 512)

    @property
    def width(self):
        return self.options.get(f"width", 512)

    @property
    def steps(self):
        return self.options.get(f"steps", 20)

    @property
    def ddim_eta(self):
        return self.options.get(f"ddim_eta", 0.5)

    @property
    def n_samples(self):
        return self.options.get(f"n_samples", 1)

    @property
    def pos_x(self):
        return self.options.get(f"pos_x", 0)

    @property
    def pos_y(self):
        return self.options.get(f"pos_y", 0)

    @property
    def outpaint_box_rect(self):
        return self.options.get(f"box_rect", "")

    @property
    def hf_token(self):
        return self.data.get("hf_token", "")

    @property
    def strength(self):
        return self.options.get(f"strength", 1.0)

    @property
    def depth_map(self):
        return self.options.get("depth_map", None)

    @property
    def image(self):
        return self.options.get(f"image", None)

    @property
    def input_image(self):
        return self.options.get("input_image", None)

    @property
    def mask(self):
        return self.options.get(f"mask", None)

    @property
    def enable_model_cpu_offload(self):
        return self.options.get("enable_model_cpu_offload", False) is True

    @property
    def use_attention_slicing(self):
        return self.options.get("use_attention_slicing", False) is True

    @property
    def use_tf32(self):
        return self.options.get("use_tf32", False) is True

    @property
    def use_last_channels(self):
        return self.options.get("use_last_channels", True) is True

    @property
    def use_enable_sequential_cpu_offload(self):
        return self.options.get("use_enable_sequential_cpu_offload", True) is True

    @property
    def use_enable_vae_slicing(self):
        return self.options.get("use_enable_vae_slicing", False) is True

    @property
    def use_tome_sd(self):
        return self.options.get("use_tome_sd", False) is True

    @property
    def do_nsfw_filter(self):
        return self.options.get("do_nsfw_filter", True) is True

    @property
    def model_version(self):
        return self.model_data["version"]

    @property
    def use_compel(self):
        return not self.use_enable_sequential_cpu_offload and \
               not self.is_txt2vid and \
               not self.is_vid2vid and \
               not self.is_sd_xl and \
               not self.is_sd_xl_turbo and \
               not self.is_turbo

    @property
    def use_tiled_vae(self):
        return self.options.get("use_tiled_vae", False) is True

    @property
    def use_accelerated_transformers(self):
        return self.options.get("use_accelerated_transformers", False) is True

    @property
    def use_torch_compile(self):
        return self.options.get("use_torch_compile", False) is True

    @property
    def is_sd_xl(self):
        return self.model_version == "SDXL 1.0" or self.is_sd_xl_turbo

    @property
    def is_sd_xl_turbo(self):
        return self.model_version == "SDXL Turbo"

    @property
    def is_turbo(self):
        return self.model_version == "SD Turbo"

    @property
    def model(self):
        return self.options.get(f"model", None)

    @property
    def action(self):
        try:
            return self.data.get("action", None)
        except Exception as e:
            self.logger.error(f"Error getting action {e}")
            return None

    @property
    def action_has_safety_checker(self):
        return self.action not in ["depth2img"]

    @property
    def is_outpaint(self):
        return self.action == "outpaint"

    @property
    def is_txt2img(self):
        try:
            return self.action == "txt2img" and self.image is None
        except Exception as e:
            self.logger.error(f"Error checking if is txt2img {e}")
            return False

    @property
    def is_vid_action(self):
        return self.is_txt2vid or self.is_vid2vid

    @property
    def input_video(self):
        return self.options.get(
            "input_video",
            None
        )

    @property
    def is_txt2vid(self):
        return self.action == "txt2vid" and not self.input_video

    @property
    def is_vid2vid(self):
        return self.action == "txt2vid" and self.input_video

    @property
    def is_upscale(self):
        return self.action == "upscale"

    @property
    def is_img2img(self):
        return self.action == "txt2img" and self.image is not None

    @property
    def is_depth2img(self):
        return self.action == "depth2img"

    @property
    def is_pix2pix(self):
        return self.action == "pix2pix"

    @property
    def use_interpolation(self):
        return self.options.get("use_interpolation", False)

    @property
    def interpolation_data(self):
        return self.options.get("interpolation_data", None)

    @property
    def current_model(self):
        return self._current_model

    @current_model.setter
    def current_model(self, model):
        if self._current_model != model:
            self._current_model = model

    @property
    def model_base_path(self):
        return self.options.get("model_base_path", None)

    @property
    def gif_path(self):
        return self.options.get("gif_path", None)

    @property
    def image_path(self):
        return self.options.get("image_path", None)

    @property
    def lora_path(self):
        return self.options.get("lora_path", None)

    @property
    def embeddings_path(self):
        return self.options.get("embeddings_path", None)

    @property
    def video_path(self):
        return self.options.get("video_path", None)

    @property
    def outpaint_model_path(self):
        return self.options.get("outpaint_model_path", None)

    @property
    def pix2pix_model_path(self):
        return self.options.get("pix2pix_model_path", None)

    @property
    def depth2img_model_path(self):
        return self.options.get("depth2img_model_path", None)

    @property
    def model_path(self):
        return self.model_data["path"]

    @property
    def cuda_error_message(self):
        return f"VRAM too low for {self.width}x{self.height} resolution. Potential solutions: try again, use a different model, restart the application, use a smaller size, upgrade your GPU."

    @property
    def is_pipe_loaded(self):
        if self.is_txt2img:
            return self.txt2img is not None
        elif self.is_img2img:
            return self.img2img is not None
        elif self.is_pix2pix:
            return self.pix2pix is not None
        elif self.is_outpaint:
            return self.outpaint is not None
        elif self.is_depth2img:
            return self.depth2img is not None
        elif self.is_vid_action:
            return self.txt2vid is not None

    @property
    def enable_controlnet(self):
        if self.input_image is None and self.controlnet_image is None:
            return False
        if self.is_vid2vid:
            return True
        return self.options.get("enable_controlnet", False)

    @property
    def controlnet_conditioning_scale(self):
        return self.options.get(f"controlnet_conditioning_scale", 1.0)

    @property
    def controlnet_guess_mode(self):
        return self.options.get("controlnet_guess_mode", False)

    @property
    def control_guidance_start(self):
        return self.options.get("control_guidance_start", 0.0)

    @property
    def control_guidance_end(self):
        return self.options.get("control_guidance_end", 1.0)

    @property
    def pipe(self):
        try:
            if self.is_txt2img:
                return self.txt2img
            elif self.is_img2img:
                return self.img2img
            elif self.is_outpaint:
                return self.outpaint
            elif self.is_depth2img:
                return self.depth2img
            elif self.is_pix2pix:
                return self.pix2pix
            elif self.is_vid_action:
                return self.txt2vid
            else:
                self.logger.warning(f"Invalid action {self.action} unable to get pipe")
                return None
        except Exception as e:
            self.logger.error(f"Error getting pipe {e}")
            return None

    @pipe.setter
    def pipe(self, value):
        if self.is_txt2img:
            self.txt2img = value
        elif self.is_img2img:
            self.img2img = value
        elif self.is_outpaint:
            self.outpaint = value
        elif self.is_depth2img:
            self.depth2img = value
        elif self.is_pix2pix:
            self.pix2pix = value
        elif self.is_vid_action:
            self.txt2vid = value

    @property
    def cuda_is_available(self):
        if self.enable_model_cpu_offload:
            return False
        return torch.cuda.is_available()

    @property
    def model_data(self):
        return self.options.get("model_data", {})

    @property
    def is_ckpt_model(self):
        return self.is_ckpt_file(self.model_path)

    @property
    def is_safetensors(self):
        return self.is_safetensor_file(self.model_path)

    @property
    def is_single_file(self):
        return self.is_ckpt_model or self.is_safetensors

    @property
    def data_type(self):
        if self.use_enable_sequential_cpu_offload:
            return torch.float
        elif self.enable_model_cpu_offload:
            return torch.float16
        data_type = torch.float16 if self.cuda_is_available else torch.float
        return data_type

    @property
    def device(self):
        return "cuda" if self.cuda_is_available else "cpu"

    @property
    def has_internet_connection(self):
        try:
            _response = requests.get('https://huggingface.co/')
            return True
        except requests.ConnectionError:
            return False

    @property
    def filters(self):
        return self.options.get("filters", {})

    @property
    def safety_checker(self):
        return self._safety_checker

    @safety_checker.setter
    def safety_checker(self, value):
        self._safety_checker = value
        if value:
            self._safety_checker.to(self.device)

    @property
    def is_dev_env(self):
        return AIRUNNER_ENVIRONMENT == "dev"

    @property
    def clip_skip(self):
        return self.options.get("clip_skip", 0)

    @property
    def do_add_lora_to_pipe(self):
        return not self.is_vid_action

    @property
    def controlnet_action_diffuser(self):
        if self.is_txt2img or self.is_vid2vid:
            return StableDiffusionControlNetPipeline
        elif self.is_img2img:
            return StableDiffusionControlNetImg2ImgPipeline
        elif self.is_outpaint:
            return StableDiffusionControlNetInpaintPipeline
        else:
            raise ValueError(f"Invalid action {self.action} unable to get controlnet action diffuser")

    @property
    def controlnet_image(self):
        controlnet_image = self.options.get("controlnet_image", None)

        if not controlnet_image and self.input_image:
            controlnet_image = self.preprocess_for_controlnet(self.input_image)
            self.emit(SignalCode.CONTROLNET_IMAGE_GENERATED_SIGNAL, {
                'image': controlnet_image,
                'data': {
                    'controlnet_image': controlnet_image
                }
            })

        self._controlnet_image = controlnet_image

        return self._controlnet_image

    @property
    def do_load_controlnet(self):
        return (
                (not self.controlnet_loaded and self.enable_controlnet) or
                (self.controlnet_loaded and self.enable_controlnet)
        )

    @property
    def do_unload_controlnet(self):
        return not self.enable_controlnet and (self.controlnet_loaded)

    @property
    def do_reuse_pipeline(self):
        return (
                (self.is_txt2img and self.txt2img is None and self.img2img) or
                (self.is_img2img and self.img2img is None and self.txt2img) or
                ((
                         (self.is_txt2img and self.txt2img) or
                         (self.is_img2img and self.img2img)
                 ) and (self.do_load_controlnet or self.do_unload_controlnet))
        )

    @property
    def latents(self):
        return self.generate_latents()

    @latents.setter
    def latents(self, value):
        self._latents = value

    @property
    def hf_api_key_read_key(self):
        return self.options.get("hf_api_key_read_key", "")

    @hf_api_key_read_key.setter
    def hf_api_key_read_key(self, value):
        self.options["hf_api_key_read_key"] = value

    @property
    def hf_api_key_write_key(self):
        return self.options.get("hf_api_key_write_key", "")

    @hf_api_key_write_key.setter
    def hf_api_key_write_key(self, value):
        self.options["hf_api_key_write_key"] = value

    @property
    def original_model_data(self):
        return self.options.get("original_model_data", {})

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
    def is_ckpt_file(model):
        if not model:
            raise ValueError("ckpt path is empty")
        return model.endswith(".ckpt")

    @staticmethod
    def is_safetensor_file(model):
        if not model:
            raise ValueError("safetensors path is empty")
        return model.endswith(".safetensors")

    def initialize(self):
        if not self.initialized or self.reload_model or self.pipe is None:
            self.logger.info("Initializing")
            self.compel_proc = None
            self.prompt_embeds = None
            self.negative_prompt_embeds = None
            if self.reload_model:
                self.reset_applied_memory_settings()
            if not self.is_upscale:
                self.load_model()
            self.reload_model = False
            self.initialized = True

    def controlnet(self):
        if self._controlnet is None \
            or self.current_controlnet_type != self.controlnet_type:
            self._controlnet = self.load_controlnet()
        else:
            print("controlnet already loaded")
        return self._controlnet

    def generator(self, device=None, seed=None):
        device = self.device if not device else device
        if seed is None:
            seed = int(self.seed)
        return torch.Generator(device=device).manual_seed(seed)

    def prepare_options(self, data):
        self.logger.info(f"Preparing options")
        action = data["action"]
        options = data["options"]
        requested_model = options.get(f"model", None)

        # do model reload checks here

    
        sequential_cpu_offload_changed = self.use_enable_sequential_cpu_offload != (options.get("use_enable_sequential_cpu_offload", True) is True)
        model_changed = (self.model is not None and self.model != requested_model)

        if (self.is_pipe_loaded and (sequential_cpu_offload_changed)) or model_changed:  # model change
            if model_changed:
                self.logger.info(f"Model changed, reloading model" + f" (from {self.model} to {requested_model})")
            if sequential_cpu_offload_changed:
                self.logger.info(f"Sequential cpu offload changed, reloading model")
            self.reload_model = True
            self.clear_scheduler()
            self.clear_controlnet()

        if ((self.controlnet_loaded and not self.enable_controlnet) or
           (not self.controlnet_loaded and self.enable_controlnet)):
            self.initialized = False

        if self.prompt != options.get(f"prompt") or \
           self.negative_prompt != options.get(f"negative_prompt") or \
           action != self.action or \
           self.reload_model:
            self._prompt_embeds = None
            self._negative_prompt_embeds = None

        self.data = data if data is not None else self.data
        torch.backends.cuda.matmul.allow_tf32 = self.use_tf32

    def send_error(self, message):
        self.emit(SignalCode.LOG_ERROR_SIGNAL, message)

    def error_handler(self, error):
        message = str(error)
        if "got an unexpected keyword argument 'image'" in message and self.action in ["outpaint", "pix2pix", "depth2img"]:
            message = f"This model does not support {self.action}"
        traceback.print_exc()
        self.logger.error(error)
        self.emit(SignalCode.LOG_ERROR_SIGNAL, message)

    def initialize_safety_checker(self, local_files_only=None):
        local_files_only = self.local_files_only if local_files_only is None else local_files_only

        if (
            not hasattr(self.pipe, "safety_checker") or
            not self.pipe.safety_checker
        ) and "path" in self.safety_checker_model:
            self.logger.info(f"Initializing safety checker with {self.safety_checker_model}")
            try:
                self.pipe.safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                    self.safety_checker_model["path"],
                    local_files_only=local_files_only,
                    torch_dtype=self.data_type
                )
            except OSError:
                self.initialize_safety_checker(local_files_only=False)
            
            try:
                self.pipe.feature_extractor = AutoFeatureExtractor.from_pretrained(
                    self.safety_checker_model["path"],
                    local_files_only=local_files_only,
                    torch_dtype=self.data_type
                )
            except OSError:
                self.initialize_safety_checker(local_files_only=False)

    def load_safety_checker(self):
        if not self.pipe:
            return
        if not self.do_nsfw_filter or self.action in ["depth2img"]:
            self.logger.info("Disabling safety checker")
            self.pipe.safety_checker = None
        elif self.pipe.safety_checker is None:
            self.logger.info("Loading safety checker")
            self.pipe.safety_checker = self.safety_checker
            if self.pipe.safety_checker:
                self.pipe.safety_checker.to(self.device)

    def do_sample(self, **kwargs):
        self.logger.info(f"Sampling {self.action}")

        if self.is_vid_action:
            message = "Generating video"
        else:
            message = "Generating image"

        self.emit(SignalCode.LOG_STATUS_SIGNAL, message)

        try:
            output = self.call_pipe(**kwargs)
        except Exception as e:
            error_message = str(e)
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                error_message = self.cuda_error_message
            elif "Scheduler.step() got an unexpected keyword argument" in str(e):
                error_message = "Invalid scheduler"
                self.clear_scheduler()
            self.log_error(error_message)
            output = None

        if self.is_vid_action:
            return self.handle_txt2vid_output(output)
        else:
            nsfw_content_detected = None
            images = None
            if output:
                try:
                    images = output.images
                except AttributeError:
                    self.logger.error("Unable to get images from output")
                if self.action_has_safety_checker:
                    try:
                        nsfw_content_detected = output.nsfw_content_detected
                    except AttributeError:
                        self.logger.error("Unable to get nsfw_content_detected from output")
            return images, nsfw_content_detected

    def generate_latents(self):
        width_scale = self.width / 512
        height_scale = self.height / 512
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

    def call_pipe(self, **kwargs):
        """
        Generate an image using the pipe
        :param kwargs:
        :return:
        """
        args = {
            "num_inference_steps": self.steps,
            "guidance_scale": self.guidance_scale,
            "callback": self.callback,
        }
        
        if self.do_add_lora_to_pipe:
            try:
                self.add_lora_to_pipe()
            except Exception as _e:
                self.error_handler("Selected LoRA are not supported with this model")
                self.reload_model = True
                return
        
        if self.is_upscale:
            args.update({
                "prompt": self.prompt,
                "negative_prompt": self.negative_prompt,
                "image": kwargs.get("image"),
                "generator": self.generator(),
            })
        elif self.is_vid_action:
            args.update({
                "prompt": self.prompt,
                "negative_prompt": self.negative_prompt,
            })
        if self.use_compel:
            try:
                args["prompt_embeds"] = self.prompt_embeds
            except Exception as _e:
                self.logger.warning("prompt_embeds failed: " + str(_e))
                args.update({
                    "prompt": self.prompt,
                })
        else:
            args.update({
                "prompt": self.prompt,
            })
        if self.use_compel:
            try:
                args["negative_prompt_embeds"] = self.negative_prompt_embeds
            except Exception as _e:
                self.logger.warning("negative_prompt_embeds failed: " + str(_e))
                args.update({
                    "negative_prompt": self.negative_prompt,
                })
        else:
            args.update({
                "negative_prompt": self.negative_prompt,
            })
        args["callback_steps"] = 1
        
        if not self.is_upscale:
            args.update(kwargs)
        
        if not self.is_pix2pix and len(self.available_lora) > 0 and len(self.loaded_lora) > 0:
            args["cross_attention_kwargs"] = {"scale": 1.0}

        if self.enable_controlnet:
            self.logger.info(f"Setting up controlnet")
            args = self.load_controlnet_arguments(**args)

        self.load_safety_checker()

        if self.is_vid_action:
            return self.call_pipe_txt2vid(**args)

        if not self.is_outpaint and not self.is_vid_action and not self.is_upscale:
            self.latents = self.latents.to(self.device)
            args["latents"] = self.latents

        args["clip_skip"] = self.clip_skip

        with torch.inference_mode():
            for n in range(self.n_samples):
                return self.pipe(**args)

    def read_video(self):
        reader = imageio.get_reader(self.input_video, "ffmpeg")
        frame_count = 8
        pose_images = [Image.fromarray(reader.get_data(i)) for i in range(frame_count)]
        return pose_images

    def call_pipe_txt2vid(self, **kwargs):
        video_length = self.n_samples
        chunk_size = 4
        prompt = kwargs["prompt"]
        negative_prompt = kwargs["negative_prompt"]

        # Generate the video chunk-by-chunk
        result = []
        chunk_ids = np.arange(0, video_length, chunk_size - 1)

        generator = self.generator()
        cur_frame = 0
        for i in range(len(chunk_ids)):
            ch_start = chunk_ids[i]
            ch_end = video_length if i == len(chunk_ids) - 1 else chunk_ids[i + 1]
            frame_ids = list(range(ch_start, ch_end))
            try:
                self.logger.info(f"Generating video with {len(frame_ids)} frames")
                self.emit(SignalCode.LOG_STATUS_SIGNAL, f"Generating video, frames {cur_frame} to {cur_frame + len(frame_ids) - 1} of {self.n_samples}")
                cur_frame += len(frame_ids)
                kwargs = {
                    "prompt": prompt,
                    "video_length": len(frame_ids),
                    "height": self.height,
                    "width": self.width,
                    "num_inference_steps": self.steps,
                    "guidance_scale": self.guidance_scale,
                    "negative_prompt": negative_prompt,
                    "num_videos_per_prompt": 1,
                    "generator": generator,
                    "callback": self.callback,
                    "frame_ids": frame_ids
                }
                if self.is_vid2vid:
                    pose_images = self.read_video()
                    latents = torch.randn(
                        (1, 4, 64, 64),
                        device=torch.device(self.device),
                        torch_dtype=self.data_type,
                    ).repeat(len(pose_images), 1, 1, 1)
                    kwargs["prompt"] = [prompt] * len(pose_images)
                    kwargs["latents"] = latents
                    kwargs["image"] = pose_images
                if self.enable_controlnet:
                    #kwargs["controlnet"] = self.controlnet()
                    kwargs = self.load_controlnet_arguments(**kwargs)
                output = self.pipe(
                    **kwargs
                )
                result.append(output.images[0:])
            except Exception as e:
                self.error_handler(e)
        return {"frames": result}

    def prepare_extra_args(self, _data, image, mask):
        action = self.action
        extra_args = {
        }
        if self.is_txt2img or self.is_vid_action:
            extra_args = {**extra_args, **{
                "width": self.width,
                "height": self.height,
            }}
        if self.is_img2img:
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.strength,
            }}
        elif self.is_pix2pix:
            extra_args = {**extra_args, **{
                "image": image,
                "image_guidance_scale": self.image_guidance_scale,
            }}
        elif self.is_depth2img:
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.strength,
                #"depth_map": self.depth_map
            }}
        elif self.is_vid_action:
            pass
        elif self.is_upscale:
            extra_args = {**extra_args, **{
                "image": image
            }}
        elif self.is_outpaint:
            extra_args = {**extra_args, **{
                "image": image,
                "mask_image": mask,
                "width": self.width,
                "height": self.height,
            }}
        return extra_args

    def sample_diffusers_model(self, data: dict):
        self.logger.info("sample_diffusers_model")
        image = self.image
        mask = self.mask
        nsfw_content_detected = None
        seed_everything(self.seed)
        extra_args = self.prepare_extra_args(data, image, mask)

        # do the sample
        try:
            images, nsfw_content_detected = self.do_sample(**extra_args)
        except Exception as e:
            images = None
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                self.log_error(self.cuda_error_message)
            else:
                self.log_error(e, "Something went wrong while generating image")

        self.final_callback()

        return images, nsfw_content_detected

    def process_prompts(self, data, seed):
        """
        Process the prompts - called before generate (and during in the case of multiple samples)
        :return:
        """
        prompt = data["options"][f"prompt"]
        negative_prompt = data["options"][f"negative_prompt"]
        data["options"][f"prompt"] = [prompt for _ in range(self.batch_size)]
        data["options"][f"negative_prompt"] = [negative_prompt for _ in range(self.batch_size)]
        return data
        prompt_data = self.prompt_data
        self.logger.info(f"Process prompt")
        if self.deterministic_seed:
            prompt = data["options"][f"prompt"]
            if ".blend(" in prompt:
                # replace .blend([0-9.]+, [0-9.]+) with ""
                prompt = re.sub(r"\.blend\([\d.]+, [\d.]+\)", "", prompt)
                # find this pattern r'\("(.*)", "(.*)"\)'
                match = re.search(r'\("(.*)", "(.*)"\)', prompt)
                # get the first and second group
                prompt = match.group(1)
                generated_prompt = match.group(2)
                prompt_data.prompt = prompt
                prompt_data.generated_prompt = generated_prompt
        else:
            prompt = prompt_data.current_prompt \
                if prompt_data.current_prompt and prompt_data.current_prompt != "" \
                else self.prompt
        negative_prompt = prompt_data.current_negative_prompt \
            if prompt_data.current_negative_prompt \
               and prompt_data.current_negative_prompt != "" \
            else self.negative_prompt

        prompt, negative_prompt = prompt_data.build_prompts(
            seed=seed,
            prompt=prompt,
            negative_prompt=negative_prompt,
            batch_size=self.batch_size,
            deterministic_style=self.deterministic_style
        )

        # we only update the prompt embed if prompt or negative prompt has changed
        if negative_prompt != self.current_negative_prompt or prompt != self.current_prompt:
            self.current_negative_prompt = negative_prompt
            self.current_prompt = prompt
            data["options"][f"prompt"] = prompt
            data["options"][f"negative_prompt"] = negative_prompt
            self.clear_prompt_embeds()
            self.process_data(data)
        return data

    def process_data(self, data: dict):
        self.logger.info("Runner: process_data called")
        self.requested_data = data
        self.prepare_options(data)
        self.prepare_scheduler()
        self.prepare_model()
        self.initialize()
        if self.pipe:
            self.change_scheduler()

    def generate(self, data):
        if not self.pipe:
            return
        self.logger.info("generate called")
        self.do_cancel = False
        self.process_data(data)

        self.emit(SignalCode.LOG_STATUS_SIGNAL, f"Applying memory settings")
        self.apply_memory_efficient_settings()

        seed = self.seed
        data = self.process_prompts(data, seed)
        self.current_sample = 1
        images, nsfw_content_detected = self.sample_diffusers_model(data)
        if self.is_vid_action and "video_filename" not in self.requested_data:
            self.requested_data["video_filename"] = self.txt2vid_file
        if self.do_cancel:
            self.do_cancel = False

        self.current_sample = 0
        return self.image_handler(images, self.requested_data, nsfw_content_detected)

    def image_handler(
        self,
        images: List[Image.Image],
        data: dict,
        nsfw_content_detected: List[bool] = None
    ):
        data["original_model_data"] = self.original_model_data or {}
        has_nsfw = True in nsfw_content_detected if nsfw_content_detected is not None else False

        if images:
            tab_section = "stablediffusion"
            data["tab_section"] = tab_section

            do_base64 = data.get("do_base64", False)

            if not has_nsfw:
                # apply filters and convert to base64 if requested
                has_filters = self.filters != {}

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

            if has_nsfw:
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
            request_type=data.get("request_type", None),
            nsfw_content_detected=has_nsfw,
        )

    def final_callback(self):
        total = int(self.steps * self.strength)
        tab_section = "stablediffusion"
        self.emit(SignalCode.SD_PROGRESS_SIGNAL,{
            "step": total,
            "total": total,
            "action": self.action,
            "tab_section": tab_section,
        })

    def callback(self, step: int, _time_step, latents):
        image = None
        data = self.data
        tab_section = "stablediffusion"
        if self.is_vid_action:
            data["video_filename"] = self.txt2vid_file
        steps = int(self.steps * self.strength) if (
                not self.enable_controlnet and
                (self.is_img2img or self.is_depth2img)
        ) else self.steps
        res = {
            "step": step,
            "total": steps,
            "action": self.action,
            "image": image,
            "data": data,
            "tab_section": tab_section,
            "latents": latents
        }
        self.emit(SignalCode.SD_PROGRESS_SIGNAL, res)

    def on_unload_stablediffusion_signal(self):
        self.unload()

    def unload(self):
        self.unload_model()
        self.unload_tokenizer()
        clear_memory()

    def unload_model(self):
        self.pipe = None
    
    def unload_tokenizer(self):
        self.tokenizer = None

    def process_upscale(self, data: dict):
        self.logger.info("Processing upscale")
        image = self.input_image
        results = []
        if image:
            self.move_pipe_to_cpu()
            results = RealESRGAN(
                input=image,
                output=None,
                model_name='RealESRGAN_x4plus', 
                denoise_strength=self.options.get("denoise_strength", 0.5), 
                face_enhance=self.options.get("face_enhance", True),
            ).run()
            clear_memory()
        else:
            self.log_error("No image found, unable to upscale")
        # check if results is a list
        if not isinstance(results, list):
            return [results]
        return results

    def generator_sample(self, data: dict):
        self.process_data(data)

        if self.is_upscale:
            images = self.process_upscale(data)
            self.current_sample = 0
            self.do_cancel = False
            return self.image_handler(images, self.requested_data, None)

        if not self.pipe:
            self.logger.info("pipe is None")
            return

        self.emit(SignalCode.LOG_STATUS_SIGNAL, f"Generating {'video' if self.is_vid_action else 'image'}")

        action = "depth2img" if data["action"] == "depth" else data["action"]

        try:
            self.initialized = self.__dict__[action] is not None
        except KeyError:
            self.logger.info(f"{action} model has not been initialized yet")
            self.initialized = False

        error = None
        error_message = ""
        try:
            yield self.generate(data)
        except TypeError as e:
            error_message = f"TypeError during generation {self.action}"
            print(e)
            error = e
        except Exception as e:
            error = e
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
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
            self._current_model = ""
            self.local_files_only = True

    def on_sd_cancel_signal(self):
        self.do_cancel = True

    def log_error(self, error, message=None):
        message = str(error) if not message else message
        traceback.print_exc()
        self.error_handler(message)

    def load_controlnet_from_ckpt(self, pipeline):
        self.logger.info("Loading controlnet from ckpt")
        pipeline = self.controlnet_action_diffuser(
            vae=pipeline.vae,
            text_encoder=pipeline.text_encoder,
            tokenizer=pipeline.tokenizer,
            unet=pipeline.unet,
            controlnet=self.controlnet(),
            scheduler=pipeline.scheduler,
            safety_checker=pipeline.safety_checker,
            feature_extractor=pipeline.feature_extractor
        )
        self.controlnet_loaded = True
        return pipeline

    def load_controlnet(self):
        standard_image_settings = self.settings["standard_image_settings"]
        controlnet_name = standard_image_settings["controlnet"]
        controlnet_model = self.controlnet_model_by_name(controlnet_name)
        self.logger.info(f"Loading controlnet {self.controlnet_type} self.controlnet_model {controlnet_model}")
        self._controlnet = None
        self.current_controlnet_type = self.controlnet_type
        controlnet = StableDiffusionControlNetPipeline.from_pretrained(
            controlnet_model,
            torch_dtype=self.data_type
        )
        # self.load_controlnet_scheduler()
        return controlnet

    def preprocess_for_controlnet(self, image):
        if self.current_controlnet_type != self.controlnet_type or not self.processor:
            self.logger.info("Loading controlnet processor " + self.controlnet_type)
            self.current_controlnet_type = self.controlnet_type
            self.logger.info("Controlnet: Processing image")
            self.processor = Processor(self.controlnet_type)
        if self.processor:
            self.logger.info("Controlnet: Processing image")
            image = self.processor(image)
            # resize image to width and height
            image = image.resize((self.width, self.height))
            return image
        self.logger.error("No controlnet processor found")

    def load_controlnet_arguments(self, **kwargs):
        if not self.is_vid_action:
            image_key = "image" if self.is_txt2img else "control_image"
            kwargs = {**kwargs, **{
                image_key: self.controlnet_image,
            }}

        kwargs = {**kwargs, **{
            "guess_mode": self.controlnet_guess_mode,
            "control_guidance_start": self.control_guidance_start,
            "control_guidance_end": self.control_guidance_end,
            "controlnet_conditioning_scale": self.controlnet_conditioning_scale,
        }}
        return kwargs

    def unload_unused_models(self):
        self.logger.info("Unloading unused models")
        for action in [
            "txt2img",
            "img2img",
            "pix2pix",
            "outpaint",
            "depth2img",
            "txt2vid",
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

    def load_model(self):
        self.logger.info("Loading model")
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        kwargs = {}

        # if self.current_model_branch:
        #     kwargs["variant"] = self.current_model_branch
        # elif self.data_type == torch.float16:
        #     kwargs["variant"] = "fp16"

        if self.do_reuse_pipeline and not self.reload_model:
            self.initialized = True

        # move all models except for our current action to the CPU
        if not self.initialized or self.reload_model:
            self.unload_unused_models()
        elif self.pipe is None and self.do_reuse_pipeline or self.pipe and self.do_load_controlnet != self.current_load_controlnet:
            self.reuse_pipeline(self.do_load_controlnet)

        self.current_load_controlnet = self.do_load_controlnet

        if self.pipe is None or self.reload_model:
            kwargs["from_safetensors"] = self.is_safetensors
            self.logger.info(f"Loading model from scratch {self.reload_model}")
            self.reset_applied_memory_settings()
            self.send_model_loading_message(self.model_path)

            if self.enable_controlnet and not self.is_vid2vid:
                kwargs["controlnet"] = self.controlnet()

            if self.is_single_file:
                try:
                    self.pipe = self.load_ckpt_model()
                except OSError as e:
                    self.handle_missing_files(self.action)
            else:
                self.logger.info(f"Loading model {self.model_path} from PRETRAINED")

                scheduler = self.load_scheduler()
                if scheduler:
                    kwargs["scheduler"] = scheduler

                pipeline_classname_ = StableDiffusionPipeline
                if self.action == "depth2img":
                    pipeline_classname_ = StableDiffusionDepth2ImgPipeline
                elif self.action == "outpaint":
                    pipeline_classname_ = AutoPipelineForInpainting
                elif self.action == "pix2pix":
                    pipeline_classname_ = StableDiffusionInstructPix2PixPipeline
                
                self.pipe = pipeline_classname_.from_pretrained(
                    self.model_path,
                    torch_dtype=self.data_type,
                    **kwargs
                )

            if self.pipe is None:
                self.emit(SignalCode.LOG_ERROR_SIGNAL, "Failed to load model")
                return
        
            """
            Initialize pipe for video to video zero
            """
            if self.pipe and self.is_vid2vid:
                self.logger.info("Initializing pipe for vid2vid")
                self.pipe.unet.set_attn_processor(CrossFrameAttnProcessor(batch_size=2))
                self.pipe.controlnet.set_attn_processor(CrossFrameAttnProcessor(batch_size=2))

            if self.is_outpaint:
                self.logger.info("Initializing vae for inpaint / outpaint")
                self.pipe.vae = AsymmetricAutoencoderKL.from_pretrained(
                    self.inpaint_vae_model["path"],
                    torch_dtype=self.data_type
                )

            if not self.is_depth2img:
                self.initialize_safety_checker()

            self.controlnet_loaded = self.enable_controlnet

            if not self.is_depth2img:
                self.safety_checker = self.pipe.safety_checker

            # store the model_path
            self.pipe.model_path = self.model_path

            # move pipe components to device and initialize text encoder for clip skip
            self.pipe.vae.to(self.data_type)
            self.pipe.text_encoder.to(self.data_type)
            self.pipe.unet.to(self.data_type)

            #self.load_learned_embed_in_clip()

    def load_ckpt_model(self):
        self.logger.info(f"Loading ckpt file {self.model_path}")
        pipeline = self.download_from_original_stable_diffusion_ckpt(path=self.model_path)
        return pipeline

    def get_pipeline_action(self, action=None):
        action = self.action if not action else action
        if action == "txt2img" and self.is_img2img:
            action = "img2img"
        return action

    def download_from_original_stable_diffusion_ckpt(self, path, local_files_only=None):
        local_files_only = self.local_files_only if local_files_only is None else local_files_only
        pipe = None
        try:
            pipe = download_from_original_stable_diffusion_ckpt(
                checkpoint_path_or_dict=path,
                device=self.device,
                scheduler_type="ddim",
                from_safetensors=self.is_safetensors,
                local_files_only=local_files_only,
                extract_ema=False,
                #vae=self.load_vae(),
                config_files={
                    "v1": "v1.yaml",
                    "v2": "v2.yaml",
                    "xl": "sd_xl_base.yaml",
                    "xl_refiner": "sd_xl_refiner.yaml"
                }
            )
            if self.enable_controlnet:
                pipe = self.load_controlnet_from_ckpt(pipe)
            old_model_path = self.current_model
            self.current_model = path
            pipe.scheduler = self.load_scheduler(config=pipe.scheduler.config)
            self.current_model = old_model_path
        except ValueError:
            if local_files_only:
                # missing required files, attempt again with online access
                return self.download_from_original_stable_diffusion_ckpt(
                    path, 
                    local_files_only=False
                )
        except Exception as e:
            self.logger.error(f"Failed to load model from ckpt: {e}")
        return pipe

    def clear_controlnet(self):
        self.logger.info("Clearing controlnet")
        self._controlnet = None
        clear_memory()
        self.reset_applied_memory_settings()
        self.controlnet_loaded = False
    
    def load_vae(self):
        return ConsistencyDecoderVAE.from_pretrained(
            self.vae_path, 
            torch_dtype=self.data_type
        )

    def reuse_pipeline(self, do_load_controlnet):
        self.logger.info("Reusing pipeline")
        pipe = None
        if self.is_txt2img:
            pipe = self.img2img if self.txt2img is None else self.txt2img
        elif self.is_img2img:
            pipe = self.txt2img if self.img2img is None else self.img2img
        if pipe is None:
            self.logger.warning("Failed to reuse pipeline")
            self.clear_controlnet()
            return
        kwargs = pipe.components

        # either load from a pretrained model or from a pipe
        if do_load_controlnet and not self.is_vid2vid:
            self.controlnet_loaded = True
            pipe = self.load_controlnet_from_ckpt(pipe)
            kwargs["controlnet"] = self.controlnet()
        else:
            if "controlnet" in kwargs:
                del kwargs["controlnet"]
            self.clear_controlnet()

            if self.is_single_file:
                #pipe = self.download_from_original_stable_diffusion_ckpt(self.model_path)
                pipeline_action = self.get_pipeline_action()

                pipeline_class_ = None
                if self.model_version == "SDXL 1.0":
                    pipeline_class_ = StableDiffusionXLPipeline
                else:
                    pipeline_class_ = StableDiffusionPipeline

                pipe = pipeline_class_.from_single_file(
                    self.model_path,
                )
                return pipe
            else:
                components = pipe.components
                if "controlnet" in components:
                    del components["controlnet"]
                if self.is_vid2vid:
                    components["controlnet"] = self.controlnet()
                
                pipe = AutoPipelineForText2Image.from_pretrained(
                    self.model_path,
                    **components
                )

        if self.is_txt2img:
            self.txt2img = pipe
            self.img2img = None
        elif self.is_img2img:
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
        self.logger.info("Prepare model")
        # get model and switch to it

        # get models from database
        model_name = self.options.get(f"model", None)

        self.send_model_loading_message(model_name)

        self._previous_model = self.current_model
        if self.is_single_file:
            self.current_model = model_name
        else:
            self.current_model = self.options.get(f"model_path", None)
            self.current_model_branch = self.options.get(f"model_branch", None)

        if self.do_unload_controlnet:
            self.unload_controlnet()

    def unload_controlnet(self):
        if self.pipe:
            self.logger.info("Unloading controlnet")
            self.pipe.controlnet = None
        self.controlnet_loaded = False

    def handle_missing_files(self, action):
        if not self.attempt_download:
            if self.is_ckpt_model or self.is_safetensors:
                self.logger.info("Required files not found, attempting download")
            else:
                traceback.print_exc()
                self.logger.info("Model not found, attempting download")
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
            return self.generator_sample(self.requested_data)
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
