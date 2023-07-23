import base64
import os
import gc
import re
from io import BytesIO

import numpy as np
import requests
from controlnet_aux.processor import Processor
from diffusers.utils import export_to_gif

from airunner.aihandler.enums import FilterType
from airunner.aihandler.mixins.kandinsky_mixin import KandinskyMixin
import traceback
import torch
from airunner.aihandler.logger import Logger as logger
from PIL import Image
from airunner.aihandler.mixins.merge_mixin import MergeMixin
from airunner.aihandler.mixins.lora_mixin import LoraMixin
from airunner.aihandler.mixins.memory_efficient_mixin import MemoryEfficientMixin
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin
from airunner.aihandler.mixins.txttovideo_mixin import TexttovideoMixin
from airunner.aihandler.mixins.compel_mixin import CompelMixin
from airunner.aihandler.mixins.scheduler_mixin import SchedulerMixin
from airunner.aihandler.settings import MessageCode, MAX_SEED, LOG_LEVEL, AIRUNNER_ENVIRONMENT

os.environ["DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


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
    _model = None
    requested_data = None

    # controlnet atributes
    processor = None
    current_controlnet_type = None
    controlnet_loaded = False

    # end controlnet atributes

    # controlnet properties
    def controlnet(self):
        if self._controlnet is None or self.current_controlnet_type != self.controlnet_type:
            self._controlnet = self.load_controlnet()
        return self._controlnet

    @property
    def controlnet_model(self):
        if self.controlnet_type == "canny":
            return "lllyasviel/control_v11p_sd15_canny"
        elif self.controlnet_type in [
            "depth_leres", "depth_leres++", "depth_midas", "depth_zoe"
        ]:
            return "lllyasviel/control_v11f1p_sd15_depth"
        elif self.controlnet_type == "mlsd":
            return "lllyasviel/control_v11p_sd15_mlsd"
        elif self.controlnet_type in ["normal_bae", "normal_midas"]:
            return "lllyasviel/control_v11p_sd15_normalbae"
        elif self.controlnet_type in ["scribble_hed", "scribble_pidinet"]:
            return "lllyasviel/control_v11p_sd15_scribble"
        elif self.controlnet_type == "segmentation":
            return "lllyasviel/control_v11p_sd15_seg"
        elif self.controlnet_type in ["lineart_coarse", "lineart_realistic"]:
            return "lllyasviel/control_v11p_sd15_lineart"
        elif self.controlnet_type == "lineart_anime":
            return "lllyasviel/control_v11p_sd15s2_lineart_anime"
        elif self.controlnet_type in [
            "openpose", "openpose_face", "openpose_faceonly",
            "openpose_full", "openpose_hand"
        ]:
            return "lllyasviel/control_v11p_sd15_openpose"
        elif self.controlnet_type in [
            "softedge_hed", "softedge_hedsafe",
            "softedge_pidinet", "softedge_pidsafe"
        ]:
            return "lllyasviel/control_v11p_sd15_softedge"
        elif self.controlnet_type == "pixel2pixel":
            return "lllyasviel/control_v11e_sd15_ip2p"
        elif self.controlnet_type == "inpaint":
            return "lllyasviel/control_v11p_sd15_inpaint"
        elif self.controlnet_type == "shuffle":
            return "lllyasviel/control_v11e_sd15_shuffle"
        raise Exception("Unknown controlnet type %s" % self.controlnet_type)
        # end controlnet properties

    @property
    def controlnet_type(self):
        controlnet_type = self.options.get("controlnet", "canny")
        return controlnet_type.replace(" ", "_")

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
    def prompt_data(self):
        return self.options.get(f"prompt_data", None)

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
    def batch_size(self):
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
        return self.model == "Stable Diuffions XL 0.9"

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
        if self.current_model and os.path.exists(self.current_model):
            return self.current_model
        path = None
        if self.is_outpaint:
            path = self.outpaint_model_path
        elif self.is_pix2pix:
            path = self.pix2pix_model_path
        elif self.is_depth2img:
            path = self.depth2img_model_path
        elif self.is_superresolution or self.is_upscale:
            path = self.upscale_model_path
        if path is None or path == "":
            path = self.model_base_path
        if self.current_model:
            path = os.path.join(path, self.current_model)
        if not os.path.exists(path):
            return self.current_model
        return path

    @property
    def cuda_error_message(self):
        if self.is_superresolution and self.scheduler_name == "DDIM":
            return f"Unable to run the model at {self.width}x{self.height} resolution using the DDIM scheduler. Try changing the scheduler to LMS or PNDM and try again."

        return f"You may not have enough GPU memory to run the model at {self.width}x{self.height} resolution. Potential solutions: try again, restart the application, use a smaller size, upgrade your GPU."

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
    def action_diffuser(self):
        from diffusers import (
            DiffusionPipeline,
            StableDiffusionPipeline,
            StableDiffusionImg2ImgPipeline,
            StableDiffusionInstructPix2PixPipeline,
            StableDiffusionInpaintPipeline,
            StableDiffusionDepth2ImgPipeline,
            StableDiffusionUpscalePipeline,
            StableDiffusionLatentUpscalePipeline,
            StableDiffusionXLPipeline,
            StableDiffusionXLImg2ImgPipeline,
            TextToVideoSDPipeline,
            VideoToVideoSDPipeline,
            TextToVideoZeroPipeline,
            KandinskyPipeline,
            KandinskyImg2ImgPipeline
        )

        if (self.enable_controlnet
                and not self.is_ckpt_model
                and not self.is_safetensors):
            return self.controlnet_action_diffuser

        if self.is_sd_xl:
            if self.is_txt2img:
                return StableDiffusionXLPipeline
            elif self.is_img2img:
                return StableDiffusionXLImg2ImgPipeline
        if self.is_txt2img:
            if self.is_shapegif:
                return DiffusionPipeline
            elif self.use_kandinsky:
                return KandinskyPipeline
            else:
                return StableDiffusionPipeline
        elif self.is_img2img:
            if self.is_shapegif:
                return DiffusionPipeline
            elif self.use_kandinsky:
                return KandinskyImg2ImgPipeline
            else:
                return StableDiffusionImg2ImgPipeline
        elif self.is_pix2pix:
            return StableDiffusionInstructPix2PixPipeline
        elif self.is_outpaint:
            return StableDiffusionInpaintPipeline
        elif self.is_depth2img:
            return StableDiffusionDepth2ImgPipeline
        elif self.is_superresolution:
            return StableDiffusionUpscalePipeline
        elif self.is_txt2vid and self.is_zeroshot:
            return TextToVideoZeroPipeline
        elif self.is_txt2vid:
            return TextToVideoSDPipeline
        elif self.is_vid2vid:
            return VideoToVideoSDPipeline
        elif self.is_upscale:
            return StableDiffusionLatentUpscalePipeline
        elif self.is_shapegif:
            return DiffusionPipeline
        else:
            return DiffusionPipeline

    @property
    def is_ckpt_model(self):
        return self._is_ckpt_file(self.model)

    @property
    def is_safetensors(self):
        return self._is_safetensor_file(self.model)

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
            response = requests.get('https://huggingface.co/')
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

    def __init__(self, *args, **kwargs):
        logger.set_level(LOG_LEVEL)
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

    def clear_memory(self):
        logger.info("Clearing memory")
        torch.cuda.empty_cache()
        gc.collect()

    def initialize(self):
        # get classname of self.action_diffuser
        if not self.initialized or self.reload_model:
            self.compel_proc = None
            self.prompt_embeds = None
            self.negative_prompt_embeds = None
            self._load_model()
            self.reload_model = False
            self.initialized = True

    def generator(self, device=None, seed=None):
        device = self.device if not device else device
        seed = self.seed if not seed else seed
        return torch.Generator(device=device).manual_seed(seed)

    def prepare_options(self, data):
        logger.info(f"Preparing options...")
        action = data["action"]
        options = data["options"]
        requested_model = options.get(f"model", None)
        enable_controlnet = options.get("enable_controlnet", False)

        # do model reload checks here
        if (
                self.is_pipe_loaded and (  # memory options change
                self.use_enable_sequential_cpu_offload != options.get("use_enable_sequential_cpu_offload", True)
        )
        ) or (  # model change
                self.model is not None
                and self.model != requested_model
        ):
            self.reload_model = True

        if ((self.controlnet_loaded and not enable_controlnet)
                or (not self.controlnet_loaded and enable_controlnet)):
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
            from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
            safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                "CompVis/stable-diffusion-safety-checker",
                local_files_only=self.local_files_only
            )
            from transformers import AutoFeatureExtractor
            feature_extractor = AutoFeatureExtractor.from_pretrained(
                "CompVis/stable-diffusion-safety-checker",
                local_files_only=self.local_files_only)
            self.pipe.safety_checker = safety_checker
            self.pipe.feature_extractor = feature_extractor

    def load_safety_checker(self):
        if not self.pipe:
            return
        if not self.do_nsfw_filter:
            self.pipe.safety_checker = None
        elif self.pipe.safety_checker is None:
            self.pipe.safety_checker = self.safety_checker
            if self.pipe.safety_checker:
                self.pipe.safety_checker.to(self.device)

    def do_sample(self, **kwargs):
        logger.info(f"Sampling {self.action}")
        self.send_message(f"Generating image...")

        try:
            logger.info(f"Generating image")
            output = self.call_pipe(**kwargs)
        except Exception as e:
            error_message = str(e)
            if "Scheduler.step() got an unexpected keyword argument" in str(e):
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
        if not self.use_kandinsky and not self.is_txt2vid and not self.is_upscale and not self.is_superresolution:
            # self.pipe = self.call_pipe_extension(**kwargs)  TODO: extensions
            try:
                self.add_lora_to_pipe()
            except Exception as e:
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
                args["num_frames"] = self.batch_size
        elif not self.use_kandinsky:
            if self.use_compel:
                try:
                    args.update({
                        "prompt_embeds": self.prompt_embeds,
                        "negative_prompt_embeds": self.negative_prompt_embeds,
                    })
                except Exception as e:
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
                    generator = [self.generator(seed=_i) for _i in range(4)]
                else:
                    generator = [self.generator(seed=self.seed + i) for i in range(4)]
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
        video_length = self.batch_size
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

    def prepare_extra_args(self, data, image, mask):
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
        if prompt_data is None:
            return data
        logger.info("Process prompt")
        if self.deterministic_seed:
            prompt = data["options"][f"prompt"]
            if ".blend(" in prompt:
                # replace .blend([0-9.]+, [0-9.]+) with ""
                prompt = re.sub(r"\.blend\([0-9.]+, [0-9.]+\)", "", prompt)
                # find this pattern r'\("(.*)", "(.*)"\)'
                match = re.search(r'\("(.*)", "(.*)"\)', prompt)
                # get the first and second group
                prompt = match.group(1)
                generated_prompt = match.group(2)
                prompt_data.prompt = prompt
                prompt_data.generated_prompt = generated_prompt
                print(prompt)
                print(generated_prompt)
        prompt, negative_prompt = prompt_data.build_prompts(
            seed=seed,
            is_deterministic=True if self.deterministic_seed else False,
            is_batch=self.deterministic_generation,
        )
        data["options"][f"prompt"] = prompt
        data["options"][f"negative_prompt"] = negative_prompt
        print(prompt)
        print(negative_prompt)
        self.clear_prompt_embeds()
        self.process_data(data)
        return data

    def process_data(self, data: dict):
        self.requested_data = data
        self.prepare_options(data)
        if self.do_clear_kandinsky:
            self.clear_kandinsky()
        self._prepare_scheduler()
        self._prepare_model()
        self.initialize()
        self._change_scheduler()

    def generate(self, data: dict):
        logger.info("generate called")
        self.do_cancel = False
        self.process_data(data)

        if not self.use_kandinsky:
            self.send_message(f"Applying memory settings...")
            self.apply_memory_efficient_settings()
        if self.is_txt2vid or self.is_upscale:
            total_to_generate = 1
        else:
            total_to_generate = self.batch_size

        seed = self.seed
        for n in range(total_to_generate):
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

    def apply_filters(self, image, filters):
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

    def image_to_base64(self, image):
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

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

            self.send_message({
                "images": images,
                "data": data,
                "request_type": data.get("request_type", None),
                "nsfw_content_detected": nsfw_content_detected == True,
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
            tab_section = "stablediffusion"
        elif self.is_shapegif:
            tab_section = "shapegif"
        if self.is_txt2vid:
            data["video_filename"] = self.txt2vid_file
        steps = int(self.steps * self.strength) if (
                not self.enable_controlnet and
                (self.is_img2img or self.is_depth2img)
        ) else self.steps
        self.send_message({
            "step": step,
            "total": steps,
            "action": self.action,
            "image": image,
            "data": data,
            "tab_section": tab_section
        }, code=MessageCode.PROGRESS)

    def latents_to_image(self, latents: torch.Tensor):
        image = latents.permute(0, 2, 3, 1)
        image = image.detach().cpu().numpy()
        image = image[0]
        image = (image * 255).astype(np.uint8)
        image = Image.fromarray(image)
        return image

    def generator_sample(
            self,
            data: dict
    ):
        self.send_message(f"Generating {'video' if self.is_txt2vid else 'image'}...")

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
        except OSError as e:
            error_message = "model_not_found"
            error = e
        except TypeError as e:
            error_message = f"TypeError during generation {self.action}"
            error = e
        except Exception as e:
            error = e
            if "PYTORCH_CUDA_ALLOC_CONF" in str(e):
                error_message = self.cuda_error_message
                self.clear_memory()
            else:
                error_message = f"Error during generation"
                traceback.print_exc()

        if error:
            self.log_error(error, error_message)
            self.initialized = False
            self.reload_model = True
            if error_message == "model_not_found" and self.local_files_only and self.has_internet_connection:
                # check if we have an internet connection
                self.send_message("Downloading model files...")
                self.local_files_only = False
                self.initialize()
                return self.generator_sample(data)
            elif not self.has_internet_connection:
                self.log_error("Please check your internet connection and try again.")
            self.scheduler_name = None
            self._current_model = None
            self.local_files_only = True

            # handle the error (sends to client)
            self.log_error(error)

    def cancel(self):
        self.do_cancel = True

    def log_error(self, error, message=None):
        message = str(error) if not message else message
        traceback.print_exc()
        self.error_handler(message)

    """
    Controlnet methods
    """

    def load_controlnet_from_ckpt(self, pipeline, config):
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
        from diffusers import ControlNetModel
        self._controlnet = None
        controlnet = ControlNetModel.from_pretrained(
            self.controlnet_model,
            local_files_only=self.local_files_only,
            torch_dtype=self.data_type
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
        image_key = "image" if self.is_txt2img else "control_image"

        if not self.is_txt2vid:
            kwargs = {**kwargs, **{
                image_key: self.preprocess_for_controlnet(self.image),
            }}

        kwargs = {**kwargs, **{
            "guess_mode": self.controlnet_guess_mode,
            "control_guidance_start": self.control_guidance_start,
            "control_guidance_end": self.control_guidance_end,
            "controlnet_conditioning_scale": self.controlnet_conditioning_scale,
        }}
        return kwargs

    # end controlnet methods

    # Model methods
    def unload_unused_models(self):
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

    def _load_model(self):
        logger.info("Loading model...")
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        kwargs = {}

        if self.current_model_branch:
            kwargs["variant"] = self.current_model_branch
        elif self.data_type == torch.float16:
            kwargs["variant"] = "fp16"

        do_load_controlnet = (
                (not self.controlnet_loaded and self.enable_controlnet) or
                (self.controlnet_loaded and self.enable_controlnet)
        )
        do_unload_controlnet = (
                (self.controlnet_loaded and not self.enable_controlnet) or
                (not self.controlnet_loaded and not self.enable_controlnet)
        )

        reuse_pipeline = (
                (self.is_txt2img and self.txt2img is None and self.img2img) or
                (self.is_img2img and self.img2img is None and self.txt2img) or
                ((
                         (self.is_txt2img and self.txt2img) or
                         (self.is_img2img and self.img2img)
                 ) and (do_load_controlnet or do_unload_controlnet))
        )

        if reuse_pipeline and not self.reload_model:
            self.initialized = True

        # move all models except for our current action to the CPU
        if not self.initialized or self.reload_model:
            self.unload_unused_models()
        elif reuse_pipeline:
            self.reuse_pipeline(do_load_controlnet)

        if self.pipe is None or self.reload_model:
            logger.info(f"Loading model from scratch {self.reload_model}")
            if self.use_kandinsky:
                logger.info("Using kandinsky model, circumventing model loading")
                return
            else:
                logger.info(f"Loading {self.model_path} from diffusers pipeline")

                kwargs.update({
                    "local_files_only": self.local_files_only,
                    "use_auth_token": self.data["options"]["hf_token"],
                })

                if self.is_superresolution:
                    kwargs["low_res_scheduler"] = self.load_scheduler(force_scheduler_name="DDPM")

                if self.enable_controlnet:
                    kwargs["controlnet"] = self.controlnet()

                if self.is_ckpt_model or self.is_safetensors:
                    self.pipe = self.action_diffuser.from_single_file(
                        self.model_path,
                        use_safetensors=True,
                        torch_dtype=self.data_type,
                        **kwargs)
                    self.pipe.scheduler = self.load_scheduler(config=self.pipe.scheduler.config)
                else:
                    self.pipe = self.action_diffuser.from_pretrained(
                        self.model_path,
                        torch_dtype=self.data_type,
                        scheduler=self.load_scheduler(),
                        **kwargs
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

    def clear_controlnet(self):
        self._controlnet = None
        self.clear_memory()
        self.controlnet_loaded = False

    def reuse_pipeline(self, do_load_controlnet):
        logger.info(f"{'Loading' if do_load_controlnet else 'Unloading'} controlnet")
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
            self.clear_controlnet()
            logger.warning("Failed to reuse pipeline")
            return
        kwargs = pipe.components
        if do_load_controlnet:
            kwargs["controlnet"] = self.controlnet()
            self.controlnet_loaded = True
        else:
            if "controlnet" in kwargs:
                del kwargs["controlnet"]
            self.clear_controlnet()
        if do_load_controlnet:
            pipe = self.controlnet_action_diffuser(**kwargs)
        else:
            pipe = self.action_diffuser(**kwargs)
        if self.is_txt2img:
            self.txt2img = pipe
            self.img2img = None
        elif self.is_img2img:
            self.img2img = pipe
            self.txt2img = None

    def _is_ckpt_file(self, model):
        if not model:
            raise ValueError("ckpt path is empty")
        return model.endswith(".ckpt")

    def _is_safetensor_file(self, model):
        if not model:
            raise ValueError("safetensors path is empty")
        return model.endswith(".safetensors")

    def _do_reload_model(self):
        logger.info("Reloading model")
        if self.reload_model:
            self._load_model()

    def _prepare_model(self):
        logger.info("Prepare model")
        # get model and switch to it

        # get models from database
        model_name = self.options.get(f"model", None)

        self.send_message(f"Loading model {model_name}")

        self._previous_model = self.current_model

        if self._is_ckpt_file(model_name):
            self.current_model = model_name
        else:
            self.current_model = self.options.get(f"model_path", None)
            self.current_model_branch = self.options.get(f"model_branch", None)
    # end model methods
