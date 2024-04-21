import io
import base64
import os
import numpy as np
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
    StableDiffusionDepth2ImgPipeline,
    AutoPipelineForInpainting,
    StableDiffusionInstructPix2PixPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline
)
from diffusers import (
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,

)
from airunner.aihandler.stablediffusion.sd_request import SDRequest
from airunner.enums import (
    GeneratorSection,
    SignalCode,
    Scheduler,
    SDMode,
    StableDiffusionVersion,
    ModelStatus,
    ModelType
)
from airunner.exceptions import PipeNotLoadedException, SafetyCheckerNotLoadedException, InterruptedException
from airunner.settings import (
    CONFIG_FILES,
    AVAILABLE_ACTIONS
)
from airunner.utils.clear_memory import clear_memory
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
        self.reload_model = False
        self.batch_size = 1
        self.moved_to_cpu = False

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
    def __do_reuse_pipeline(self) -> bool:
        return (
            (self.sd_request.is_txt2img and self.txt2img is None and self.img2img) or
            (self.sd_request.is_img2img and self.img2img is None and self.txt2img) or
            (
                (self.sd_request.is_txt2img and self.txt2img) or
                (self.sd_request.is_img2img and self.img2img)
            )
        )

    @staticmethod
    def __is_pytorch_error(e) -> bool:
        return "PYTORCH_CUDA_ALLOC_CONF" in str(e)

    def unload_image_generator_model(self):
        self.__unload_model()
        self.__do_reset_applied_memory_settings()
        clear_memory()

    def load_image_generator_model(self):
        self.logger.info("Loading image generator model")

        # Unload the pipeline if it is already loaded
        if self.pipe:
            self.unload_image_generator_model()

        # Continue with loading the model
        self.__prepare_model()
        self.__load_model()
        self.__move_model_to_device()

    def generate(
        self,
        settings: dict,
        sd_request: SDRequest,
        generator_request_data: dict
    ):
        self.__load_generator_arguments(settings, sd_request, generator_request_data)

        self.do_generate = False

        self.__swap_pipeline(sd_request)
        return self.__generate(generator_request_data)

    def __swap_pipeline(self, sd_request: SDRequest):
        if not self.pipe:
            raise PipeNotLoadedException()

        is_txt2img = sd_request.is_txt2img
        is_outpaint = sd_request.is_outpaint
        is_img2img = sd_request.is_img2img

        if not is_img2img and not is_outpaint:
            is_txt2img = True

        if is_img2img and (
            "image" not in self.data or ("image" in self.data and self.data["image"] is None)
        ):
            self.data = sd_request.disable_img2img(self.data)
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

        enable_controlnet = (
            sd_request.generator_settings.enable_controlnet and
            "control_image" in self.data and
            self.data["control_image"] is not None
        )

        pipeline_map = {
            ("txt2img", True): StableDiffusionControlNetPipeline,
            ("txt2img", False): StableDiffusionPipeline,
            ("img2img", True): StableDiffusionControlNetImg2ImgPipeline,
            ("img2img", False): StableDiffusionImg2ImgPipeline,
            ("outpaint", True): StableDiffusionControlNetInpaintPipeline,
            ("outpaint", False): StableDiffusionInpaintPipeline,
        }

        operation_type = "txt2img" if is_txt2img else "img2img" if is_img2img else "outpaint"

        if enable_controlnet:
            kwargs["controlnet"] = self.pipe.controlnet

        pipeline_class_ = pipeline_map.get((operation_type, enable_controlnet))

        if pipeline_class_ is not None:
            self.logger.debug("Swapping pipeline")
            self.pipe = pipeline_class_(**kwargs)

    def __move_model_to_device(self):
        if self.pipe:
            self.pipe.to(self.data_type)
            self.pipe.vae.to(self.data_type)
            self.pipe.text_encoder.to(self.data_type)
            self.pipe.unet.to(self.data_type)

    def __has_pipe(self) -> bool:
        return self.pipe is not None

    def __is_pipe_on_cpu(self) -> bool:
        return self.__has_pipe() and self.pipe.device.type == "cpu"

    def __callback(self, step: int, _time_step, latents):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": step,
            "total": self.sd_request.generator_settings.steps
        })
        if self.latents_set is False:
            self.latents = latents
        QApplication.processEvents()
        return {}

    def __generate_latents(self):
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
            generator=self.__generator(torch.device(self.device)),
        )

    def __model_is_loaded(self, model: ModelType) -> bool:
        return self.model_status[model] == ModelStatus.LOADED

    def __safety_checker_ready(self) -> bool:
        return (self.pipe and ((
           self.use_safety_checker and
           self.__model_is_loaded(ModelType.SAFETY_CHECKER) and
           self.__model_is_loaded(ModelType.FEATURE_EXTRACTOR)
        ) or (
            not self.use_safety_checker
        )))

    def __prepare_request_data(self, generator_request_data: dict) -> dict:
        data = self.data
        for k, v in generator_request_data.items():
            data[k] = v
        return data

    def __call_pipe(self, generator_request_data: dict):
        """
        Generate an image using the pipe
        :return:
        """
        if not self.__safety_checker_ready():
            raise SafetyCheckerNotLoadedException()

        data = self.__prepare_request_data(generator_request_data)

        data["callback_on_step_end"] = self.__interrupt_callback

        results = self.pipe(**data)
        images = results.get("images", [])
        nsfw_content_detected = results.get("nsfw_content_detected", None)
        if nsfw_content_detected is None:
            nsfw_content_detected = [False] * len(images)
        return images, nsfw_content_detected

    def __interrupt_callback(self, pipe, i, t, callback_kwargs):
        if self.do_interrupt_image_generation:
            self.do_interrupt_image_generation = False
            raise InterruptedException()
        return callback_kwargs

    def __generate(self, generator_request_data: dict):
        if not self.pipe:
            raise PipeNotLoadedException()

        self.logger.debug("sample_diffusers_model")

        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, f"Generating media")
        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, "Generating image")
        self.emit_signal(SignalCode.VISION_CAPTURE_LOCK_SIGNAL)

        images, nsfw_content_detected = self.__call_pipe(generator_request_data)

        self.emit_signal(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL)

        return self.__image_handler(
            images,
            nsfw_content_detected
        )

    def __convert_image_to_base64(self, image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return base64.encodebytes(img_byte_arr).decode('ascii')

    def __apply_filters_to_image(self, image):
        return self.apply_filters(image, self.filters)

    def __mark_image_as_nsfw(self, image):
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
        return image

    def __process_images(self, images: List[Image.Image], do_base64: bool, has_filters: bool, nsfw_content_detected: List[bool]):
        for i, image in enumerate(images):
            if has_filters:
                image = self.__apply_filters_to_image(image)
            if do_base64:
                image = self.__convert_image_to_base64(image)
            if nsfw_content_detected[i]:
                image = self.__mark_image_as_nsfw(image)
            images[i] = image
        return images

    def __image_handler(self, images: List[Image.Image], nsfw_content_detected: List[bool]):
        self._final_callback()
        if images is None:
            return

        if self.requested_data is not None:
            self.requested_data["original_model_data"] = self.original_model_data or {}

        has_nsfw = True in nsfw_content_detected if nsfw_content_detected is not None else False

        if images:
            do_base64 = self.requested_data.get("do_base64", False)
            has_filters = self.filters is not None and len(self.filters) > 0
            images = self.__process_images(images, do_base64, has_filters, nsfw_content_detected)

        return dict(
            images=images,
            data=self.requested_data,
            nsfw_content_detected=has_nsfw,
        )

    def __generator(self, device=None, seed=None):
        if self._generator is None:
            device = self.device if not device else device
            if seed is None:
                seed = int(self.settings["generator_settings"]["seed"])
            self._generator = torch.Generator(device=device).manual_seed(seed)
        return self._generator

    def __unload_model(self):
        self.logger.debug("Unloading model")
        self.pipe = None
        self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
            "model": ModelType.SD,
            "status": ModelStatus.UNLOADED,
            "path": ""
        })

    def __handle_model_changed(self):
        self.reload_model = True

    def __do_reset_applied_memory_settings(self):
        self.emit_signal(SignalCode.RESET_APPLIED_MEMORY_SETTINGS)

    def __unload_unused_models(self):
        self.logger.debug("Unloading unused models")
        for action in AVAILABLE_ACTIONS:
            val = getattr(self, action)
            if val:
                val.to("cpu")
                setattr(self, action, None)
                del val
        clear_memory()
        self.reset_applied_memory_settings()

    def __pipeline_class(self):
        if self.settings["controlnet_enabled"] and self.controlnet is not None:
            if self.sd_request.is_img2img:
                pipeline_classname_ = StableDiffusionControlNetImg2ImgPipeline
            elif self.sd_request.is_txt2img:
                pipeline_classname_ = StableDiffusionControlNetPipeline
            elif self.sd_request.generator_settings.section == GeneratorSection.OUTPAINT.value:
                pipeline_classname_ = StableDiffusionControlNetInpaintPipeline
            else:
                pipeline_classname_ = StableDiffusionControlNetPipeline
        elif self.sd_request.generator_settings.section == GeneratorSection.DEPTH2IMG.value:
            pipeline_classname_ = StableDiffusionDepth2ImgPipeline
        elif self.sd_request.generator_settings.section == GeneratorSection.OUTPAINT.value:
            pipeline_classname_ = AutoPipelineForInpainting
        elif self.sd_request.generator_settings.section == GeneratorSection.PIX2PIX.value:
            pipeline_classname_ = StableDiffusionInstructPix2PixPipeline
        elif self.sd_request.is_img2img:
            pipeline_classname_ = StableDiffusionImg2ImgPipeline
        else:
            pipeline_classname_ = StableDiffusionPipeline
        return pipeline_classname_

    def __load_model(self):
        self.logger.debug("Loading model")
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        kwargs = {}

        already_loaded = self.__do_reuse_pipeline and not self.reload_model

        # move all models except for our current action to the CPU
        if not already_loaded or self.reload_model:
            self.__unload_unused_models()
        # elif self.pipe is None and self.__do_reuse_pipeline or self.pipe:
        #     self.__reuse_pipeline()

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

            if self.is_single_file:
                try:
                    self.logger.debug(f"Loading ckpt file {self.model_path}")
                    self.pipe = self.__download_from_original_stable_diffusion_ckpt()
                    if self.pipe is not None:
                        self.pipe.scheduler = self.load_scheduler(config=self.pipe.scheduler.config)
                except Exception as e:
                    self.logger.error(f"Failed to load model from ckpt: {e}")
            elif self.model is not None:
                self.logger.debug(
                    f"Loading model `{self.model['name']}` `{self.model_path}` for {self.sd_request.generator_settings.section}")

                pipeline_classname_ = self.__pipeline_class()

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
                        controlnet=self.controlnet,
                        scheduler=self.scheduler,
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

            self.make_stable_diffusion_memory_efficient()

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

    def __get_pipeline_action(self, action=None):
        action = self.sd_request.generator_settings.section if not action else action
        if action == "txt2img" and self.sd_request.is_img2img:
            action = "img2img"
        return action

    def __download_from_original_stable_diffusion_ckpt(self):
        pipe = None
        data = {
            "checkpoint_path_or_dict": self.model_path,
            "device": self.device,
            "scheduler_type": Scheduler.DDIM.value.lower(),
            "from_safetensors": self.is_safetensors,
            "local_files_only": True,
            "extract_ema": False,
            "config_files": CONFIG_FILES,
            "pipeline_class": self.__pipeline_class(),
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

    def __prepare_model(self):
        self.logger.info("Prepare model")
        if not self.model:
            return
        self._previous_model = self.current_model
        if self.is_single_file:
            self.current_model = self.model
        else:
            self.current_model = self.model_path
            self.current_model_branch = self.model["branch"]

    # def __reuse_pipeline(self):
    #     self.logger.debug("Reusing pipeline")
    #     pipe = None
    #     if self.sd_request.is_txt2img:
    #         pipe = self.img2img if self.txt2img is None else self.txt2img
    #     elif self.sd_request.is_img2img:
    #         pipe = self.txt2img if self.img2img is None else self.img2img
    #     if pipe is None:
    #         self.logger.warning("Failed to reuse pipeline")
    #         self.clear_controlnet()
    #         return
    #     kwargs = pipe.components
    #
    #     # either load from a pretrained model or from a pipe
    #     if self.settings["controlnet_enabled"]:
    #         pipe = self.load_controlnet_from_ckpt(pipe)
    #         kwargs["controlnet"] = self.controlnet
    #     else:
    #         if "controlnet" in kwargs:
    #             del kwargs["controlnet"]
    #
    #         if self.is_single_file:
    #             if self.model_version == "SDXL 1.0":
    #                 pipeline_class_ = StableDiffusionXLPipeline
    #             else:
    #                 pipeline_class_ = StableDiffusionPipeline
    #
    #             pipe = pipeline_class_.from_single_file(
    #                 self.model_path,
    #                 local_files_only=True
    #             )
    #             return pipe
    #         else:
    #             components = pipe.components
    #             if "controlnet" in components:
    #                 del components["controlnet"]
    #             components["controlnet"] = self.controlnet
    #
    #             pipe = AutoPipelineForText2Image.from_pretrained(
    #                 os.path.expanduser(
    #                     os.path.join(
    #                         self.settings["path_settings"]["txt2img_model_path"],
    #                         self.model_path
    #                     )
    #                 ),
    #                 **components
    #             )
    #
    #     if self.sd_request.is_txt2img:
    #         self.txt2img = pipe
    #         self.img2img = None
    #     elif self.sd_request.is_img2img:
    #         self.img2img = pipe
    #         self.txt2img = None

    def __load_generator_arguments(
        self,
        settings: dict,
        sd_request: SDRequest,
        generator_request_data: dict
    ):
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        requested_model = settings["generator_settings"]["model"]
        model = sd_request.generator_settings.model
        self.logger.debug(f"Model changed clearing")

        model_changed = (
            model is not None and
            model is not None and
            model != requested_model
        )
        if model_changed:
            self.__handle_model_changed()
            self.clear_scheduler()
            self.clear_controlnet()

        # Set a reference to pipe
        is_txt2img = sd_request.is_txt2img
        is_img2img = sd_request.is_img2img
        is_outpaint = sd_request.is_outpaint
        controlnet_image = self.get_controlnet_image()
        self.data = sd_request(
            model_data=model,
            extra_options={},
            callback=self.__callback,
            cross_attention_kwargs_scale=(
                    not sd_request.is_pix2pix and
                    len(self.available_lora) > 0 and
                    len(self.loaded_lora) > 0
            ),
            latents=self.latents,
            device=self.device,
            generator=self.__generator(),
            model_changed=model_changed,
            prompt_embeds=sd_request.prompt_embeds,
            negative_prompt_embeds=sd_request.negative_prompt_embeds,
            controlnet_image=controlnet_image,
            generator_request_data=generator_request_data
        )

        pipe = None
        pipeline_class_ = None

        if sd_request.is_txt2img and not is_txt2img:
            if is_img2img:
                pipe = self.img2img
            elif is_outpaint:
                pipe = self.outpaint
            if pipe is not None:
                pipeline_class_ = StableDiffusionPipeline
                if sd_request.generator_settings.enable_controlnet:
                    pipeline_class_ = StableDiffusionControlNetPipeline
                self.pipe = pipeline_class_(**pipe.components)
        elif sd_request.is_img2img and not is_img2img:
            if is_txt2img:
                pipe = self.txt2img
            elif is_outpaint:
                pipe = self.outpaint
            if pipe is not None:
                pipeline_class_ = StableDiffusionImg2ImgPipeline
                if sd_request.generator_settings.enable_controlnet:
                    pipeline_class_ = StableDiffusionControlNetImg2ImgPipeline
                self.pipe = pipeline_class_(**pipe.components)
        elif sd_request.is_outpaint and not is_outpaint:
            if is_txt2img:
                pipe = self.txt2img
            elif is_img2img:
                pipe = self.img2img
            pipeline_class_ = StableDiffusionInpaintPipeline
            if sd_request.generator_settings.enable_controlnet:
                pipeline_class_ = StableDiffusionControlNetInpaintPipeline

        if pipe is not None and pipeline_class_ is not None:
            self.pipe = pipeline_class_(**pipe.components)

        self.requested_data = self.data
        self.model_version = sd_request.generator_settings.version
        self.is_sd_xl = self.model_version == StableDiffusionVersion.SDXL1_0.value or self.is_sd_xl_turbo
        self.is_sd_xl_turbo = self.model_version == StableDiffusionVersion.SDXL_TURBO.value
        self.is_turbo = self.model_version == StableDiffusionVersion.SD_TURBO.value
        self.use_compel = (
                not sd_request.memory_settings.use_enable_sequential_cpu_offload and
                not self.is_sd_xl and
                not self.is_sd_xl_turbo and
                not self.is_turbo
        )
        self.__generator().manual_seed(sd_request.generator_settings.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)