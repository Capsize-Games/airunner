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
from airunner.settings import CONFIG_FILES
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


class ModelMixin:
    def __init__(self, *args, **kwargs):
        self.txt2img = None
        self.img2img = None
        self.pix2pix = None
        self.outpaint = None
        self.depth2img = None

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

    def has_pipe(self) -> bool:
        return self.pipe is not None

    def is_pipe_on_cpu(self) -> bool:
        return self.has_pipe() and self.pipe.device.type == "cpu"

    def final_callback(self):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": self.sd_request.generator_settings.steps,
            "total": self.sd_request.generator_settings.steps,
        })
        self.latents_set = True

    def callback(self, step: int, _time_step, latents):
        res = {
            "step": step,
            "total": self.sd_request.generator_settings.steps
        }
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, res)
        QApplication.processEvents()
        if self.latents_set is False:
            self.latents = latents
        return {}

    def do_sample(self):
        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, "Generating image")
        self.emit_signal(SignalCode.VISION_CAPTURE_LOCK_SIGNAL)
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
        self.emit_signal(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL)
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
        if (self.pipe and ((
           self.use_safety_checker and
           self.safety_checker_status is ModelStatus.LOADED
        ) or (
            not self.use_safety_checker
        ))):
            data = self.data
            for k, v in self.generator_request_data.items():
                data[k] = v
            try:
                return self.pipe(
                    **data,
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
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                        draw.text(
                            (
                                self.settings["working_width"] / 2 - 30,
                                self.settings["working_height"] / 2
                            ),
                            "NSFW",
                            (255, 255, 255),
                            font=font
                        )
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

    def generator(self, device=None, seed=None):
        if self._generator is None:
            device = self.device if not device else device
            if seed is None:
                seed = int(self.settings["generator_settings"]["seed"])
            self._generator = torch.Generator(device=device).manual_seed(seed)
        return self._generator

    def unload(self):
        self.initialized = False
        self.unload_model()
        print("unloaded")
        clear_memory()

    def unload_model(self):
        self.logger.debug("Unloading model")
        self.pipe = None
        self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
            "model": ModelType.SD,
            "status": ModelStatus.UNLOADED,
            "path": ""
        })

    def handle_model_changed(self) -> bool:
        requested_model = self.settings["generator_settings"]["model"]
        model_changed = (
                    self.model is not None and self.model["name"] is not None and self.model["name"] != requested_model)
        if model_changed:  # model change
            self.logger.debug(f"Model changed clearing debugger: {self.model['name']} != {requested_model}")
            self.reload_model = True
            self.clear_scheduler()
            self.clear_controlnet()
        return model_changed

    def generator_sample(self):
        """
        Called from sd_generate_worker, kicks off the generation process.
        :param data:
        :return:
        """
        action = self.settings["generator_settings"]["section"]
        if (
                self.sd_request.generator_settings and action != self.sd_request.generator_settings.section) or self.reload_model:
            self._prompt_embeds = None
            self._negative_prompt_embeds = None

        if (
                (self.controlnet_loaded and not self.settings["controlnet_enabled"]) or
                (not self.controlnet_loaded and self.settings["controlnet_enabled"])
        ):
            self.initialized = False

        self.load_generator_arguments()

        if self.do_load:
            self.load()

        if self.pipe and self.moved_to_cpu:
            self.reset_applied_memory_settings()
            self.moved_to_cpu = False
        self.apply_memory_efficient_settings()

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
            except Exception as e:
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

        # if self.sd_request.is_upscale:
        #     return self.do_upscale(self.data)

        if not self.pipe:
            import traceback
            traceback.print_stack()
            self.logger.error("pipe is None")
            return

        if not self.do_generate:
            return

        self.do_generate = False

        is_txt2img = self.sd_request.is_txt2img
        is_outpaint = self.sd_request.is_outpaint
        is_img2img = self.sd_request.is_img2img

        if not is_img2img and not is_outpaint:
            is_txt2img = True

        if is_img2img and (
                "image" not in self.data or ("image" in self.data and self.data["image"] is None)
        ):
            self.data = self.sd_request.disable_img2img(self.data)
            is_txt2img = True

        kwargs = dict(
            vae=self.pipe.vae,
            text_encoder=self.pipe.text_encoder,
            tokenizer=self.pipe.tokenizer,
            unet=self.pipe.unet,
            scheduler=self.pipe.scheduler,
            safety_checker=self.safety_checker,
            feature_extractor=self.feature_extractor
        )

        enable_controlnet = self.sd_request.generator_settings.enable_controlnet and "control_image" in self.data and \
                            self.data["control_image"] is not None
        if is_txt2img:
            if enable_controlnet:
                kwargs["controlnet"] = self.pipe.controlnet
                self.pipe = StableDiffusionControlNetPipeline(**kwargs)
            else:
                self.pipe = StableDiffusionPipeline(**kwargs)
        elif is_img2img:
            if enable_controlnet:
                kwargs["controlnet"] = self.pipe.controlnet
                self.pipe = StableDiffusionControlNetImg2ImgPipeline(**kwargs)
            else:
                self.pipe = StableDiffusionImg2ImgPipeline(**kwargs)
        elif self.sd_request.is_outpaint:
            if enable_controlnet:
                kwargs["controlnet"] = self.pipe.controlnet
                self.pipe = StableDiffusionControlNetInpaintPipeline(**kwargs)
            else:
                self.pipe = StableDiffusionInpaintPipeline(**kwargs)

        self.emit_signal(
            SignalCode.LOG_STATUS_SIGNAL,
            f"Generating media"
        )

        return self.generate()

    def unload_unused_models(self):
        self.logger.debug("Unloading unused models")
        for action in [
            "txt2img",
            "img2img",
            "pix2pix",
            "outpaint",
            "depth2img",
            "controlnet",
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
        if self.settings["controlnet_enabled"] and self.controlnet is not None:
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

    def initialize(self):
        if self.settings["sd_enabled"] and (
            self.initialized is False or
            self.reload_model is True or
            self.pipe is None
        ):
            self.send_model_loading_message(self.current_model)
            if self.reload_model:
                self.reset_applied_memory_settings()
            if self.do_load or not self.initialized:
                self.load_model()
            self.reload_model = False

    def load(self):
        if not self._scheduler:
            self.load_scheduler()

        if not self.pipe:
            self.prepare_model()
            self.initialize()

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
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADING,
                    "path": self.model_path
                }
            )

            self.logger.debug(
                f"Loading model from scratch {self.reload_model} for {self.sd_request.generator_settings.section}")
            self.reset_applied_memory_settings()
            self.send_model_loading_message(self.model_path)

            if self.settings["controlnet_enabled"]:
                kwargs["controlnet"] = self.controlnet

            self.load_safety_checker()

            if self.is_single_file:
                try:
                    self.logger.debug(f"Loading ckpt file {self.model_path}")
                    self.pipe = self.download_from_original_stable_diffusion_ckpt()
                    if self.pipe is not None:
                        self.pipe.scheduler = self.load_scheduler(config=self.pipe.scheduler.config)
                except Exception as e:
                    self.logger.error(f"Failed to load model from ckpt: {e}")
            elif self.model is not None:
                self.logger.debug(
                    f"Loading model `{self.model['name']}` `{self.model_path}` for {self.sd_request.generator_settings.section}")
                scheduler = self.load_scheduler()
                if scheduler:
                    kwargs["scheduler"] = scheduler

                pipeline_classname_ = self.pipeline_class()

                try:
                    self.pipe = pipeline_classname_.from_pretrained(
                        os.path.expanduser(
                            os.path.join(
                                self.settings["path_settings"][
                                    f"{self.sd_request.generator_settings.section}_model_path"],
                                self.model_path
                            )
                        ),
                        torch_dtype=self.data_type,
                        safety_checker=self.safety_checker,
                        feature_extractor=self.feature_extractor,
                        use_safetensors=True,
                        **kwargs
                    )
                except Exception as e:
                    self.logger.error(e)
                    self.logger.error(f"Failed to load model from {self.model_path}: {e}")

            if self.pipe is None:
                self.emit_signal(
                    SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                        "model": ModelType.SD,
                        "status": ModelStatus.FAILED,
                        "path": self.model_path
                    }
                )
                return

            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.LOADED,
                    "path": self.model_path
                }
            )

            if self.settings["nsfw_filter"] is False:
                self.pipe.safety_checker = None
                self.pipe.feature_extractor = None

            if self.pipe is None:
                self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Failed to load model")
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

            self.controlnet_loaded = self.settings["controlnet_enabled"]

    def get_pipeline_action(self, action=None):
        action = self.sd_request.generator_settings.section if not action else action
        if action == "txt2img" and self.sd_request.is_img2img:
            action = "img2img"
        return action

    def download_from_original_stable_diffusion_ckpt(self):
        pipe = None
        data = {
            "checkpoint_path_or_dict": self.model_path,
            "device": self.device,
            "scheduler_type": Scheduler.DDIM.value.lower(),
            "from_safetensors": self.is_safetensors,
            "local_files_only": True,
            "extract_ema": False,
            "config_files": CONFIG_FILES,
            "pipeline_class": self.pipeline_class(),
            "load_safety_checker": False,
        }
        if self.settings["controlnet_enabled"]:
            data["controlnet"] = self.controlnet
        try:
            pipe = download_from_original_stable_diffusion_ckpt(**data)
        except Exception as e:
            self.logger.error(f"Failed to load model from ckpt: {e}")

        if pipe is not None:
            pipe.safety_checker = self.safety_checker
            pipe.feature_extractor = self.feature_extractor
        return pipe

    def prepare_model(self):
        self.logger.debug("Prepare model")
        if not self.model:
            return
        self._previous_model = self.current_model
        if self.is_single_file:
            self.current_model = self.model
        else:
            self.current_model = self.model_path
            self.current_model_branch = self.model["branch"]

        if self.do_unload_controlnet:
            self.unload_controlnet()

    def send_model_loading_message(self, model_name):
        if self.attempt_download:
            if self.downloading_controlnet:
                message = f"Downloading controlnet model"
            else:
                message = f"Downloading model {model_name}"
        else:
            message = f"Loading model {model_name}"
        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, message)

    def reuse_pipeline(self, do_load_controlnet):
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
            pipe = self.load_controlnet_from_ckpt(pipe)
            kwargs["controlnet"] = self.controlnet
        else:
            if "controlnet" in kwargs:
                del kwargs["controlnet"]

            if self.is_single_file:
                if self.model_version == "SDXL 1.0":
                    pipeline_class_ = StableDiffusionXLPipeline
                else:
                    pipeline_class_ = StableDiffusionPipeline

                pipe = pipeline_class_.from_single_file(
                    self.model_path,
                    local_files_only=True
                )
                return pipe
            else:
                components = pipe.components
                if "controlnet" in components:
                    del components["controlnet"]
                components["controlnet"] = self.controlnet

                pipe = AutoPipelineForText2Image.from_pretrained(
                    os.path.expanduser(
                        os.path.join(
                            self.settings["path_settings"]["txt2img_model_path"],
                            self.model_path
                        )
                    ),
                    **components
                )

        if self.sd_request.is_txt2img:
            self.txt2img = pipe
            self.img2img = None
        elif self.sd_request.is_img2img:
            self.img2img = pipe
            self.txt2img = None
