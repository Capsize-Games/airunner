import base64
import io
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
from diffusers import StableDiffusionControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, \
    StableDiffusionControlNetInpaintPipeline, AutoencoderKL
from diffusers.models.modeling_utils import load_state_dict

from diffusers.utils.torch_utils import randn_tensor
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_depth2img import StableDiffusionDepth2ImgPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_instruct_pix2pix import StableDiffusionInstructPix2PixPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img import StableDiffusionImg2ImgPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_inpaint import StableDiffusionInpaintPipeline
from safetensors.torch import load_file
from transformers import CLIPTokenizer

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
from diffusers.loaders.single_file_utils import create_text_encoder_from_ldm_clip_checkpoint

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
        self.__generator = None
        self.__text_encoder = None

    def is_ckpt_file(self, model_path) -> bool:
        if not model_path:
            self.logger.error("ckpt path is empty")
            return False
        return model_path.endswith(".ckpt")

    def is_safetensor_file(self, model_path) -> bool:
        if not model_path:
            self.logger.error("safetensors path is empty")
            return False
        return model_path.endswith(".safetensors")

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

    @property
    def enable_controlnet(self):
        return (
            self.sd_request.generator_settings.enable_controlnet
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
        self.__load_generator(
            torch.device(self.device),
            self.settings["generator_settings"]["seed"]
        )
        self.__prepare_model()
        self.__load_model()
        self.__move_model_to_device()

    def generate(
        self,
        settings: dict,
        generator_request_data: dict
    ):
        if not self.pipe:
            raise PipeNotLoadedException()
        self.__load_generator_arguments(settings, generator_request_data)
        self.do_generate = False
        self.__swap_pipeline()
        return self.__generate(generator_request_data)

    def __swap_pipeline(self):
        if not self.pipe:
            return

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

        operation_type = "txt2img" if is_txt2img else "img2img" if is_img2img else "outpaint"
        if self.enable_controlnet:
            kwargs["controlnet"] = self.pipe.controlnet
            operation_type = f"{operation_type}_controlnet"
        pipeline_class_ = self.__pipeline_class(operation_type)

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
            generator=self.__generator,
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

        self.data["callback_on_step_end"] = self.__interrupt_callback

        results = self.pipe(**self.data)
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

        if self.data is not None:
            self.data["original_model_data"] = self.original_model_data or {}

        has_nsfw = True in nsfw_content_detected if nsfw_content_detected is not None else False

        if images:
            do_base64 = self.data.get("do_base64", False)
            has_filters = self.filters is not None and len(self.filters) > 0
            images = self.__process_images(images, do_base64, has_filters, nsfw_content_detected)

        return dict(
            images=images,
            data=self.data,
            nsfw_content_detected=has_nsfw,
        )

    def __load_generator(self, device=None, seed=None):
        if self.__generator is None:
            device = self.device if not device else device
            if seed is None:
                seed = int(self.settings["generator_settings"]["seed"])
            self.__generator = torch.Generator(device=device).manual_seed(seed)
        return self.__generator

    def __unload_model(self):
        self.logger.debug("Unloading model")
        self.pipe = None
        self.change_model_status(ModelType.SD, ModelStatus.UNLOADED, "")

    def __handle_model_changed(self):
        self.reload_model = True

    def __do_reset_applied_memory_settings(self):
        self.emit_signal(SignalCode.RESET_APPLIED_MEMORY_SETTINGS)

    def __unload_unused_models(self):
        self.logger.debug("Unloading unused models")
        for action in AVAILABLE_ACTIONS:
            if action in ["controlnet", "safety_checker"]:
                continue
            val = getattr(self, action)
            if val:
                self.logger.debug(f"Unloading model {action}")
                val.to("cpu")
                setattr(self, action, None)
                del val
        clear_memory()
        self.reset_applied_memory_settings()

    def __pipeline_class(self, operation_type=None):
        if operation_type is None:
            operation_type = self.sd_request.generator_settings.section

        if self.enable_controlnet:
            operation_type = f"{operation_type}_controlnet"

        pipeline_map = {
            "txt2img": StableDiffusionPipeline,
            "img2img": StableDiffusionImg2ImgPipeline,
            "outpaint": StableDiffusionInpaintPipeline,
            "txt2img_controlnet": StableDiffusionControlNetPipeline,
            "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
            "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline
        }

        return pipeline_map.get(operation_type)

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

        if self.pipe is None or self.reload_model:
            self.change_model_status(ModelType.SD, ModelStatus.LOADING, self.model_path)

            self.logger.debug(
                f"Loading model from scratch {self.reload_model} for {self.sd_request.generator_settings.section}")

            self.reset_applied_memory_settings()

            if self.is_single_file:
                self._load_tokenizer()
                self.__load_text_encoder()

                data = dict(
                    from_safetensors=True,
                    local_files_only=True,
                    tokenizer=self.__tokenizer,
                    text_encoder=self.__text_encoder,
                    torch_dtype=self.data_type
                )

                if self.enable_controlnet:
                    data["controlnet"] = self.controlnet
                    self.pipe = StableDiffusionControlNetPipeline.from_single_file(
                        self.model_path,
                        **data
                    )
                else:
                    self.pipe = StableDiffusionPipeline.from_single_file(
                        self.model_path,
                        **data
                    )
                if self.pipe is not None:
                    self.pipe.scheduler = self.load_scheduler(config=self.pipe.scheduler.config)
            elif self.model_path is not None:
                self.logger.debug(
                    f"Loading model `{self.model_path}` for {self.sd_request.generator_settings.section}")

                kwargs.update(dict(
                    torch_dtype=self.data_type,
                    safety_checker=self.safety_checker,
                    feature_extractor=self.feature_extractor,
                    use_safetensors=True,
                    controlnet=self.controlnet,
                    scheduler=self.scheduler,
                ))
                # path = os.path.expanduser(
                #     os.path.join(
                #         self.settings["path_settings"][
                #             f"{self.sd_request.generator_settings.section}_model_path"],
                #         self.model_path
                #     )
                # )
                pipeline_class_ = self.__pipeline_class()
                self.pipe = pipeline_class_.from_pretrained(
                    self.model_path,
                    **kwargs
                )

            if self.pipe is None:
                self.change_model_status(ModelType.SD, ModelStatus.FAILED, self.model_path)
                return

            self.make_stable_diffusion_memory_efficient()
            self.change_model_status(ModelType.SD, ModelStatus.LOADED, self.model_path)

            if self.settings["nsfw_filter"] is False:
                self.pipe.safety_checker = None
                self.pipe.feature_extractor = None

            if self.pipe is None:
                self.emit_signal(SignalCode.LOG_ERROR_SIGNAL, "Failed to load model")
                return

            old_model_path = self.current_model

            self.current_model = self.model_path
            self.current_model = old_model_path
            self.controlnet_loaded = self.settings["controlnet_enabled"]

    def _load_tokenizer(self):
        path = os.path.dirname(self.model_path)
        path = f"/home/joe/.airunner/art/models/txt2img/SD 1.5/runwayml/stable-diffusion-v1-5/tokenizer"
        self.logger.debug(f"Loading tokenizer from {path}")
        try:
            self.__tokenizer = CLIPTokenizer.from_pretrained(path, local_files_only=True)
            self.change_model_status(ModelType.SD_TOKENIZER, ModelStatus.LOADED, path)
        except Exception as e:
            self.logger.error(f"Failed to load tokenizer")
            self.logger.error(e)
            self.change_model_status(ModelType.SD_TOKENIZER, ModelStatus.FAILED, path)

    def __get_pipeline_action(self, action=None):
        action = self.sd_request.generator_settings.section if not action else action
        if action == "txt2img" and self.sd_request.is_img2img:
            action = "img2img"
        return action

    def __load_text_encoder(self):
        checkpoint = load_state_dict(self.model_path)

        text_encoder_path = os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["feature_extractor_model_path"],
                "openai/clip-vit-large-patch14"
            )
        )
        self.__text_encoder = create_text_encoder_from_ldm_clip_checkpoint(
            text_encoder_path,
            checkpoint,
            local_files_only=True,
            torch_dtype=self.data_type
        )


    def __prepare_model(self):
        self.logger.info("Prepare model")
        if not self.model_path:
            return
        self._previous_model = self.current_model
        self.current_model = self.model_path

    def __load_generator_arguments(
        self,
        settings: dict,
        generator_request_data: dict
    ):
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        requested_model = settings["generator_settings"]["model"]
        model = self.sd_request.generator_settings.model
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
        is_txt2img = self.sd_request.is_txt2img
        is_img2img = self.sd_request.is_img2img
        is_outpaint = self.sd_request.is_outpaint
        controlnet_image = self.get_controlnet_image()
        self.data = self.sd_request(
            model_data=model,
            extra_options={},
            callback=self.__callback,
            cross_attention_kwargs_scale=(
                    not self.sd_request.is_pix2pix and
                    len(self.available_lora) > 0 and
                    len(self.loaded_lora) > 0
            ),
            latents=self.latents,
            device=self.device,
            generator=self.__generator,
            model_changed=model_changed,
            prompt_embeds=self.sd_request.prompt_embeds,
            negative_prompt_embeds=self.sd_request.negative_prompt_embeds,
            controlnet_image=controlnet_image,
            generator_request_data=generator_request_data
        )

        pipe = None
        pipeline_class_ = None

        if self.sd_request.is_txt2img and not is_txt2img:
            if is_img2img:
                pipe = self.img2img
            elif is_outpaint:
                pipe = self.outpaint
            if pipe is not None:
                if self.enable_controlnet:
                    pipeline_class_ = StableDiffusionControlNetPipeline
                else:
                    pipeline_class_ = StableDiffusionPipeline
                self.pipe = pipeline_class_(**pipe.components)
        elif self.sd_request.is_img2img and not is_img2img:
            if is_txt2img:
                pipe = self.txt2img
            elif is_outpaint:
                pipe = self.outpaint
            if pipe is not None:
                if self.enable_controlnet:
                    pipeline_class_ = StableDiffusionControlNetImg2ImgPipeline
                else:
                    pipeline_class_ = StableDiffusionImg2ImgPipeline
                self.pipe = pipeline_class_(**pipe.components)
        elif self.sd_request.is_outpaint and not is_outpaint:
            if is_txt2img:
                pipe = self.txt2img
            elif is_img2img:
                pipe = self.img2img
            if pipe is not None:
                if self.enable_controlnet:
                    pipeline_class_ = StableDiffusionControlNetInpaintPipeline
                else:
                    pipeline_class_ = StableDiffusionInpaintPipeline

        if pipe is not None and pipeline_class_ is not None:
            self.pipe = pipeline_class_(**pipe.components)

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
        self.__generator.manual_seed(self.sd_request.generator_settings.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
