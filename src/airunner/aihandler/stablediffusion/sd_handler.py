import os
from typing import Any, List

import diffusers
import numpy as np
import tomesd
import torch
from DeepCache import DeepCacheSDHelper
from PIL import (
    ImageDraw,
    ImageFont
)
from PySide6.QtCore import QRect, QThread, Slot, Signal
from PySide6.QtWidgets import QApplication
from compel import Compel, DiffusersTextualInversionManager, ReturnedEmbeddingsType
from controlnet_aux.processor import Processor
from diffusers import StableDiffusionPipeline, StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline, \
    StableDiffusionControlNetPipeline, StableDiffusionControlNetImg2ImgPipeline, \
    StableDiffusionControlNetInpaintPipeline, StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, \
    StableDiffusionXLInpaintPipeline, StableDiffusionXLControlNetPipeline, StableDiffusionXLControlNetImg2ImgPipeline, \
    StableDiffusionXLControlNetInpaintPipeline, ControlNetModel
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from transformers import CLIPFeatureExtractor, CLIPTokenizerFast

from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import (
    SDMode, StableDiffusionVersion, GeneratorSection, ModelStatus, ModelType, SignalCode, HandlerState,
    EngineResponseCode
)
from airunner.exceptions import PipeNotLoadedException, InterruptedException
from airunner.settings import MIN_NUM_INFERENCE_STEPS_IMG2IMG
from airunner.utils.clear_memory import clear_memory
from airunner.utils.get_torch_device import get_torch_device

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class SDHandler(BaseHandler):
    def  __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_status = ModelStatus.UNLOADED
        self.model_type = "sd"
        self._current_model:str = ""
        self._controlnet:ControlNetModel = None
        self._controlnet_processor:Processor = None
        self._safety_checker:StableDiffusionSafetyChecker = None
        self._feature_extractor:CLIPFeatureExtractor = None
        self._memory_settings_flags:dict = {
            "torch_compile_applied": False,
            "vae_slicing_applied": None,
            "last_channels_applied": None,
            "attention_slicing_applied": None,
            "tiled_vae_applied": None,
            "accelerated_transformers_applied": None,
            "cpu_offload_applied": None,
            "model_cpu_offload_applied": None,
            "tome_sd_applied": None,
            "tome_ratio": 0.0,
            "use_enable_sequential_cpu_offload": None,
            "enable_model_cpu_offload": None,
            "use_tome_sd": None,
        }
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
        self._pooled_prompt_embeds = None
        self._negative_pooled_prompt_embeds = None
        self._pipe = None
        self._current_prompt:str = ""
        self._current_negative_prompt: str = ""
        self._current_prompt_2: str = ""
        self._current_negative_prompt_2: str = ""
        self._tokenizer: CLIPTokenizerFast = None
        self._generator: torch.Generator = None
        self._latents = None
        self._textual_inversion_manager: DiffusersTextualInversionManager = None
        self._compel_proc: Compel = None
        self._loaded_lora: List = []
        self._disabled_lora: List = []
        self._loaded_embeddings: List = []
        self._current_state: HandlerState = HandlerState.UNINITIALIZED
        self._deep_cache_helper: DeepCacheSDHelper = None
        self.do_interrupt_image_generation = False
        self._sd_status = ModelStatus.UNLOADED
        self._controlnet_status = ModelStatus.UNLOADED
        self._safety_checker_status = ModelStatus.UNLOADED
        self._section = None

    @Slot(str)
    def _handle_worker_error(self, error_message):
        self.logger.error(f"Worker error: {error_message}")

    @property
    def is_single_file(self) -> bool:
        return self.is_ckpt_file or self.is_safetensors

    @property
    def is_ckpt_file(self) -> bool:
        if not self.model_path:
            self.logger.error("ckpt path is empty")
            return False
        return self.model_path.endswith(".ckpt")

    @property
    def is_safetensors(self) -> bool:
        if not self.model_path:
            self.logger.error("safetensors path is empty")
            return False
        return self.model_path.endswith(".safetensors")

    @property
    def is_sd_xl(self) -> bool:
        return self.generator_settings.version == StableDiffusionVersion.SDXL1_0.value

    @property
    def is_sd_xl_turbo(self) -> bool:
        return self.generator_settings.version == StableDiffusionVersion.SDXL_TURBO.value

    @property
    def section(self):
        if self._section is None:
            section = GeneratorSection.TXT2IMG
            if self.image_to_image_settings.image is not None or self.drawing_pad_settings.image is not None:
                section = GeneratorSection.IMG2IMG
            if self.outpaint_image is not None and self.outpaint_settings.enabled:
                section = GeneratorSection.OUTPAINT
            self.section = section
        return self._section

    @section.setter
    def section(self, value):
        self._section = value

    @property
    def model_path(self):
        base_path:str = self.path_settings.base_path
        model_name:str = self._current_model
        version:str = self.generator_settings.version
        section:str = self.generator_settings.section
        for model in self.ai_models:
            model_path:str = model.path
            if (
                model.name == model_name and
                model.version == version and
                model.pipeline_action == section
            ):
                return os.path.expanduser(
                    os.path.join(
                        base_path,
                        "art/models",
                        version,
                        section,
                        model_path
                    )
                )

    @property
    def enable_controlnet(self):
        return self.controlnet_settings.enabled

    @property
    def data_type(self):
        return torch.float16

    @property
    def use_safety_checker(self):
        return self.application_settings.nsfw_filter

    @property
    def safety_checker_initialized(self) -> bool:
        try:
            return not self.use_safety_checker or (
                self._safety_checker is not None and
                self._feature_extractor is not None and
                self._pipe.safety_checker is not None and
                self._pipe.feature_extractor is not None
            )
        except AttributeError:
            pass
        return False

    @property
    def controlnet_type(self):
        controlnet = self.controlnet_image_settings.controlnet
        controlnet_item = self.controlnet_model_by_name(controlnet)
        return controlnet_item.name

    @property
    def is_txt2img(self) -> bool:
        return self.section is GeneratorSection.TXT2IMG

    @property
    def is_img2img(self) -> bool:
        return self.section is GeneratorSection.IMG2IMG

    @property
    def is_outpaint(self) -> bool:
        return self.section is GeneratorSection.OUTPAINT

    @property
    def controlnet_enabled(self) -> bool:
        return self.controlnet_settings.enabled

    @property
    def _device(self):
        return get_torch_device(self.memory_settings.default_gpu_sd)

    @property
    def _pipeline_class(self):
        operation_type = "txt2img"
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_outpaint:
            operation_type = "outpaint"

        if self.enable_controlnet:
            operation_type = f"{operation_type}_controlnet"

        if self.is_sd_xl:
            pipeline_map = {
                "txt2img": StableDiffusionXLPipeline,
                "img2img": StableDiffusionXLImg2ImgPipeline,
                "outpaint": StableDiffusionXLInpaintPipeline,
                "txt2img_controlnet": StableDiffusionXLControlNetPipeline,
                "img2img_controlnet": StableDiffusionXLControlNetImg2ImgPipeline,
                "outpaint_controlnet": StableDiffusionXLControlNetInpaintPipeline
            }
        else:
            pipeline_map = {
                "txt2img": StableDiffusionPipeline,
                "img2img": StableDiffusionImg2ImgPipeline,
                "outpaint": StableDiffusionInpaintPipeline,
                "txt2img_controlnet": StableDiffusionControlNetPipeline,
                "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
                "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline
            }
        return pipeline_map.get(operation_type)

    def load_safety_checker(self):
        """
        Public method to load the safety checker model.
        """
        if self._safety_checker_status is ModelStatus.LOADING:
            return
        self._load_safety_checker()

    def unload_safety_checker(self):
        """
        Public method to unload the safety checker model.
        """
        if self._safety_checker_status is ModelStatus.LOADING:
            return
        self._unload_safety_checker()

    def load_controlnet(self):
        """
        Public method to load the controlnet model.
        """
        self._load_controlnet()

    def unload_controlnet(self):
        """
        Public method to unload the controlnet model.
        """
        if self._controlnet_status is ModelStatus.LOADING:
            return
        self._unload_controlnet()

    def load_stable_diffusion(self):
        if self._sd_status is ModelStatus.LOADING:
            return
        self.unload_stable_diffusion()
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._reset_parameters()
        self._load_safety_checker()
        self._load_tokenizer()
        self._load_generator()
        self._load_pipe()
        self._load_scheduler()
        self._load_controlnet()
        self._load_lora()
        self._load_embeddings()
        self._load_compel()
        self._load_deep_cache()
        self._make_memory_efficient()
        self._finalize_load_stable_diffusion()

    def unload_stable_diffusion(self):
        if self._sd_status is ModelStatus.LOADING:
            return
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._unload_safety_checker()
        self._unload_scheduler()
        self._unload_controlnet()
        self._unload_lora()
        self._unload_emebeddings()
        self._unload_compel()
        self._unload_tokenizer()
        self._unload_generator()
        self._unload_deep_cache()
        self._unload_pipe()
        self._clear_memory_efficient_settings()
        clear_memory()
        self.change_model_status(ModelType.SD, ModelStatus.UNLOADED)

    def handle_generate_signal(self, message: dict=None):
        if self._model_status is not ModelStatus.LOADED:
            self.load_stable_diffusion()

        if self._current_state not in (
            HandlerState.GENERATING,
            HandlerState.PREPARING_TO_GENERATE
        ):
            self._current_state = HandlerState.PREPARING_TO_GENERATE
            try:
                response = self._generate()
            except PipeNotLoadedException as e:
                self.logger.warning(e)
                response = None
            except Exception as e:
                self.logger.error(f"Error generating image: {e}")
                response = None
            print("HANDLE GENERATE SIGNAL", message)
            if message is not None:
                callback = message.get("callback", None)
                if callback:
                    callback(message)
            self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
                'code': EngineResponseCode.IMAGE_GENERATED,
                'message': response
            })
            self._current_state = HandlerState.READY

    def load_lora(self):
        self._load_lora()

    def load_embeddings(self):
        self._load_embeddings()

    def interrupt_image_generation(self):
        if self._current_state == HandlerState.GENERATING:
            self.do_interrupt_image_generation = True

    def change_model_status(self, model: ModelType, status: ModelStatus):
        if model is ModelType.SD:
            self._model_status = status
        elif model is ModelType.CONTROLNET:
            self._controlnet_status = status
        elif model is ModelType.SAFETY_CHECKER:
            self._safety_checker_status = status
        super().change_model_status(model, status)

    def _reset_parameters(self):
        self.section = None

    def _generate(self):
        self.logger.debug("Generating image")
        model = self.generator_settings.model
        if self._current_model != model:
            if self._pipe is not None:
                self.unload_stable_diffusion()
                self.load_stable_diffusion()
        if self._pipe is None:
            raise PipeNotLoadedException()
        self._load_prompt_embeds()
        clear_memory()
        args = self._prepare_data()
        self._current_state = HandlerState.GENERATING
        with torch.no_grad():
            results = self._pipe(**args)
        images = results.get("images", [])
        images, nsfw_content_detected = self._check_and_mark_nsfw_images(images)
        if images is not None:
            self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
                "step": self.generator_settings.steps,
                "total": self.generator_settings.steps,
            })

            if images is None:
                return

            if self.application_settings.auto_export_images:
                self._export_images(images)

            return dict(
                images=images,
                data=args,
                nsfw_content_detected=any(nsfw_content_detected)
            )
        else:
            return dict(
                images=[],
                data=args,
                nsfw_content_detected=False
            )

    def _export_images(self, images: List[Any]):
        extension = self.application_settings.image_export_type
        filename = "image"
        i = 1
        for image in images:
            filepath = os.path.expanduser(
                os.path.join(
                    self.path_settings.image_path,
                    f"{filename}.{extension}"
                )
            )
            while os.path.exists(filepath):
                filename = f"image_{i}"
                filepath = os.path.expanduser(
                    os.path.join(
                        self.path_settings.image_path,
                        f"{filename}.{extension}"
                    )
                )
                if not os.path.exists(filepath):
                    break
                i += 1
            image.save(filepath)

    def _check_and_mark_nsfw_images(self, images) -> tuple:
        if not self._feature_extractor or not self._safety_checker:
            return images, [False] * len(images)

        safety_checker_input = self._feature_extractor(images, return_tensors="pt").to(self._device)
        _, has_nsfw_concepts = self._safety_checker(
            images=[np.array(img) for img in images],
            clip_input=safety_checker_input.pixel_values.to(self._device)
        )

        # Mark images as NSFW if NSFW content is detected
        for i, img in enumerate(images):
            if has_nsfw_concepts[i]:
                img = img.convert("RGBA")
                img.paste((0, 0, 0), (0, 0, img.size[0], img.size[1]))

                draw = ImageDraw.Draw(img)
                font = ImageFont.load_default(50)  # load_default() does not support size argument

                # Text you want to center
                text = "NSFW"

                # Calculate the bounding box of the text
                text_bbox = draw.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]

                # Calculate the position to center the text line
                text_x = (img.width - text_width) // 2
                text_y = (img.height - text_height) // 2

                # Draw the text at the calculated position, ensuring the text line is centered
                draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

                images[i] = img

        return images, has_nsfw_concepts

    def _load_safety_checker(self):
        if not self.application_settings.nsfw_filter or self._safety_checker_status is ModelStatus.LOADING:
            return
        self._load_safety_checker_model()
        self._load_feature_extractor()

    def _load_safety_checker_model(self):
        self.logger.debug("Loading safety checker")
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        safety_checker_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models/SD 1.5/safety_checker",
                "CompVis/stable-diffusion-safety-checker/"
            )
        )
        try:
            self._safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                safety_checker_path,
                torch_dtype=self.data_type,
                device_map=self._device,
                local_files_only=True,
                use_safetensors=False
            )
            self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADED)
        except Exception as e:
            self.logger.error(f"Unable to load safety checker: {e}")
            self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.FAILED)

    def _load_feature_extractor(self):
        self.logger.debug("Loading feature extractor")
        self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADING)
        feature_extractor_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models/SD 1.5/feature_extractor",
                "openai/clip-vit-large-patch14/"
            )
        )
        try:
            self._feature_extractor = CLIPFeatureExtractor.from_pretrained(
                feature_extractor_path,
                torch_dtype=self.data_type,
                device_map=self._device,
                local_files_only=True,
                use_safetensors=True
            )
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED)
        except Exception as e:
            self.logger.error(f"Unable to load feature extractor {e}")
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED)

    def _load_tokenizer(self):
        self.logger.debug("Loading tokenizer")
        if self.is_sd_xl:
            return
        tokenizer_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                "SD 1.5",
                "feature_extractor",
                "openai/clip-vit-large-patch14"
            )
        )
        try:
            self.logger.debug(f"ModelMixin: Loading tokenizer from {tokenizer_path}")
            self._tokenizer = CLIPTokenizerFast.from_pretrained(
                tokenizer_path,
                local_files_only=True,
                torch_dtype=self.data_type
            )
        except Exception as e:
            self.logger.error(f"Failed to load tokenizer")
            self.logger.error(e)

    def _load_generator(self, seed=None):
        self.logger.debug("Loading generator")
        if not self._generator is None:
            seed = seed or int(self.generator_settings.seed)
            self._generator = torch.Generator(device=self._device)
            self._generator.manual_seed(seed)
        return self._generator

    def _load_controlnet(self):
        if not self.controlnet_settings.enabled or self._controlnet_status is ModelStatus.LOADING:
            return
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)

        try:
            self._load_controlnet_model()
        except Exception as e:
            self.logger.error(f"Error loading controlnet {e}")
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)
            return

        try:
            self._load_controlnet_processor()
        except Exception as e:
            self.logger.error(f"Error loading controlnet processor {e}")
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)
            return

        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED)

    def _load_controlnet_model(self):
        if self._controlnet is not None:
            return
        self.logger.debug(f"Loading controlnet model")
        name = self.controlnet_type
        controlnet_model = self.controlnet_model_by_name(name)
        if not controlnet_model:
            raise ValueError(f"Unable to find controlnet model {name}")
        controlnet_model_path = controlnet_model.path
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)
        version: str = self.generator_settings.version
        path: str = "diffusers/controlnet-canny-sdxl-1.0-small" if self.is_sd_xl else controlnet_model_path
        controlnet_path = os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "art/models",
            version,
            "controlnet",
            path
        ))
        self._controlnet = ControlNetModel.from_pretrained(
            controlnet_path,
            torch_dtype=self.data_type,
            device=self._device,
            local_files_only=True,
            use_safetensors=True,
            use_fp16=True
        )

    def _load_controlnet_processor(self):
        if self._controlnet_processor is not None:
            return
        self.logger.debug("Loading controlnet processor")
        self._controlnet_processor = Processor(self.controlnet_type)

    def _load_scheduler(self):
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)
        scheduler_name = self.generator_settings.scheduler
        base_path:str = self.path_settings.base_path
        scheduler_version:str = self.generator_settings.version
        scheduler_path = os.path.expanduser(
            os.path.join(
                base_path,
                "art/models",
                scheduler_version,
                "txt2img/scheduler/scheduler_config.json"
            )
        )
        for scheduler in self.schedulers:
            if scheduler.display_name == scheduler_name:
                scheduler_name = scheduler.display_name
                scheduler_class_name = scheduler.name
                scheduler_class = getattr(diffusers, scheduler_class_name)
                try:
                    self.scheduler = scheduler_class.from_pretrained(
                        scheduler_path,
                        subfolder="scheduler",
                        local_files_only=True
                    )
                    self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
                    self.current_scheduler_name = scheduler_name
                    self.logger.debug(f"Loaded scheduler {scheduler_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load scheduler {scheduler_name}: {e}")
                    self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
                    return
                if self._pipe:
                    self._pipe.scheduler = self.scheduler
                return scheduler

    def _load_pipe(self):
        self._current_model = self.generator_settings.model
        data = dict(
            torch_dtype=self.data_type,
            use_safetensors=True,
            local_files_only=True,
            device=self._device,
        )

        if self.enable_controlnet:
            data["controlnet"] = self._controlnet

        pipeline_class_ = self._pipeline_class
        if self.is_single_file:
            try:
                self._pipe = pipeline_class_.from_single_file(
                    self.model_path,
                    config=os.path.dirname(self.model_path),
                    add_watermarker=False,
                    **data
                )
            except FileNotFoundError as e:
                self.logger.error(f"Failed to load model from {self.model_path}: {e}")
                self.change_model_status(ModelType.SD, ModelStatus.FAILED)
                return
            except RuntimeError as e:
                self.logger.warning(f"Failed to load model from {self.model_path}: {e}")
        else:
            if self.enable_controlnet:
                data["controlnet"] = self._controlnet

            try:
                self._pipe = pipeline_class_.from_pretrained(
                    self.model_path,
                    **data
                )
            except (FileNotFoundError, OSError) as e:
                self.logger.error(f"Failed to load model from {self.model_path}: {e}")
                self.change_model_status(ModelType.SD, ModelStatus.FAILED)
                return

        if self._pipe is not None:
            try:
                self._pipe.to(self._device)
            except torch.OutOfMemoryError as e:
                self.logger.error(f"Failed to load model to device: {e}")
            except RuntimeError as e:
                self.logger.error(f"Failed to load model to device: {e}")

    def _load_lora(self):
        self._loaded_lora = []
        available_lora = self.get_lora_by_version(self.generator_settings.version)
        if len(available_lora) == 0:
            return
        self._remove_lora_from_pipe()
        if self._pipe is not None:
            for lora in available_lora:
                if lora.enabled:
                    self._apply_lora(lora, available_lora)
            if len(self.loaded_lora):
                self.logger.debug("LoRA loaded")

    def _apply_lora(self, lora, available_lora):
        if lora.path in self._disabled_lora:
            return

        if not self._has_lora_changed(available_lora):
            return

        do_disable_lora = False

        try:
            filename = lora.path.split("/")[-1]
            for _lora in self.loaded_lora:
                if _lora.name == lora.name and _lora.path == lora.path:
                    return
            base_path:str = self.path_settings.base_path
            version:str = self.generator_settings.version
            lora_path = os.path.expanduser(
                os.path.join(
                    base_path,
                    "art/models",
                    version,
                    "lora"
                )
            )
            self._pipe.load_lora_weights(
                lora_path,
                weight_name=filename
            )
            self.loaded_lora.append(lora)
        except AttributeError as _e:
            self.logger.warning("This model does not support LORA")
            do_disable_lora = True
        except RuntimeError:
            self.logger.warning("LORA could not be loaded")
            do_disable_lora = True
        except ValueError:
            self.logger.warning("LORA could not be loaded")
            do_disable_lora = True

        if do_disable_lora:
            self._disabled_lora.append(lora.path)

    def _has_lora_changed(self, available_lora):
        """
        Check if there are any changes in the available LORA compared to the loaded LORA.
        Return True if there are changes, otherwise False.
        """
        loaded_lora_paths = {lora.path for lora in self.loaded_lora}

        for lora in available_lora:
            if lora.enabled and lora.path not in loaded_lora_paths:
                return True

        return False

    def _remove_lora_from_pipe(self):
        self.loaded_lora = []
        if self._pipe is not None:
            self._pipe.unload_lora_weights()

    def _load_embeddings(self):
        if not self._pipe:
            return
        self.logger.debug("Loading embeddings")
        available_embeddings = self.get_embeddings_by_version(self.generator_settings.version)
        for embedding in available_embeddings:
            path = os.path.expanduser(embedding.path)
            if embedding.active and embedding not in self._loaded_embeddings:
                if os.path.exists(path):
                    token = embedding.name
                    try:
                        self._pipe.load_textual_inversion(path, token=token, weight_name=path)
                        self._loaded_embeddings.append(embedding)
                    except Exception as e:
                        if "already in tokenizer" not in str(e):
                            self.logger.error(f"Failed to load embedding {token}: {e}")
            else:
                try:
                    self._pipe.unload_textual_inversion(embedding.name)
                    self._loaded_embeddings.remove(embedding)
                except ValueError as e:
                    if "No tokens to remove" not in str(e):
                        self.logger.error(f"Failed to unload embedding {embedding.name}: {e}")

    def _load_compel(self):
        if self.generator_settings.use_compel:
            self.logger.debug("Loading compel")
            try:
                self._load_textual_inversion_manager()
                self._load_compel_proc()
            except Exception as e:
                self.logger.error(f"Error creating compel proc: {e}")
                self._unload_compel()
        else:
            self._unload_compel()

    def _load_deep_cache(self):
        self._deep_cache_helper = DeepCacheSDHelper(pipe=self._pipe)
        self._deep_cache_helper.set_params(
            cache_interval=3,
            cache_branch_id=0
        )
        try:
            self._deep_cache_helper.enable()
        except AttributeError as e:
            self.logger.error(f"Failed to enable deep cache: {e}")

    def _load_textual_inversion_manager(self):
        self._textual_inversion_manager = DiffusersTextualInversionManager(self._pipe)

    def _load_compel_proc(self):
        parameters = dict(
            truncate_long_prompts=False,
            textual_inversion_manager=self._textual_inversion_manager
        )
        if self.is_sd_xl:
            tokenizer = [self._pipe.tokenizer, self._pipe.tokenizer_2]
            text_encoder = [self._pipe.text_encoder, self._pipe.text_encoder_2]
            parameters["returned_embeddings_type"] = ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED
            parameters["requires_pooled"] = [False, True]
        else:
            tokenizer = self._pipe.tokenizer
            text_encoder = self._pipe.text_encoder
        parameters.update(dict(
            tokenizer=tokenizer,
            text_encoder=text_encoder
        ))
        self._compel_proc = Compel(**parameters)

    def _make_memory_efficient(self):
        if not self._pipe:
            self.logger.error("Pipe is None, unable to apply memory settings")
            return

        memory_settings = [
            ("last_channels_applied", "use_last_channels", self._apply_last_channels),
            ("vae_slicing_applied", "use_enable_vae_slicing", self._apply_vae_slicing),
            ("attention_slicing_applied", "use_attention_slicing", self._apply_attention_slicing),
            ("tiled_vae_applied", "use_tiled_vae", self._apply_tiled_vae),
            ("accelerated_transformers_applied", "use_accelerated_transformers", self._apply_accelerated_transformers),
            ("cpu_offload_applied", "use_enable_sequential_cpu_offload", self._apply_cpu_offload),
            ("model_cpu_offload_applied", "enable_model_cpu_offload", self._apply_model_offload),
            ("tome_sd_applied", "tome_sd_ratio", self._apply_tome),
        ]

        for setting_name, attribute_name, apply_func in memory_settings:
            self._apply_memory_setting(setting_name, attribute_name, apply_func)

    def _finalize_load_stable_diffusion(self):
        safety_checker_ready = True
        tokenizer_ready = True
        if self.use_safety_checker:
            safety_checker_ready = (
                self._safety_checker is not None and
                self._feature_extractor is not None
            )
        if not self.is_sd_xl:
            tokenizer_ready = self._tokenizer is not None
        if (
            self._pipe is not None
            and tokenizer_ready
            and safety_checker_ready
        ):
            self._current_state = HandlerState.READY
            self.change_model_status(ModelType.SD, ModelStatus.LOADED)
        else:
            self.logger.error("Something went wrong with Stable Diffusion loading")
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            self.unload_stable_diffusion()

        if (
            self._controlnet is not None
            and self._controlnet_processor is not None
            and self._pipe
        ):
            self._pipe.__controlnet = self._controlnet
            self._pipe.processor = self._controlnet_processor

    def _apply_memory_setting(self, setting_name, attribute_name, apply_func):
        attr_val = getattr(self.memory_settings, attribute_name)
        if self._memory_settings_flags[setting_name] != attr_val:
            apply_func(attr_val)
            self._memory_settings_flags[setting_name] = attr_val

    def _apply_last_channels(self, attr_val):
        self.logger.debug(f"{'Enabling' if attr_val else 'Disabling'} torch.channels_last")
        self._pipe.unet.to(memory_format=torch.channels_last if attr_val else torch.contiguous_format)

    def _apply_vae_slicing(self, attr_val):
        try:
            if attr_val:
                self.logger.debug("Enabling vae slicing")
                self._pipe.enable_vae_slicing()
            else:
                self.logger.debug("Disabling vae slicing")
                self._pipe.disable_vae_slicing()
        except AttributeError as e:
            self.logger.error("Failed to apply vae slicing")
            self.logger.error(e)

    def _apply_attention_slicing(self, attr_val):
        try:
            if attr_val:
                self.logger.debug("Enabling attention slicing")
                self._pipe.enable_attention_slicing(1)
            else:
                self.logger.debug("Disabling attention slicing")
                self._pipe.disable_attention_slicing()
        except AttributeError as e:
            self.logger.warning(f"Failed to apply attention slicing: {e}")

    def _apply_tiled_vae(self, attr_val):
        try:
            if attr_val:
                self.logger.debug("Enabling tiled vae")
                self._pipe.vae.enable_tiling()
            else:
                self.logger.debug("Disabling tiled vae")
                self._pipe.vae.disable_tiling()
        except AttributeError:
            self.logger.warning("Tiled vae not supported for this model")

    def _apply_accelerated_transformers(self, attr_val):
        from diffusers.models.attention_processor import AttnProcessor, AttnProcessor2_0
        self.logger.debug(f"{'Enabling' if attr_val else 'Disabling'} accelerated transformers")
        self._pipe.unet.set_attn_processor(AttnProcessor2_0() if attr_val else AttnProcessor())

    def _apply_cpu_offload(self, attr_val):
        if attr_val and not self.memory_settings.enable_model_cpu_offload:
            self._pipe.to("cpu")
            try:
                self.logger.debug("Enabling sequential cpu offload")
                self._pipe.enable_sequential_cpu_offload()
            except NotImplementedError as e:
                self.logger.warning(f"Error applying sequential cpu offload: {e}")
                self._pipe.to(self._device)
        else:
            self.logger.debug("Sequential cpu offload disabled")

    def _apply_model_offload(self, attr_val):
        if attr_val and not self.memory_settings.use_enable_sequential_cpu_offload:
            self.logger.debug("Enabling model cpu offload")
            #self._move_stable_diffusion_to_cpu()
            self._pipe.enable_model_cpu_offload()
        else:
            self.logger.debug("Model cpu offload disabled")

    def _apply_tome(self, attr_val):
        tome_sd_ratio = self.memory_settings.tome_sd_ratio / 1000
        self.logger.debug(f"Applying ToMe SD weight merging with ratio {tome_sd_ratio}")
        if attr_val:
            self._remove_tome_sd()
            try:
                tomesd.apply_patch(self._pipe, ratio=tome_sd_ratio)
            except Exception as e:
                self.logger.error(f"Error applying ToMe SD weight merging: {e}")
        else:
            self._remove_tome_sd()

    def _remove_tome_sd(self):
        self.logger.debug("Removing ToMe SD weight merging")
        try:
            tomesd.remove_patch(self._pipe)
        except Exception as e:
            self.logger.error(f"Error removing ToMe SD weight merging: {e}")

    def _unload_safety_checker(self):
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        self._unload_safety_checker_model()
        self._unload_feature_extractor_model()
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED)

    def _unload_safety_checker_model(self):
        self.logger.debug("Unloading safety checker model")
        if self._pipe is not None and hasattr(self._pipe, "safety_checker"):
            del self._pipe.safety_checker
            self._pipe.safety_checker = None
        if self._safety_checker:
            try:
                self._safety_checker.to("cpu")
            except RuntimeError as e:
                self.logger.warning(f"Failed to load model from {self.model_path}: {e}")
        del self._safety_checker
        self._safety_checker = None

    def _unload_feature_extractor_model(self):
        self.logger.debug("Unloading feature extractor")
        if self._pipe is not None:
            del self._pipe.feature_extractor
            self._pipe.feature_extractor = None
        del self._feature_extractor
        self._feature_extractor = None

    def _unload_scheduler(self):
        self.logger.debug("Unloading scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        self.scheduler = None

    def _unload_controlnet(self):
        self.logger.debug("Unloading controlnet")
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)
        self._unload_controlnet_model()
        self._unload_controlnet_processor()
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.UNLOADED)

    def _unload_controlnet_model(self):
        self.logger.debug("Clearing controlnet")
        if self._pipe and hasattr(self._pipe, "controlnet"):
            try:
                del self._pipe.__controlnet
            except AttributeError:
                pass
            self._pipe.__controlnet = None
        del self._controlnet
        self._controlnet = None

    def _unload_controlnet_processor(self):
        self.logger.debug("Clearing controlnet processor")
        if self._pipe and hasattr(self._pipe, "processor"):
            del self._pipe.processor
            self._pipe.processor = None
        del self._controlnet_processor
        self._controlnet_processor = None

    def _unload_lora(self):
        self.logger.debug("Unloading lora")
        self._remove_lora_from_pipe()
        if self._pipe is not None:
            self._pipe.unload_lora_weights()
        self._loaded_lora = []
        self._disabled_lora = []

    def _unload_emebeddings(self):
        self.logger.debug("Unloading embeddings")
        self._loaded_embeddings = []

    def _unload_compel(self):
        if (
            self._textual_inversion_manager is not None
            or self._compel_proc is not None
        ):
            self.logger.debug("Unloading compel")
            self._unload_textual_inversion_manager()
            self._unload_compel_proc()
            self._unload_prompt_embeds()
            clear_memory()

    def _unload_textual_inversion_manager(self):
        self.logger.debug("Unloading textual inversion manager")
        try:
            del self._textual_inversion_manager.pipe
        except TypeError:
            pass
        del self._textual_inversion_manager
        self._textual_inversion_manager = None

    def _unload_compel_proc(self):
        self.logger.debug("Unloading compel proc")
        del self._compel_proc
        self._compel_proc = None

    def _unload_latents(self):
        self.logger.debug("Unloading latents")
        del self._latents
        self._latents = None

    def _unload_prompt_embeds(self):
        self.logger.debug("Unloading prompt embeds")
        del self._prompt_embeds
        del self._negative_prompt_embeds
        del self._pooled_prompt_embeds
        del self._negative_pooled_prompt_embeds
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
        self._pooled_prompt_embeds = None
        self._negative_pooled_prompt_embeds = None

    def _unload_deep_cache(self):
        if self._deep_cache_helper is not None:
            try:
                self._deep_cache_helper.disable()
            except AttributeError:
                pass
        del self._deep_cache_helper
        self._deep_cache_helper = None

    def _unload_pipe(self):
        self.logger.debug("Unloading pipe")
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        del self._pipe
        self._pipe = None
        self.change_model_status(ModelType.SD, ModelStatus.UNLOADED)

    def _unload_tokenizer(self):
        self.logger.debug("Unloading tokenizer")
        del self._tokenizer
        self._tokenizer = None

    def _unload_generator(self):
        self.logger.debug("Unloading generator")
        del self._generator
        self._generator = None

    def _load_prompt_embeds(self):
        self.logger.debug("Loading prompt embeds")
        if not self.generator_settings.use_compel:
            return
        prompt = self.generator_settings.prompt
        negative_prompt = self.generator_settings.negative_prompt
        prompt_2 = self.generator_settings.second_prompt
        negative_prompt_2 = self.generator_settings.second_negative_prompt


        if (
            self._current_prompt != prompt
            or self._current_negative_prompt != negative_prompt
            or self._current_prompt_2 != prompt_2
            or self._current_negative_prompt_2 != negative_prompt_2
        ):
            self._unload_latents()
            self._current_prompt = prompt
            self._current_negative_prompt = negative_prompt
            self._current_prompt_2 = prompt_2
            self._current_negative_prompt_2 = negative_prompt_2
            self._unload_prompt_embeds()

        pooled_prompt_embeds = None
        negative_pooled_prompt_embeds = None

        if self.is_sd_xl:
            prompt_embeds, pooled_prompt_embeds = self._compel_proc.build_conditioning_tensor(f'("{prompt}", "{prompt_2}").and()')
            negative_prompt_embeds, negative_pooled_prompt_embeds = self._compel_proc.build_conditioning_tensor(f'("{negative_prompt}", "{negative_prompt_2}").and()')
        else:
            prompt_embeds = self._compel_proc.build_conditioning_tensor(prompt)
            negative_prompt_embeds = self._compel_proc.build_conditioning_tensor(negative_prompt)
        [
            prompt_embeds,
            negative_prompt_embeds
        ] = self._compel_proc.pad_conditioning_tensors_to_same_length([
            prompt_embeds,
            negative_prompt_embeds
        ])

        self._prompt_embeds = prompt_embeds
        self._negative_prompt_embeds = negative_prompt_embeds
        self._pooled_prompt_embeds = pooled_prompt_embeds
        self._negative_pooled_prompt_embeds = negative_pooled_prompt_embeds

        self._prompt_embeds.half().to(self._device)
        self._negative_prompt_embeds.half().to(self._device)
        self._pooled_prompt_embeds.half().to(self._device)
        self._negative_pooled_prompt_embeds.half().to(self._device)

    def _clear_memory_efficient_settings(self):
        self.logger.debug("Clearing memory efficient settings")
        for key in self._memory_settings_flags:
            if key.endswith("_applied"):
                self._memory_settings_flags[key] = None

    def _prepare_data(self) -> dict:
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        self.logger.debug("Preparing data")
        active_rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        active_rect.translate(
            -self.canvas_settings.pos_x,
            -self.canvas_settings.pos_y
        )
        args = dict(
            outpaint_box_rect=active_rect,
            width=int(self.application_settings.working_width),
            height=int(self.application_settings.working_height),
            clip_skip=int(self.generator_settings.clip_skip),
            num_inference_steps=int(self.generator_settings.steps),
            callback=self._callback,
            callback_steps=1,
            generator=self._generator,
            callback_on_step_end=self.__interrupt_callback,
        )

        if self.generator_settings.use_compel:
            args.update(dict(
                prompt_embeds=self._prompt_embeds,
                negative_prompt_embeds=self._negative_prompt_embeds,
                pooled_prompt_embeds=self._pooled_prompt_embeds,
                negative_pooled_prompt_embeds=self._negative_pooled_prompt_embeds
            ))
        else:
            args.update(dict(
                prompt=self.generator_settings.prompt,
                negative_prompt=self.generator_settings.negative_prompt
            ))

        width = int(self.application_settings.working_width)
        height = int(self.application_settings.working_height)
        image = None
        mask = None

        if self.is_txt2img or self.is_outpaint or self.is_img2img:
            args.update(dict(
                width=width,
                height=height,
            ))

        if self.is_img2img:
            if args["num_inference_steps"] < MIN_NUM_INFERENCE_STEPS_IMG2IMG:
                args["num_inference_steps"] = MIN_NUM_INFERENCE_STEPS_IMG2IMG

        if not self.controlnet_settings.enabled:
            if self.is_txt2img:
                args.update(dict(
                    guidance_scale=self.generator_settings.scale / 100.0
                ))
            elif self.is_img2img:
                args.update(dict(
                    strength=self.generator_settings.strength / 100.0,
                    guidance_scale=self.generator_settings.scale / 100.0
                ))

        if self.is_outpaint:
            if image is None:
                image = self.outpaint_image
            if mask is None:
                mask = self.outpaint_mask

        if image is not None:
            args.update(dict(
                image=image
            ))

        if mask is not None:
            args.update(dict(
                mask=mask
            ))

        if self.controlnet_enabled:
            args.update(dict(
                guess_mode=None,
                control_guidance_start=0.0,
                control_guidance_end=1.0,
                strength=self.controlnet_settings.strength / 100.0,
                guidance_scale=self.generator_settings.scale / 100.0,
                controlnet_conditioning_scale=self.controlnet_settings.conditioning_scale / 100.0,
                controlnet=[
                    self.controlnet_image_settings.controlnet
                ]
            ))
            if self.is_txt2img:
                args.update(dict(
                    image=self.controlnet_image
                ))
            else:
                args.update(dict(
                    control_image=self.controlnet_image
                ))
        return args

    def _set_seed(self):
        seed = self.generator_settings.seed
        self._generator.manual_seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    def _callback(self, step: int, _time_step, latents):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": step,
            "total": self.generator_settings.steps
        })
        if self._latents is None:
            self._latents = latents
        QApplication.processEvents()
        return {}

    def __interrupt_callback(self, _pipe, _i, _t, callback_kwargs):
        if self.do_interrupt_image_generation:
            self.do_interrupt_image_generation = False
            raise InterruptedException()
        return callback_kwargs
