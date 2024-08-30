import base64
import ctypes
import io
import os
import threading
import time

import numpy as np
from PySide6.QtWidgets import QApplication
from typing import List
import torch
from PIL import Image
from diffusers import StableDiffusionControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, \
    StableDiffusionControlNetInpaintPipeline, StableDiffusionXLPipeline, \
    StableDiffusionXLImg2ImgPipeline, StableDiffusionXLInpaintPipeline, StableDiffusionXLControlNetPipeline, \
    StableDiffusionXLControlNetImg2ImgPipeline, StableDiffusionXLControlNetInpaintPipeline

from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion import StableDiffusionPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_img2img import StableDiffusionImg2ImgPipeline
from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion_inpaint import StableDiffusionInpaintPipeline
from transformers import AutoTokenizer

from airunner.enums import (
    SignalCode,
    SDMode,
    StableDiffusionVersion,
    ModelStatus,
    ModelType, HandlerState
)
from airunner.exceptions import PipeNotLoadedException, SafetyCheckerNotLoadedException, InterruptedException, \
    ThreadInterruptException
from airunner.settings import BASE_PATH
from airunner.utils.clear_memory import clear_memory

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)
CONTROLNET_PIPELINES_SD = (
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline
)
CONTROLNET_PIPELINES_SDXL = (
    StableDiffusionXLControlNetPipeline,
    StableDiffusionXLControlNetImg2ImgPipeline,
    StableDiffusionXLControlNetInpaintPipeline
)


