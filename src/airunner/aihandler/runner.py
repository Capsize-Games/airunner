import base64
import os
import gc
import re
from io import BytesIO
import traceback
import torch
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests
from torchvision import transforms

from airunner.aihandler.auto_pipeline import AutoImport
from airunner.aihandler.enums import FilterType
from airunner.aihandler.mixins.kandinsky_mixin import KandinskyMixin
from airunner.aihandler.logger import Logger as logger
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.txttovideo_mixin import TexttovideoMixin
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.aihandler.settings import MAX_SEED, LOG_LEVEL, AIRUNNER_ENVIRONMENT
from airunner.aihandler.enums import MessageCode
from airunner.aihandler.settings_manager import ApplicationData, SettingsManager
from airunner.prompt_builder.prompt_data import PromptData

from controlnet_aux.processor import Processor

from diffusers.utils import export_to_gif
from diffusers.pipelines.stable_diffusion.convert_from_ckpt import \
    download_from_original_stable_diffusion_ckpt


class SDRunner(
    MergeMixin,
    LoraMixin,
    MemoryEfficientMixin,
    EmbeddingMixin,
    TexttovideoMixin,
    CompelMixin,
    SchedulerMixin,
    KandinskyMixin
):
    _current_model: str = ""
    _previous_model: str = ""
    _initialized: bool = False
    _current_sample = 0
    _reload_model: bool = False
    do_cancel = False
    current_model_branch = None
    state = None
    _local_files_only = True
    lora_loaded = False
    loaded_lora = []
    _settings = None
    _action = None
    embeds_loaded = False
    _compel_proc = None
    _prompt_embeds = None
    _negative_prompt_embeds = None
    _data = {
        "options": {}
    }
    current_prompt = None
    current_negative_prompt = None
    _model = None
    requested_data = None
    current_clip_skip = 0
    _allow_online_mode = None
    current_load_controlnet = False

    # controlnet atributes
    processor = None
    current_controlnet_type = None
    controlnet_loaded = False
    attempt_download = False
    downloading_controlnet = False
    safety_checker_model = ""
    text_encoder_model = ""
    inpaint_vae_model = ""
    _controlnet_image = None
    # end controlnet atributes

    def controlnet(self):
        if self._controlnet is None \
            or self.current_controlnet_type != self.controlnet_type:
            self._controlnet = self.load_controlnet()
        return self._controlnet

    @property
    def controlnet_model(self):
        # read default and custom from application_data
        data = self.application_data.settings.controlnet_models.get()
        # combine default and custom controlnet_models
        data = {**data["default"], **data["custom"]}
        try:
            return data[self.controlnet_type]
        except KeyError:
            raise Exception(f"Unknown controlnet type {self.controlnet_type}")

    @property
    def controlnet_type(self):
        controlnet_type = self.options.get("controlnet", "canny")
        return controlnet_type.replace(" ", "_")

    @property
    def allow_online_when_missing_files(self):
        """
        This settings prevents the application from going online when a file is missing.
        :return:
        """
        if self._allow_online_mode is None:
            self._allow_online_mode = self.settings_manager.settings.allow_online_mode.get()
        return self._allow_online_mode

    @property
    def local_files_only(self):
        return self._local_files_only

    @local_files_only.setter
    def local_files_only(self, value):
        logger.info("Setting local_files_only to %s" % value)
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

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def options(self):
        return self.data.get("options", {})

    @property
    def seed(self):
        return self.options.get(f"seed", 42) + self.current_sample

    @property
    def deterministic_seed(self):
        return self.options.get("deterministic_seed", None)

    @property
    def batch_size(self):
        return 4 if self.deterministic_generation else 1

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
        return self.options.get(f"image_scale", 1.5)

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
        if self.is_txt2vid or self.is_upscale:
            return 1
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
        return self.options.get(f"strength", 1)

    @property
    def image(self):
        return self.options.get(f"image", None)

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
    def do_nsfw_filter(self):
        return self.options.get("do_nsfw_filter", True) is True

    @property
    def use_compel(self):
        return not self.use_enable_sequential_cpu_offload and \
               not self.is_txt2vid and \
               not self.is_sd_xl and \
               not self.is_shapegif

    @property
    def use_tiled_vae(self):
        if self.use_kandinsky:
            return False
        return self.options.get("use_tiled_vae", False) is True

    @property
    def use_accelerated_transformers(self):
        if self.use_kandinsky:
            return False
        return self.options.get("use_accelerated_transformers", False) is True

    @property
    def use_torch_compile(self):
        return self.options.get("use_torch_compile", False) is True

    @property
    def is_sd_xl(self):
        return self.model == "Stable Diffusion XL 0.9"

    @property
    def model(self):
        return self.options.get(f"model", None)

    @property
    def do_mega_scale(self):
        # return self.is_superresolution
        return False

    @property
    def action(self):
        return self.data.get("action", None)

    @property
    def action_has_safety_checker(self):
        return self.action not in ["depth2img", "superresolution"]

    @property
    def is_outpaint(self):
        return self.action == "outpaint"

    @property
    def is_txt2img(self):
        return self.action == "txt2img"

    @property
    def is_zeroshot(self):
        return self.options.get("zeroshot", False) is True

    @property
    def is_shapegif(self):
        return self.options.get(f"generator_section") == "shapegif"

    @property
    def is_txt2vid(self):
        return self.action == "txt2vid"

    @property
    def is_vid2vid(self):
        return self.action == "vid2vid"

    @property
    def is_upscale(self):
        return self.action == "upscale"

    @property
    def is_img2img(self):
        return self.action == "img2img"

    @property
    def is_depth2img(self):
        return self.action == "depth2img"

    @property
    def is_pix2pix(self):
        return self.action == "pix2pix"

    @property
    def is_superresolution(self):
        return self.action == "superresolution"

    @property
    def use_interpolation(self):
        return self.options.get("use_interpolation", False)

    @property
    def interpolation_data(self):
        return self.options.get("interpolation_data", None)

    @property
    def deterministic_generation(self):
        return self.options.get("deterministic_generation", False)

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
    def upscale_model_path(self):
        return self.options.get("upscale_model_path", None)

    @property
    def model_path(self):
        return self.model_data["path"]

    @property
    def cuda_error_message(self):
        if self.is_superresolution and self.scheduler_name == "DDIM":
            return f"Unable to run the model at {self.width}x{self.height} resolution using the DDIM scheduler. Try changing the scheduler to LMS or PNDM and try again."
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
        elif self.is_superresolution:
            return self.superresolution is not None
        elif self.is_txt2vid:
            return self.txt2vid is not None
        elif self.is_upscale:
            return self.upscale is not None

    @property
    def enable_controlnet(self):
        if self.image is None and self.controlnet_image is None:
            return False
        return self.options.get("enable_controlnet", False)

    @property
    def controlnet_conditioning_scale(self):
        return self.options.get(f"controlnet_conditioning_scale", 1000) / 1000.0

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
        elif self.is_superresolution:
            return self.superresolution
        elif self.is_txt2vid:
            return self.txt2vid
        elif self.is_upscale:
            return self.upscale
        else:
            raise ValueError(f"Invalid action {self.action} unable to get pipe")

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
        elif self.is_superresolution:
            self.superresolution = value
        elif self.is_txt2vid:
            self.txt2vid = value
        elif self.is_upscale:
            self.upscale = value
        else:
            raise ValueError(f"Invalid action {self.action} unable to set pipe")

    @property
    def cuda_is_available(self):
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
        return not self.use_kandinsky \
               and not self.is_txt2vid \
               and not self.is_upscale \
               and not self.is_superresolution

    @property
    def controlnet_action_diffuser(self):
        from diffusers import (
            StableDiffusionControlNetPipeline,
            StableDiffusionControlNetImg2ImgPipeline,
            StableDiffusionControlNetInpaintPipeline,
        )
        if self.is_txt2img or self.is_zeroshot:
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

        if not controlnet_image and self.image:
            controlnet_image = self.preprocess_for_controlnet(self.image)
            self.send_message({
                "image": controlnet_image,
                "data": {
                    "controlnet_image": controlnet_image
                },
                "request_type": None
            }, MessageCode.CONTROLNET_IMAGE_GENERATED)

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
        return (
            (self.controlnet_loaded and not self.enable_controlnet) or
            (not self.controlnet_loaded and not self.enable_controlnet)
        )

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

    def  __init__(self, **kwargs):
        logger.set_level(LOG_LEVEL)
        self.settings_manager = SettingsManager()
        self.application_data = ApplicationData()
        self.safety_checker_model = self.application_data.available_models_by_section("safety_checker")
        self.text_encoder_model = self.application_data.available_models_by_section("text_encoder")
        self.inpaint_vae_model = self.application_data.available_models_by_section("inpaint_vae")

        self.app = kwargs.get("app", None)
        self._message_var = kwargs.get("message_var", None)
        self._message_handler = kwargs.get("message_handler", None)
        self._safety_checker = None
        self._controlnet = None
        self.txt2img = None
        self.img2img = None
        self.pix2pix = None
        self.outpaint = None
        self.depth2img = None
        self.superresolution = None
        self.txt2vid = None
        self.upscale = None

    @staticmethod
    def latents_to_image(latents: torch.Tensor):
        image = latents.permute(0, 2, 3, 1)
        image = image.detach().cpu().numpy()
        image = image[0]
        image = (image * 255).astype(np.uint8)
        image = Image.fromarray(image)
        return image

    @staticmethod
    def clear_memory():
        logger.info("Clearing memory")
        torch.cuda.empty_cache()
        gc.collect()

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
    def image_to_base64(image):
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

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
            logger.info("Initializing")
            self.compel_proc = None
            self.prompt_embeds = None
            self.negative_prompt_embeds = None
            if self.reload_model:
                self.reset_applied_memory_settings()
            self.load_model()
            self.reload_model = False
            self.initialized = True

    def generator(self, device=None, seed=None):
        device = self.device if not device else device
        seed = self.seed if not seed else seed
        return torch.Generator(device=device).manual_seed(seed)

    def prepare_options(self, data):
        logger.info(f"Preparing options")
        action = data["action"]
        options = data["options"]
        requested_model = options.get(f"model", None)
        enable_controlnet = options.get("enable_controlnet", False)

        # do model reload checks here
        if (self.is_pipe_loaded and (  # memory options change
            self.use_enable_sequential_cpu_offload != options.get("use_enable_sequential_cpu_offload", True))) or \
           (self.model is not None and self.model != requested_model):  # model change
            self.reload_model = True

        if ((self.controlnet_loaded and not enable_controlnet) or
           (not self.controlnet_loaded and enable_controlnet)):
            self.initialized = False

        if self.prompt != options.get(f"prompt") or \
           self.negative_prompt != options.get(f"negative_prompt") or \
           action != self.action or \
           self.reload_model:
            self._prompt_embeds = None
            self._negative_prompt_embeds = None

        self.data = data
        if not self.use_kandinsky:
            torch.backends.cuda.matmul.allow_tf32 = self.use_tf32

    def send_error(self, message):
        self.send_message(message, MessageCode.ERROR)

    def send_message(self, message, code=None):
        code = code or MessageCode.STATUS
        formatted_message = {
            "code": code,
            "message": message
        }
        if self._message_handler:
            self._message_handler(formatted_message)
        elif self._message_var:
            self._message_var.emit(formatted_message)

    def error_handler(self, error):
        message = str(error)
        if "got an unexpected keyword argument 'image'" in message and self.action in ["outpaint", "pix2pix",
                                                                                       "depth2img"]:
            message = f"This model does not support {self.action}"
        traceback.print_exc()
        logger.error(error)
        self.send_message(message, MessageCode.ERROR)

    def initialize_safety_checker(self):
        if not hasattr(self.pipe, "safety_checker") or not self.pipe.safety_checker:
            self.pipe.safety_checker = self.from_pretrained(
                pipeline_action="safety_checker",
                model=self.safety_checker_model
            )
            self.pipe.feature_extractor = self.from_pretrained(
                pipeline_action="feature_extractor",
                model=self.safety_checker_model
            )

    def load_safety_checker(self):
        if not self.pipe:
            return
        if not self.do_nsfw_filter:
            logger.info("Disabling safety checker")
            self.pipe.safety_checker = None
        elif self.pipe.safety_checker is None:
            logger.info("Loading safety checker")
            self.pipe.safety_checker = self.safety_checker
            if self.pipe.safety_checker:
                self.pipe.safety_checker.to(self.device)

    def do_sample(self, **kwargs):
        logger.info(f"Sampling {self.action}")
        self.send_message(f"Generating image")

        try:
            logger.info(f"Generating image")
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

        if self.is_zeroshot:
            return self.handle_zeroshot_output(output)
        if self.is_txt2vid:
            return self.handle_txt2vid_output(output)
        else:
            nsfw_content_detected = None
            images = None
            if output:
                try:
                    images = output.images
                except AttributeError:
                    pass
                if self.action_has_safety_checker:
                    try:
                        nsfw_content_detected = output.nsfw_content_detected
                    except AttributeError:
                        pass
            return images, nsfw_content_detected

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
                "generator": torch.manual_seed(self.seed),
            })
        elif self.is_txt2vid:
            args.update({
                "prompt": self.prompt,
                "negative_prompt": self.negative_prompt,
            })
            if not self.is_zeroshot:
                args["num_frames"] = self.n_samples
        elif not self.use_kandinsky:
            if self.use_compel:
                try:
                    args.update({
                        "prompt_embeds": self.prompt_embeds,
                        "negative_prompt_embeds": self.negative_prompt_embeds,
                    })
                except Exception as _e:
                    logger.warning("Compel failed: " + str(_e))
                    args.update({
                        "prompt": self.prompt,
                        "negative_prompt": self.negative_prompt,
                    })
            else:
                args.update({
                    "prompt": self.prompt,
                    "negative_prompt": self.negative_prompt,
                })
        if not self.is_upscale:
            args.update(kwargs)
        if self.use_kandinsky:
            return self.kandinsky_call_pipe(**kwargs)
        if not self.is_pix2pix and len(self.available_lora) > 0 and len(self.loaded_lora) > 0:
            args["cross_attention_kwargs"] = {"scale": 1.0}

        if self.deterministic_generation:
            if self.is_txt2img:
                if self.deterministic_seed:
                    generator = [self.generator(seed=self.seed) for _i in range(self.batch_size)]
                else:
                    generator = [self.generator(seed=self.seed + i) for i in range(self.batch_size)]
                args["generator"] = generator

            if not self.is_upscale and not self.is_superresolution and not self.is_txt2vid:
                args["num_images_per_prompt"] = 1

        if self.enable_controlnet:
            logger.info(f"Setting up controlnet")
            args = self.load_controlnet_arguments(**args)

        self.load_safety_checker()

        if self.is_zeroshot:
            return self.call_pipe_zeroshot(**args)

        if self.is_shapegif:
            return self.call_shapegif_pipe()

        # print stacktrace
        return self.pipe(**args)

    def call_shapegif_pipe(self):
        kwargs = {
            "num_images_per_prompt": 1,
            "num_inference_steps": self.steps,
            "generator": self.generator(),
            "guidance_scale": self.guidance_scale,
            "frame_size": self.width,
        }

        if self.is_txt2img:
            kwargs["prompt"] = self.prompt

        if self.is_img2img:
            kwargs["image"] = self.image

        images = self.pipe(**kwargs).images

        try:
            path = self.gif_path
        except AttributeError:
            path = None

        if not path or path == "":
            try:
                path = self.image_path
            except AttributeError:
                path = None

        if not path or path == "":
            try:
                path = self.model_base_path
            except AttributeError:
                path = None

        if not path or path == "":
            raise Exception("No path to save images found")

        for image in images:
            export_to_gif(
                image,
                os.path.join(
                    path,
                    f"{self.prompt}_{self.seed}.gif")
            )
        return {
            "images": None,
            "nsfw_content_detected": None,
        }

    def call_pipe_zeroshot(self, **kwargs):
        video_length = self.n_samples
        chunk_size = 4
        prompt = kwargs["prompt"]
        negative_prompt = kwargs["negative_prompt"]

        # kwargs["output_type"] = "numpy"
        kwargs["generator"] = self.generator()

        # Generate the video chunk-by-chunk
        result = []
        chunk_ids = np.arange(0, video_length, chunk_size - 1)

        generator = self.generator()
        for i in range(len(chunk_ids)):
            ch_start = chunk_ids[i]
            ch_end = video_length if i == len(chunk_ids) - 1 else chunk_ids[i + 1]
            frame_ids = [0] + list(range(ch_start, ch_end))
            try:
                output = self.pipe(
                    prompt=prompt,
                    width=self.width,
                    height=self.height,
                    num_inference_steps=self.steps,
                    guidance_scale=self.guidance_scale,
                    negative_prompt=negative_prompt,
                    video_length=len(frame_ids),
                    callback=self.callback,
                    motion_field_strength_x=12,
                    motion_field_strength_y=12,
                    generator=generator,
                    frame_ids=frame_ids
                )
            except Exception as e:
                self.error_handler(e)
                return None
            result.append(output.images[1:])
        return {"frames": result}

    def prepare_extra_args(self, _data, image, mask):
        action = self.action
        extra_args = {
        }
        if action == "txt2img" or action == "txt2vid":
            extra_args = {**extra_args, **{
                "width": self.width,
                "height": self.height,
            }}
        if action == "img2img":
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.strength,
            }}
        elif action == "pix2pix":
            extra_args = {**extra_args, **{
                "image": image,
                "image_guidance_scale": self.image_guidance_scale,
            }}
        elif action == "depth2img":
            extra_args = {**extra_args, **{
                "image": image,
                "strength": self.strength,
            }}
        elif action == "txt2vid":
            pass
        elif action == "upscale":
            extra_args = {**extra_args, **{
                "image": image,
                "image_guidance_scale": self.image_guidance_scale,
            }}
        elif self.is_superresolution:
            extra_args = {**extra_args, **{
                "image": image,
            }}
        elif action == "outpaint":
            extra_args = {**extra_args, **{
                "image": image,
                "mask_image": mask,
                "width": self.width,
                "height": self.height,
            }}
        return extra_args

    def sample_diffusers_model(self, data: dict):
        from pytorch_lightning import seed_everything
        image = self.image
        mask = self.mask
        nsfw_content_detected = None
        seed_everything(self.seed)
        extra_args = self.prepare_extra_args(data, image, mask)

        # do the sample
        try:
            if self.do_mega_scale:
                return self.do_mega_scale_sample(data, image, extra_args)
            else:
                images, nsfw_content_detected = self.do_sample(**extra_args)
        except Exception as e:
            images = None
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                self.log_error(self.cuda_error_message)
            else:
                self.log_error(e, "Something went wrong while generating image")

        self.final_callback()

        return images, nsfw_content_detected

    def do_mega_scale_sample(self, data, image, extra_args):
        # first we will downscale the original image using the PIL algorithm
        # called "bicubic" which is a high quality algorithm
        # then we will upscale the image using the super resolution model
        # then we will upscale the image using the PIL algorithm called "bicubic"
        # to the desired size
        # the new dimensions of scaled_w and scaled_h should be the width and height
        # of the image that current image but aspect ratio scaled to 128
        # so if the image is 256x256 then the scaled_w and scaled_h should be 128x128 but
        # if the image is 512x256 then the scaled_w and scaled_h should be 128x64

        max_in_width = 512
        scale_size = 256
        in_width = self.width
        in_height = self.height
        original_image_width = data["options"]["original_image_width"]
        original_image_height = data["options"]["original_image_height"]

        if original_image_width > max_in_width:
            scale_factor = max_in_width / original_image_width
            in_width = int(original_image_width * scale_factor)
            in_height = int(original_image_height * scale_factor)
            scale_size = int(scale_size * scale_factor)

        if in_width > max_in_width:
            # scale down in_width and in_height by scale_size
            # but keep the aspect ratio
            in_width = scale_size
            in_height = int((scale_size / original_image_width) * original_image_height)

        # now we will scale the image to the new dimensions
        # and then upscale it using the super resolution model
        # and then downscale it using the PIL bicubic algorithm
        # to the original dimensions
        # this will give us a high quality image
        scaled_w = int(in_width * (scale_size / in_height))
        scaled_h = scale_size
        downscaled_image = image.resize((scaled_w, scaled_h), Image.BILINEAR)
        extra_args["image"] = downscaled_image
        upscaled_image = self.do_sample(**extra_args)
        # upscale back to self.width and self.height
        image = upscaled_image  # .resize((original_image_width, original_image_height), Image.BILINEAR)

        return [image]

    def process_prompts(self, data, seed):
        """
        Process the prompts - called before generate (and during in the case of multiple samples)
        :return:
        """
        prompt_data = self.prompt_data
        logger.info("Process prompt")
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
            is_deterministic=True if self.deterministic_seed else False,
            is_batch=self.deterministic_generation,
            batch_size=self.batch_size
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
        self.requested_data = data
        self.prepare_options(data)
        self.prepare_scheduler()
        self.prepare_model()
        self.initialize()
        if self.pipe:
            self.change_scheduler()

    def generate(self, data: dict):
        if not self.pipe and not self.use_kandinsky:
            return
        logger.info("generate called")
        self.do_cancel = False
        self.process_data(data)

        if not self.use_kandinsky:
            self.send_message(f"Applying memory settings")
            self.apply_memory_efficient_settings()

        seed = self.seed
        for n in range(self.n_samples):
            data = self.process_prompts(data, seed)
            self.current_sample = n
            images, nsfw_content_detected = self.sample_diffusers_model(data)
            if self.is_txt2vid and "video_filename" not in self.requested_data:
                self.requested_data["video_filename"] = self.txt2vid_file
            self.image_handler(images, self.requested_data, nsfw_content_detected)
            if self.do_cancel:
                self.do_cancel = False
                break

            seed += 1
            if seed >= MAX_SEED:
                seed = 0

        self.current_sample = 0

    def image_handler(self, images, data, nsfw_content_detected):
        if images:
            tab_section = "stablediffusion"
            if self.use_kandinsky:
                tab_section = "kandinsky"
            elif self.is_shapegif:
                tab_section = "shapegif"
            data["tab_section"] = tab_section

            # apply filters and convert to base64 if requested
            has_filters = self.filters != {}

            do_base64 = data.get("do_base64", False)
            if has_filters or do_base64:
                for i, image in enumerate(images):
                    if has_filters:
                        image = self.apply_filters(image, self.filters)
                    if do_base64:
                        image = self.image_to_base64(image)
                    images[i] = image

            has_nsfw = False
            if nsfw_content_detected is not None:
                for i, is_nsfw in enumerate(nsfw_content_detected):
                    if is_nsfw:
                        has_nsfw = True
                        # iterate over each image and add the word "NSFW" to the
                        # center with bold white letters
                        image = images[i]
                        image = image.convert("RGBA")
                        draw = ImageDraw.Draw(image)
                        font = ImageFont.truetype("arial.ttf", 30)
                        w, h = draw.textsize(f"NSFW", font=font)
                        draw.text(((image.width - w) / 2, (image.height - h) / 2), "NSFW", font=font,
                                  fill=(255, 255, 255, 255))
                        images[i] = image.convert("RGB")

            self.send_message({
                "images": images,
                "data": data,
                "request_type": data.get("request_type", None),
                "nsfw_content_detected": has_nsfw,
            }, MessageCode.IMAGE_GENERATED)

    def final_callback(self):
        total = int(self.steps * self.strength)
        tab_section = "stablediffusion"
        if self.use_kandinsky:
            tab_section = "kandinsky"
        elif self.is_shapegif:
            tab_section = "shapegif"
        self.send_message({
            "step": total,
            "total": total,
            "action": self.action,
            "tab_section": tab_section,
        }, code=MessageCode.PROGRESS)

    def callback(self, step: int, _time_step, _latents):
        # convert _latents to image
        image = None
        data = self.data
        tab_section = "stablediffusion"
        if self.use_kandinsky:
            tab_section = "kandinsky"
        elif self.is_shapegif:
            tab_section = "shapegif"
        if self.is_txt2vid:
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
            "tab_section": tab_section
        }
        if self.use_kandinsky:
            """
            When a Kandinsky response is returned, also return the image embeds
            and negative image embeds - these can be generated independently
            with a separate seed and used to generate a new Kandinsky image.
            Returning the generated embeds here as PIL images allows us to
            """
            image_embed = self.image_embeds.view(32, 24)
            negative_image_embed = self.negative_image_embeds.view(32, 24)
            transform = transforms.ToPILImage()
            image_embed = transform(image_embed)
            negative_image_embed = transform(negative_image_embed)
            res.update({
                "image_embed": image_embed,
                "negative_image_embed": negative_image_embed
            })
        self.send_message(res, code=MessageCode.PROGRESS)

    def generator_sample(self, data: dict):
        logger.info("generator_sample called")
        self.process_data(data)

        if not self.pipe and not self.use_kandinsky:
            logger.info("pipe is None")
            return

        if self.current_clip_skip != self.clip_skip and self.pipe is not None:
            if self.pipe.text_encoder.config.num_hidden_layers <= 12:
                self.reload_model = True

        self.send_message(f"Generating {'video' if self.is_txt2vid else 'image'}")

        action = "depth2img" if data["action"] == "depth" else data["action"]

        try:
            self.initialized = self.__dict__[action] is not None
        except KeyError:
            logger.info(f"{action} model has not been initialized yet")
            self.initialized = False

        error = None
        error_message = ""
        try:
            self.generate(data)
        except TypeError as e:
            error_message = f"TypeError during generation {self.action}"
            error = e
        except Exception as e:
            error = e
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                error = self.cuda_error_message
                self.clear_memory()
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

        return self.pipe

    def cancel(self):
        self.do_cancel = True

    def log_error(self, error, message=None):
        message = str(error) if not message else message
        traceback.print_exc()
        self.error_handler(message)

    def load_controlnet_from_ckpt(self, pipeline):
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
        logger.info(f"Loading controlnet {self.controlnet_type} self.controlnet_model {self.controlnet_model}")
        self._controlnet = None
        controlnet = self.from_pretrained(
            pipeline_action="controlnet",
            model=self.controlnet_model
        )
        # self.load_controlnet_scheduler()
        return controlnet

    def preprocess_for_controlnet(self, image):
        if self.current_controlnet_type != self.controlnet_type or not self.processor:
            logger.info("Loading controlnet processor " + self.controlnet_type)
            self.current_controlnet_type = self.controlnet_type
            logger.info("Controlnet: Processing image")
            self.processor = Processor(self.controlnet_type)
        if self.processor:
            logger.info("Controlnet: Processing image")
            image = self.processor(image)
            # resize image to width and height
            image = image.resize((self.width, self.height))
            return image
        logger.error("No controlnet processor found")

    def load_controlnet_arguments(self, **kwargs):
        if not self.is_txt2vid:
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
        logger.info("Unloading unused models")
        for action in [
            "txt2img",
            "img2img",
            "pix2pix",
            "outpaint",
            "depth2img",
            "superresolution",
            "txt2vid",
            "upscale",
            "_controlnet",
            "safety_checker",
        ]:
            val = getattr(self, action)
            if val:
                val.to("cpu")
                setattr(self, action, None)
                del val
        self.clear_memory()
        self.reset_applied_memory_settings()

    def load_model(self):
        logger.info("Loading model")
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        kwargs = {}

        if self.current_model_branch:
            kwargs["variant"] = self.current_model_branch
        elif self.data_type == torch.float16:
            kwargs["variant"] = "fp16"

        if self.do_reuse_pipeline and not self.reload_model:
            self.initialized = True

        # move all models except for our current action to the CPU
        if not self.initialized or self.reload_model:
            self.unload_unused_models()
        elif self.pipe is None and self.do_reuse_pipeline or self.pipe and self.do_load_controlnet != self.current_load_controlnet:
            self.reuse_pipeline(self.do_load_controlnet)

        self.current_load_controlnet = self.do_load_controlnet

        if self.pipe is None or self.reload_model:
            logger.info(f"Loading model from scratch {self.reload_model}")
            self.reset_applied_memory_settings()
            if self.use_kandinsky:
                logger.info("Using kandinsky model, circumventing model loading")
                return
            else:
                self.send_model_loading_message(self.model_path)

                if self.is_superresolution:
                    kwargs["low_res_scheduler"] = self.load_scheduler(force_scheduler_name="DDPM")

                if self.enable_controlnet:
                    kwargs["controlnet"] = self.controlnet()

                if self.is_single_file:
                    try:
                        self.pipe = self.load_ckpt_model()
                    except OSError as e:
                        return self.handle_missing_files(self.action)
                else:
                    self.pipe = self.from_pretrained(
                        model=self.model_path,
                        scheduler=self.load_scheduler(),
                        **kwargs
                    )

                if self.pipe is None:
                    logger.error("Failed to load pipeline")
                    return

                self.pipe = self.load_text_encoder(self.pipe)

                if self.is_outpaint:
                    self.pipe.vae = self.from_pretrained(
                        pipeline_action="inpaint_vae",
                        model=self.inpaint_vae_model
                    )

                if not self.is_depth2img:
                    self.initialize_safety_checker()

                self.controlnet_loaded = self.enable_controlnet

                if self.is_upscale:
                    self.pipe.scheduler = self.load_scheduler(force_scheduler_name="Euler")

            if not self.is_depth2img:
                self.safety_checker = self.pipe.safety_checker

        # store the model_path
        self.pipe.model_path = self.model_path

        self.load_learned_embed_in_clip()

    def load_text_encoder(self, pipeline):
        if not pipeline or (pipeline.text_encoder and pipeline.text_encoder.config.num_hidden_layers > 12):
            return pipeline

        if self.clip_skip == self.current_clip_skip:
            return pipeline

        self.current_clip_skip = self.clip_skip
        pipeline.text_encoder = self.from_pretrained(
            pipeline_action="text_encoder",
            model=self.text_encoder_model,
            num_hidden_layers=12 - self.clip_skip,
        )
        return pipeline

    def load_ckpt_model(self):
        logger.info(f"Loading ckpt file {self.model_path}")
        pipeline = self.download_from_original_stable_diffusion_ckpt(path=self.model_path)
        if pipeline:
            pipeline.vae.to(self.data_type)
            pipeline = self.load_text_encoder(pipeline)
            self.current_clip_skip = self.clip_skip
            pipeline.text_encoder.to(self.data_type)
            pipeline.unet.to(self.data_type)
        return pipeline

    def download_from_original_stable_diffusion_ckpt(self, path):
        pipe = download_from_original_stable_diffusion_ckpt(
            checkpoint_path=path,
            device=self.device,
            scheduler_type="ddim",
            from_safetensors=self.is_safetensors,
            local_files_only=self.local_files_only,
            extract_ema=False,
            pipeline_class=AutoImport.class_object(
                self.action,
                self.model_data,
                pipeline_action=self.action,
                single_file=True
            ),
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
        return pipe

    def clear_controlnet(self):
        logger.info("Clearing controlnet")
        self._controlnet = None
        self.clear_memory()
        self.reset_applied_memory_settings()
        self.controlnet_loaded = False

    def reuse_pipeline(self, do_load_controlnet):
        logger.info("Reusing pipeline")
        pipe = None
        if self.is_txt2img:
            if self.txt2img is None:
                pipe = self.img2img
            else:
                pipe = self.txt2img
        elif self.is_img2img:
            if self.img2img is None:
                pipe = self.txt2img
            else:
                pipe = self.img2img
        if pipe is None:
            logger.warning("Failed to reuse pipeline")
            self.clear_controlnet()
            return
        kwargs = pipe.components

        # either load from a pretrained model or from a pipe
        if do_load_controlnet:
            kwargs["controlnet"] = self.controlnet()
            self.controlnet_loaded = True
            pipe = self.load_controlnet_from_ckpt(pipe)
        else:
            if "controlnet" in kwargs:
                del kwargs["controlnet"]
            self.clear_controlnet()

            if self.is_single_file:
                pipe = self.download_from_original_stable_diffusion_ckpt(self.model_path)
            else:
                pretrained_object = AutoImport.class_object(
                    self.action,
                    self.model_data,
                    pipeline_action=self.action,
                    category=self.model_data["category"]
                )
                components = pipe.components
                if "controlnet" in components:
                    del components["controlnet"]
                pipe = pretrained_object.from_pretrained(self.model_path, **components)

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
        self.send_message(message)

    def prepare_model(self):
        logger.info("Prepare model")
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

    def from_pretrained(self, **kwargs):
        pipeline_action = kwargs.pop("pipeline_action", self.model_data["pipeline_action"])
        model = kwargs.pop("model", self.model_data)
        if isinstance(model, list):
            model = model[0]["path"]
        elif isinstance(model, dict):
            model = model["path"]
        try:
            return AutoImport.from_pretrained(
                self.action,
                model_data=self.model_data,
                pipeline_action=pipeline_action,
                category=kwargs.pop("category", self.model_data["category"]),
                model=model,
                torch_dtype=self.data_type,
                local_files_only=self.local_files_only,
                use_auth_token=self.data["options"]["hf_token"],
                **kwargs
            )
        except OSError as e:
            logger.error(f"failed to load {model} from pretrained")
            return self.handle_missing_files(pipeline_action)

    def handle_missing_files(self, action):
        if not self.attempt_download:
            if self.is_ckpt_model or self.is_safetensors:
                logger.info("Required files not found, attempting download")
            else:
                import traceback
                traceback.print_exc()
                logger.info("Model not found, attempting download")
            # check if we have an internet connection
            if self.allow_online_when_missing_files:
                self.send_message("Downloading model files")
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