class ModelMixin:
    def __init__(self, *args, **kwargs):
        self.model_version = ""
        self.is_sd_xl_turbo = False
        self.is_sd_xl = False
        self.is_turbo = False
        self.do_generate = False

        self.data = None
        self.txt2img = None
        self.img2img = None
        self.pix2pix = None
        self.outpaint = None
        self.depth2img = None
        self.reload_model = False
        self.batch_size = 1
        self.moved_to_cpu = False
        self.__generator = None
        self.__tokenizer = None
        self.__current_tokenizer_path = ""
        self._pipe = None
        self.__sd_model_status = ModelStatus.UNLOADED
        self.__tokenizer_status = ModelStatus.UNLOADED
        self.cancel_load_flag = False
        self.load_thread = None

        self.register(SignalCode.QUIT_APPLICATION, self.action_quit_triggered)

    @property
    def sd_model_status(self):
        return self.__sd_model_status

    def action_quit_triggered(self, _message=None):
        pass

    def on_unload_stablediffusion_signal(self, _message: dict = None):
        self.unload_image_generator_model()

    def on_tokenizer_load_signal(self, _data: dict = None):
        self.__load_tokenizer()

    def on_tokenizer_unload_signal(self, _data: dict = None):
        self.__unload_tokenizer()

    @property
    def enable_controlnet(self):
        return self.settings["controlnet_enabled"]

    @property
    def is_single_file(self) -> bool:
        return self.__is_ckpt_file or self.__is_safetensors

    @property
    def __is_ckpt_file(self) -> bool:
        if not self.model_path:
            self.logger.error("ckpt path is empty")
            return False
        return self.model_path.endswith(".ckpt")

    @property
    def __is_safetensors(self) -> bool:
        if not self.model_path:
            self.logger.error("safetensors path is empty")
            return False
        return self.model_path.endswith(".safetensors")

    @property
    def model_path(self):
        generator_settings = self.settings["generator_settings"]
        model_name = generator_settings["model"]
        version = generator_settings["version"]
        section = generator_settings["section"]
        for model in self.settings["ai_models"]:
            if (
                model["name"] == model_name and
                model["version"] == version and
                model["pipeline_action"] == section
            ):
                return os.path.expanduser(
                    os.path.join(
                        self.settings["path_settings"]["base_path"],
                        "art/models",
                        version,
                        section,
                        model["path"]
                    )
                )

    @property
    def __tokenizer_path(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["base_path"],
                "art/models",
                "SD 1.5",
                "feature_extractor",
                "openai/clip-vit-large-patch14"
            )
        )

    @staticmethod
    def __is_pytorch_error(e) -> bool:
        return "PYTORCH_CUDA_ALLOC_CONF" in str(e)
        self.cancel_load_flag = Falsed

    def unload_image_generator_model(self):
        self.emit_signal(SignalCode.INTERRUPT_IMAGE_GENERATION_SIGNAL)
        self.__unload_model()
        self.__do_reset_applied_memory_settings()
        clear_memory()

    def cancel_load(self):
        self.cancel_load_flag = True
        if self.load_thread:
            self.raise_exception_in_thread(self.load_thread, ThreadInterruptException)

    def raise_exception_in_thread(self, thread, exception):
        if not thread.is_alive():
            return

        thread_id = next(t.ident for t in threading.enumerate() if t is thread)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(exception))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            raise SystemError("PyThreadState_SetAsyncExc failed")


    def load_image_generator_model(self):
        self.logger.info("Loading image generator model")
        self.load_thread = threading.current_thread()

        # Unload the pipeline if it is already loaded
        if self.pipe:
            self.__unload_tokenizer()
            self.unload_image_generator_model()

        self.model_version = self.settings["generator_settings"]["version"]
        self.is_sd_xl_turbo = self.model_version == StableDiffusionVersion.SDXL_TURBO.value
        self.is_sd_xl = self.model_version == StableDiffusionVersion.SDXL1_0.value or self.is_sd_xl_turbo

        try:
            self.__load_generator(torch.device(self.device), self.settings["generator_settings"]["seed"])
            self.__load_tokenizer()
            self.__prepare_model()
            self.__load_model()
            self.__move_model_to_device()
            self.load_scheduler()
        except ThreadInterruptException:
            self.logger.info("Model loading was interrupted.")
            self.__unload_model()
            self.__do_reset_applied_memory_settings()
            clear_memory()
            return

    @property
    def use_compel(self):
        return (
            not self.sd_request.memory_settings.use_enable_sequential_cpu_offload
            and self.settings["generator_settings"]['use_compel']
        )

    def generate(
        self,
        settings: dict,
        generator_request_data: dict
    ):
        if not self.pipe:
            self.load_stable_diffusion()
            if not self.pipe:
                raise PipeNotLoadedException()
        while self.sd_model_status is not ModelStatus.LOADED:
            time.sleep(0.1)
        self.__load_generator_arguments(settings, generator_request_data)
        self.do_generate = False
        return self.__generate()

    def model_is_loaded(self, model: ModelType) -> bool:
        return self.model_status[model] == ModelStatus.LOADED

    def apply_tokenizer_to_pipe(self):
        self.__change_sd_tokenizer_status(ModelStatus.LOADED)

    def __move_model_to_device(self):
        if self.pipe:
            self.pipe.to(self.data_type)

    def __callback(self, step: int, _time_step, latents):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": step,
            "total": self.sd_request.generator_settings.steps
        })
        if self.latents_set is False:
            self.latents = latents
        QApplication.processEvents()
        return {}

    def __prepare_data(self):
        data = self.data.copy()

        if type(self.pipe) in [StableDiffusionXLPipeline, StableDiffusionPipeline] and "image" in data:
            del data["image"]

        prompt_embeds = None
        negative_prompt_embeds = None
        pooled_prompt_embeds = None
        negative_pooled_prompt_embeds = None

        if self.is_sd_xl:
            self.pipe.to(self.device)
            (
                prompt_embeds,
                negative_prompt_embeds,
                pooled_prompt_embeds,
                negative_pooled_prompt_embeds,
            ) = self.pipe.encode_prompt(
                prompt=self.settings["generator_settings"]["prompt"],
                negative_prompt=self.settings["generator_settings"]["negative_prompt"],
                prompt_2=self.settings["generator_settings"]["second_prompt"],
                negative_prompt_2=self.settings["generator_settings"]["second_negative_prompt"],
                device=self.device,
                num_images_per_prompt=1,
                clip_skip=self.settings["generator_settings"]["clip_skip"],
            )
        elif self.use_compel:
            prompt_embeds = self.prompt_embeds
            negative_prompt_embeds = self.negative_prompt_embeds
            pooled_prompt_embeds = self.pooled_prompt_embeds
            negative_pooled_prompt_embeds = self.pooled_negative_prompt_embeds

        if prompt_embeds is not None:
            data.update(dict(
                prompt_embeds=prompt_embeds,
                negative_prompt_embeds=negative_prompt_embeds,
            ))
            for key in ["prompt", "negative_prompt"]:
                if key in data:
                    del data[key]

        if self.is_sd_xl:
            data.update(dict(
                pooled_prompt_embeds=pooled_prompt_embeds,
                negative_pooled_prompt_embeds=negative_pooled_prompt_embeds,
                crops_coords_top_left=self.settings["generator_settings"]["crops_coord_top_left"],
                original_size=self.settings["generator_settings"]["original_size"],
                target_size=self.settings["generator_settings"]["target_size"],
                negative_original_size=self.settings["generator_settings"]["negative_original_size"],
                negative_target_size=self.settings["generator_settings"]["negative_target_size"],
            ))

        for key in ["outpaint_box_rect", "action"]:
            if key in data:
                del data[key]

        data["callback_on_step_end"] = self.__interrupt_callback

        # Clean up the data based on the operation
        if "image" in data and data["image"] is None:
            del data["image"]
        elif "image" not in data and self.sd_request.is_img2img:
            image = self.sd_request.drawing_pad_image
            data["image"] = image

        return data

    def __call_pipe(self):
        """
        Generate an image using the pipe
        :return:
        """
        # Raise an exception if the safety checker is not loaded and we have safety checker enabled
        if not self.safety_checker_ready:
            raise SafetyCheckerNotLoadedException()

        # Prepare the arguments for the pipeline
        data = self.__prepare_data()
        self.__finalize_pipeline(data)

        self.current_state = HandlerState.GENERATING

        # Generate the image
        results = self.pipe(**data)
        images = results.get("images", [])

        # Check if NSFW content is detected and return the results
        return self.check_and_mark_nsfw_images(images)

    def __finalize_pipeline(self, data):
        # Ensure controlnet is applied to the pipeline.
        model_changed = self.sd_request.model_changed
        if self.enable_controlnet and (
            (not hasattr(self.pipe, "controlnet") or not hasattr(self.pipe, "processor")) or
            (self.pipe.controlnet is None or self.pipe.processor is None)
        ):
            self.on_load_controlnet_signal()
            self.apply_controlnet_to_pipe()
            model_changed = True

        if model_changed:
            # Swap the pipeline if the request is different from the current pipeline
            self.__pipe_swap(data)

            # Add lora to the pipeline
            self.add_lora_to_pipe()

            # Clear the memory before generating the image
            clear_memory()

            # Apply memory settings
            self.make_stable_diffusion_memory_efficient()
            self.make_controlnet_memory_efficient()

    def __pipe_swap(self, data):
        enable_controlnet = self.enable_controlnet
        if "image" not in data:
            enable_controlnet = False
        __pipeline_class = self.__pipeline_class(enable_controlnet)
        if type(self.pipe) is not __pipeline_class:
            clear_memory()
            if __pipeline_class in CONTROLNET_PIPELINES_SD or __pipeline_class in CONTROLNET_PIPELINES_SDXL:
                self.pipe = __pipeline_class.from_pipe(self.pipe, controlnet=self.controlnet)
            else:
                self.pipe = __pipeline_class.from_pipe(self.pipe)
            clear_memory()
            self.make_stable_diffusion_memory_efficient()

    def __interrupt_callback(self, _pipe, _i, _t, callback_kwargs):
        if self.do_interrupt_image_generation:
            self.do_interrupt_image_generation = False
            raise InterruptedException()
        return callback_kwargs

    def __generate(self):
        if not self.pipe:
            raise PipeNotLoadedException()
        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, f"Generating media")
        self.emit_signal(SignalCode.LOG_STATUS_SIGNAL, "Generating image")
        self.emit_signal(SignalCode.VISION_CAPTURE_LOCK_SIGNAL)

        images, nsfw_content_detected = self.__call_pipe()

        self.emit_signal(SignalCode.VISION_CAPTURE_UNLOCK_SIGNAL)

        return self.__image_handler(
            images,
            nsfw_content_detected
        )

    @staticmethod
    def __convert_image_to_base64(image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return base64.encodebytes(img_byte_arr).decode('ascii')

    def __apply_filters_to_image(self, image):
        return self.apply_filters(image, self.filters)

    def __process_images(self, images: List[Image.Image], do_base64: bool, has_filters: bool):
        for i, image in enumerate(images):
            if has_filters:
                image = self.__apply_filters_to_image(image)
            if do_base64:
                image = self.__convert_image_to_base64(image)
            images[i] = image
        return images

    def __image_handler(self, images: List[Image.Image], nsfw_content_detected: List[bool]):
        self._final_callback()
        if images is None:
            return

        if self.data is not None:
            self.data["original_model_data"] = self.original_model_data or {}

        if images:
            do_base64 = self.data.get("do_base64", False)
            has_filters = self.filters is not None and len(self.filters) > 0
            images = self.__process_images(
                images,
                do_base64,
                has_filters
            )

        return dict(
            images=images,
            data=self.data,
            nsfw_content_detected=any(nsfw_content_detected),
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
        self.remove_safety_checker_from_pipe()
        self.pipe = None
        self.on_unload_controlnet_signal()
        self.__change_sd_model_status(ModelStatus.UNLOADED)

    def __change_sd_model_status(self, status: ModelStatus):
        self.__sd_model_status = status
        self.change_model_status(ModelType.SD, status, self.model_path)

    def __change_sd_tokenizer_status(self, status: ModelStatus):
        self.__tokenizer_status = status
        self.change_model_status(ModelType.SD_TOKENIZER, status, self.__tokenizer_path)

    def __handle_model_changed(self):
        self.reload_model = True

    def __do_reset_applied_memory_settings(self):
        self.emit_signal(SignalCode.RESET_APPLIED_MEMORY_SETTINGS)

    def __pipeline_class(self, enable_controlnet):
        operation_type = self.sd_request.section
        if enable_controlnet:
            operation_type = f"{operation_type}_controlnet"

        pipeline_map = {
            "txt2img": StableDiffusionPipeline,
            "img2img": StableDiffusionImg2ImgPipeline,
            "outpaint": StableDiffusionInpaintPipeline,
            "txt2img_controlnet": StableDiffusionControlNetPipeline,
            "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
            "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline
        }

        if self.is_sd_xl:
            pipeline_map.update(
                {
                    "txt2img": StableDiffusionXLPipeline,
                    "img2img": StableDiffusionXLImg2ImgPipeline,
                    "outpaint": StableDiffusionXLInpaintPipeline,
                    "txt2img_controlnet": StableDiffusionXLControlNetPipeline,
                    "img2img_controlnet": StableDiffusionXLControlNetImg2ImgPipeline,
                    "outpaint_controlnet": StableDiffusionXLControlNetInpaintPipeline
                }
            )

        return pipeline_map.get(operation_type)

    def __load_model(self):
        self.logger.debug("Loading model")
        if not self.model_path:
            self.logger.error("Model path is empty")
            return
        self.torch_compile_applied = False
        self.lora_loaded = False
        self.embeds_loaded = False

        if self.pipe is None or self.reload_model:
            self.__change_sd_model_status(ModelStatus.LOADING)

            self.logger.debug(
                f"Loading model from scratch {self.reload_model} for {self.sd_request.section}")

            self.reset_applied_memory_settings()

            self.logger.debug(f"Loading model `{self.model_path}` for {self.sd_request.section}")

            pipeline_class_ = self.__pipeline_class(self.settings["controlnet_enabled"])

            data = dict(
                torch_dtype=self.data_type,
                use_safetensors=True,
                local_files_only=True,
            )

            safety_checker = self.safety_checker if self.safety_checker_ready else None
            feature_extractor = self.feature_extractor if self.feature_extractor_ready else None

            data.update(
                dict(
                    safety_checker=safety_checker,
                    feature_extractor=feature_extractor,
                    requires_safety_checker=self.settings["nsfw_filter"],
                )
            )

            if self.is_sd_xl:
                data.update(
                    dict(
                        variant="fp16"
                    )
                )

            if self.enable_controlnet:
                data["controlnet"] = self.controlnet

            if self.is_single_file:
                try:
                    self.pipe = pipeline_class_.from_single_file(
                        self.model_path,
                        config=os.path.dirname(self.model_path),
                        add_watermarker=False,
                        **data
                    )
                except FileNotFoundError as e:
                    self.logger.error(f"Failed to load model from {self.model_path}: {e}")
                    self.__change_sd_model_status(ModelStatus.FAILED)
                    return
            else:
                if self.enable_controlnet:
                    data["controlnet"] = self.controlnet

                try:
                    self.pipe = pipeline_class_.from_pretrained(
                        self.model_path,
                        **data
                    )
                except (FileNotFoundError, OSError) as e:
                    self.logger.error(f"Failed to load model from {self.model_path}: {e}")
                    self.__change_sd_model_status(ModelStatus.FAILED)
                    return

            if not self.is_sd_xl:
                self.apply_tokenizer_to_pipe()

            if self.pipe is None:
                self.__change_sd_model_status(ModelStatus.FAILED)
                return

            self.__change_sd_model_status(ModelStatus.LOADED)

            if self.settings["nsfw_filter"] is False:
                self.remove_safety_checker_from_pipe()

            old_model_path = self.current_model

            self.current_model = self.model_path
            self.current_model = old_model_path
            self.controlnet_loaded = self.settings["controlnet_enabled"]

    def __get_pipeline_action(self, action=None):
        action = self.sd_request.section if not action else action
        if action == "txt2img" and self.sd_request.is_img2img:
            action = "img2img"
        return action

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

        model_changed = (
            model is not None and
            model is not None and
            model != requested_model
        )
        if model_changed:
            self.logger.debug(f"Model changed clearing")
            self.__handle_model_changed()
            self.clear_scheduler()
            self.clear_controlnet()

        # Set a reference to pipe
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
            controlnet_image=controlnet_image,
            generator_request_data=generator_request_data
        )
        self.__generator.manual_seed(self.sd_request.generator_settings.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)

    def __unload_tokenizer(self):
        self.__tokenizer = None
        self.__change_sd_tokenizer_status(ModelStatus.UNLOADED)
        clear_memory()

    def __load_tokenizer(self):
        if self.is_sd_xl:
            return

        if self.__tokenizer and self.__current_tokenizer_path == self.__tokenizer_path:
            return
        try:
            self.logger.debug(f"Loading tokenizer from {self.__tokenizer_path}")
            self.__tokenizer = AutoTokenizer.from_pretrained(
                self.__tokenizer_path,
                local_files_only=True,
                torch_dtype=self.data_type
            )
            self.__current_tokenizer_path = self.__tokenizer_path
            self.__change_sd_tokenizer_status(ModelStatus.READY)
        except Exception as e:
            self.logger.error(f"Failed to load tokenizer")
            self.logger.error(e)
            self.__change_sd_tokenizer_status(ModelStatus.FAILED)
