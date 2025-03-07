import datetime
import os
from typing import Any, List, Dict, Optional

import PIL
import diffusers
import numpy as np
import tomesd
import torch
from sqlalchemy.orm import joinedload
from DeepCache import DeepCacheSDHelper
from PIL import (
    ImageDraw,
    ImageFont
)
from PIL.Image import Image
from PySide6.QtCore import QRect, Slot
from PySide6.QtWidgets import QApplication
from compel import (
    Compel, 
    DiffusersTextualInversionManager, 
    ReturnedEmbeddingsType
)
from controlnet_aux.processor import MODELS as controlnet_aux_models
from diffusers import (
    StableDiffusionPipeline, 
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLInpaintPipeline,
    StableDiffusionXLControlNetPipeline,
    StableDiffusionXLControlNetImg2ImgPipeline,
    StableDiffusionXLControlNetInpaintPipeline,
    ControlNetModel,
    AutoencoderTiny,
    AutoencoderKL
)
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from transformers import (
    CLIPFeatureExtractor, 
    CLIPTextModel, 
    CLIPTextModelWithProjection
)
from transformers import BitsAndBytesConfig as TransformersBitsAndBytesConfig
from airunner.handlers.base_handler import BaseHandler
from airunner.data.models import (
    Schedulers, 
    Lora, 
    Embedding, 
    ControlnetModel, 
    AIModels
)
from airunner.enums import (
    SDMode, 
    StableDiffusionVersion, 
    GeneratorSection, 
    ModelStatus, 
    ModelType, 
    SignalCode, 
    HandlerState,
    EngineResponseCode, 
    ModelAction
)
from airunner.exceptions import PipeNotLoadedException, InterruptedException
from airunner.handlers.stablediffusion.prompt_weight_bridge import \
    PromptWeightBridge
from airunner.settings import MIN_NUM_INFERENCE_STEPS_IMG2IMG
from airunner.utils.clear_memory import clear_memory
from airunner.utils.image.convert_binary_to_image import convert_binary_to_image
from airunner.utils.image.convert_image_to_binary import convert_image_to_binary
from airunner.utils.image.export_image import export_images
from airunner.utils.get_torch_device import get_torch_device
from airunner.data.models import GeneratorSettings

SKIP_RELOAD_CONSTS = (
    SDMode.FAST_GENERATE,
    SDMode.DRAWING,
)


class ArtHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_model_path = ""
        self._controlnet_model = None
        self._controlnet: Optional[ControlNetModel] = None
        self._controlnet_processor: Any = None
        self.model_type = ModelType.SD
        self._safety_checker: Optional[StableDiffusionSafetyChecker] = None
        self._feature_extractor: Optional[CLIPFeatureExtractor] = None
        self._memory_settings_flags: dict = {
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
        self._prompt_embeds: Optional[torch.Tensor] = None
        self._negative_prompt_embeds: Optional[torch.Tensor] = None
        self._pooled_prompt_embeds: Optional[torch.Tensor] = None
        self._negative_pooled_prompt_embeds: Optional[torch.Tensor] = None
        self._pipe = None
        self._current_prompt: str = ""
        self._current_negative_prompt: str = ""
        self._current_prompt_2: str = ""
        self._current_negative_prompt_2: str = ""
        self._generator: Optional[torch.Generator] = None
        self._latents = None
        self._textual_inversion_manager: Optional[DiffusersTextualInversionManager] = None
        self._compel_proc: Optional[Compel] = None
        self._loaded_lora: Dict = {}
        self._disabled_lora: List = []
        self._loaded_embeddings: List = []
        self._current_state: HandlerState = HandlerState.UNINITIALIZED
        self._deep_cache_helper: Optional[DeepCacheSDHelper] = None
        self.do_interrupt_image_generation: bool = False

        # The following properties must be set to None before generating an
        # image each time generate is called. These are cached properties that 
        # come from the database. 
        # Caching them here allows us to avoid querying the database each time.
        self._outpaint_image = None
        self._img2img_image = None
        self._controlnet_settings = None
        self._controlnet_image_settings = None
        self._generator_settings = None
        self._application_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None
        self._current_memory_settings = None
    
    def on_application_settings_changed(self):
        if self._pipe:
            pipeline_class = self._pipe.__class__
            print(pipeline_class)
            if (
                pipeline_class in self.img2img_pipelines and 
                not self.image_to_image_settings.enabled
            ) or (
                pipeline_class in self.txt2img_pipelines and 
                self.image_to_image_settings.enabled
            ):
                self._swap_pipeline()

        memory_settings = self.memory_settings.to_dict()
        if self._pipe and self._current_memory_settings != memory_settings:
            self._clear_memory_efficient_settings()
            self._make_memory_efficient()

    def _clear_cached_properties(self):
        self._outpaint_image = None
        self._img2img_image = None
        self._controlnet_settings = None
        self._controlnet_image_settings = None
        self._generator_settings = None
        self._application_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None

    @property
    def img2img_pipelines(self):
        return (
            StableDiffusionXLImg2ImgPipeline,
            StableDiffusionXLControlNetImg2ImgPipeline,
            StableDiffusionImg2ImgPipeline,
            StableDiffusionControlNetImg2ImgPipeline
        )

    @property
    def txt2img_pipelines(self):
        return (
            StableDiffusionXLPipeline,
            StableDiffusionXLControlNetPipeline,
            StableDiffusionPipeline,
            StableDiffusionControlNetPipeline
        )

    @property
    def outpaint_pipelines(self):
        return (
            StableDiffusionXLInpaintPipeline,
            StableDiffusionInpaintPipeline,
            StableDiffusionControlNetInpaintPipeline,
            StableDiffusionXLControlNetInpaintPipeline
        )

    @property
    def use_compel(self) -> bool:
        return self.generator_settings_cached.use_compel

    @property
    def controlnet_path(self):
        version: str = self.controlnet_model.version
        path: str = self.controlnet_model.path
        return os.path.expanduser(os.path.join(
            self.path_settings_cached.base_path,
            "art",
            "models",
            version,
            "controlnet",
            path
        ))

    @property
    def controlnet_processor_path(self):
        return os.path.expanduser(os.path.join(
            self.path_settings_cached.base_path,
            "art",
            "models",
            "controlnet_processors"
        ))

    @property
    def model_status(self):
        return self._model_status

    @Slot(str)
    def _handle_worker_error(self, error_message):
        self.logger.error("Worker error: %s", error_message)

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
    def version(self) -> str:
        version = self.generator_settings_cached.version
        if version == "SDXL Turbo":
            version = "SDXL 1.0"
        return version

    @property
    def is_sd_xl(self) -> bool:
        return self.generator_settings_cached.version == StableDiffusionVersion.SDXL1_0.value

    @property
    def is_sd_xl_turbo(self) -> bool:
        return self.generator_settings_cached.version == StableDiffusionVersion.SDXL_TURBO.value

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return self.is_sd_xl or self.is_sd_xl_turbo

    @property
    def img2img_image_cached(self) -> Image:
        if self._img2img_image is None:
            self._img2img_image = self.img2img_image
        return self._img2img_image

    @property
    def application_settings_cached(self):
        if self._application_settings is None:
            self._application_settings = self.application_settings
        return self._application_settings

    @property
    def drawing_pad_settings_cached(self):
        if self._drawing_pad_settings is None:
            self._drawing_pad_settings = self.drawing_pad_settings
        return self._drawing_pad_settings

    @property
    def outpaint_settings_cached(self):
        if self._outpaint_settings is None:
            self._outpaint_settings = self.outpaint_settings
        return self._outpaint_settings

    @property
    def path_settings_cached(self):
        if self._path_settings is None:
            self._path_settings = self.path_settings
        return self._path_settings

    @property
    def current_model_path(self) -> str:
        return self._current_model_path
    
    @current_model_path.setter
    def current_model_path(self, value: str):
        self._current_model_path = value

    @property
    def _current_model(self) -> AIModels:
        generator_settings = GeneratorSettings.objects.options(
            joinedload(GeneratorSettings.aimodel)
        ).first()
        return generator_settings.aimodel

    @property
    def generator_settings_cached(self):
        return self.generator_settings

    @property
    def generator_settings_scale(self) -> int:
        return self.generator_settings_cached.scale

    @property
    def controlnet_settings_cached(self):
        if self._controlnet_settings is None:
            self._controlnet_settings = self.controlnet_settings
        return self._controlnet_settings

    @property
    def controlnet_image(self) -> Image:
        img = self.controlnet_settings_cached.image
        if img is not None:
            img = convert_binary_to_image(img)
        return img

    @property
    def controlnet_model(self) -> Optional[ControlnetModel]:
        if (
            self._controlnet_model is None or
            self._controlnet_model.version != self.version or
            self._controlnet_model.display_name != self.controlnet_settings_cached.controlnet
        ):
            
            self._controlnet_model = ControlnetModel.objects.filter_by(
                display_name=self.controlnet_settings_cached.controlnet,
                version=self.version
            ).first()
            
        return self._controlnet_model

    @property
    def controlnet_enabled(self) -> bool:
        return self.controlnet_settings_cached.enabled and self.application_settings.controlnet_enabled

    @property
    def controlnet_strength(self) -> int:
        return self.controlnet_settings_cached.strength

    @property
    def controlnet_conditioning_scale(self) -> int:
        return self.controlnet_settings_cached.conditioning_scale

    @property
    def controlnet_is_loading(self) -> bool:
        return self.model_status[ModelType.CONTROLNET] is ModelStatus.LOADING

    @property
    def controlnet_is_unloaded(self) -> bool:
        return self.model_status[ModelType.CONTROLNET] is ModelStatus.UNLOADED

    @property
    def section(self) -> GeneratorSection:
        section = GeneratorSection.TXT2IMG
        if (
            self.img2img_image_cached is not None and
            self.image_to_image_settings.enabled
        ):
            section = GeneratorSection.IMG2IMG
        if (
            self.drawing_pad_settings.mask is not None and
            self.drawing_pad_settings.image is not None and
            self.generator_settings_cached.pipeline_action == "inpaint" and
            self.outpaint_settings_cached.enabled
        ):
            section = GeneratorSection.OUTPAINT
        return section

    @property
    def model_path(self) -> str:
        if not self._current_model:
            return ""
        return os.path.expanduser(
            self._current_model.path
        )

    @property
    def lora_base_path(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.path_settings_cached.base_path,
                "art/models",
                self.version,
                "lora"
            )
        )

    @property
    def lora_scale(self) -> float:
        return self.generator_settings_cached.lora_scale / 100.0

    @property
    def data_type(self) -> torch.dtype:
        return torch.float16

    @property
    def use_safety_checker(self) -> bool:
        return self.application_settings_cached.nsfw_filter

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
    def is_txt2img(self) -> bool:
        return self.section is GeneratorSection.TXT2IMG

    @property
    def is_img2img(self) -> bool:
        return self.section is GeneratorSection.IMG2IMG

    @property
    def is_outpaint(self) -> bool:
        return self.section is GeneratorSection.OUTPAINT

    @property
    def safety_checker_is_loading(self):
        return self.model_status[ModelType.SAFETY_CHECKER] is ModelStatus.LOADING

    @property
    def sd_is_loading(self):
        return self.model_status[ModelType.SD] is ModelStatus.LOADING

    @property
    def sd_is_loaded(self):
        return self.model_status[ModelType.SD] is ModelStatus.LOADED

    @property
    def sd_is_unloaded(self):
        return self.model_status[ModelType.SD] is ModelStatus.UNLOADED

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

        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"

        if self.is_sd_xl_or_turbo:
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

    @property
    def mask_blur(self) -> int:
        return self.outpaint_settings_cached.mask_blur

    @property
    def prompt(self):
        prompt = self.generator_settings_cached.prompt
        return PromptWeightBridge.convert(prompt)

    @property
    def second_prompt(self):
        prompt = self.generator_settings_cached.second_prompt
        return PromptWeightBridge.convert(prompt)

    @property
    def negative_prompt(self):
        prompt = self.generator_settings_cached.negative_prompt
        return PromptWeightBridge.convert(prompt)

    @property
    def second_negative_prompt(self):
        prompt = self.generator_settings_cached.second_negative_prompt
        return PromptWeightBridge.convert(prompt)

    def load_safety_checker(self):
        """
        Public method to load the safety checker model.
        """
        if self.safety_checker_is_loading:
            return
        self._load_safety_checker()

    def unload_safety_checker(self):
        """
        Public method to unload the safety checker model.
        """
        if self.safety_checker_is_loading:
            return
        self._unload_safety_checker()

    def load_controlnet(self):
        """
        Public method to load the controlnet model.
        """
        # clear the controlnet settings so that we get the latest selected controlnet model
        if not self.controlnet_enabled or self.controlnet_is_loading:
            return
        self._controlnet_model = None
        self._controlnet_settings = None
        self._load_controlnet()

    def unload_controlnet(self):
        """
        Public method to unload the controlnet model.
        """
        if self.controlnet_is_loading:
            return
        self._unload_controlnet()

    def load_scheduler(self, scheduler_name):
        """
        Public method to load the scheduler.
        """
        self._load_scheduler(scheduler_name)

    def reload(self):
        self.logger.debug("Reloading stable diffusion")
        self._clear_cached_properties()
        self.unload()
        self.load()

    def load(self):
        if self.sd_is_loading or self.sd_is_loaded:
            return
        if self.generator_settings_cached.model is None:
            self.logger.error("No model selected")
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            return
        self.unload()
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._load_safety_checker()
        self._load_generator()
        self._load_controlnet()
        self._load_pipe()
        self._load_scheduler()
        self._load_lora()
        self._load_embeddings()
        self._load_compel()
        self._load_deep_cache()
        self._make_memory_efficient()
        self._finalize_load_stable_diffusion()

    def unload(self):
        if self.sd_is_loading or self.sd_is_unloaded:
            return
        elif self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING
        ):
            self.interrupt_image_generation()
            self.requested_action = ModelAction.CLEAR
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._unload_safety_checker()
        self._unload_scheduler()
        self._unload_controlnet()
        self._unload_loras()
        self._unload_emebeddings()
        self._unload_compel()
        self._unload_generator()
        self._unload_deep_cache()
        self._unload_pipe()
        self._clear_memory_efficient_settings()
        clear_memory()
        self.change_model_status(ModelType.SD, ModelStatus.UNLOADED)

    def handle_generate_signal(self, message: Optional[Dict] = None):
        self.load()
        self._clear_cached_properties()
        self._swap_pipeline()
        if self._current_state not in (
            HandlerState.GENERATING,
            HandlerState.PREPARING_TO_GENERATE
        ):
            self._current_state = HandlerState.PREPARING_TO_GENERATE
            response = None
            code = EngineResponseCode.NONE
            try:
                response = self._generate()
                code = EngineResponseCode.IMAGE_GENERATED
            except PipeNotLoadedException as e:
                self.logger.error(e)
            except Exception as e:
                if "CUDA out of memory" in str(e):
                    code = EngineResponseCode.INSUFFICIENT_GPU_MEMORY
                self.logger.error("Error generating image: %s", e)
            if message is not None:
                callback = message.get("callback", None)
                if callback:
                    callback(message)
            self.emit_signal(SignalCode.ENGINE_RESPONSE_WORKER_RESPONSE_SIGNAL, {
                'code': code,
                'message': response
            })
            self._current_state = HandlerState.READY
            clear_memory()
        self.handle_requested_action()

    def reload_lora(self):
        if self.model_status[ModelType.SD] is not ModelStatus.LOADED or self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING
        ):
            return
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._unload_loras()
        self._load_lora()
        self.emit_signal(SignalCode.LORA_UPDATED_SIGNAL)
        self.change_model_status(ModelType.SD, ModelStatus.LOADED)

    def reload_embeddings(self):
        if self.model_status[ModelType.SD] is not ModelStatus.LOADED or self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING
        ):
            return
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        self._load_embeddings()
        self.emit_signal(SignalCode.EMBEDDING_UPDATED_SIGNAL)
        self.change_model_status(ModelType.SD, ModelStatus.LOADED)

    def load_embeddings(self):
        self._load_embeddings()

    def interrupt_image_generation(self):
        if self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING
        ):
            self.do_interrupt_image_generation = True

    def _swap_pipeline(self):
        pipeline_class_ = self._pipeline_class
        if self._pipe.__class__ is pipeline_class_:  # noqa
            return
       
        self.logger.debug("Swapping pipeline from %s to %s", 
                          self._pipe.__class__, 
                          pipeline_class_)
        try:
            kwargs = {}
            if pipeline_class_ in (
                StableDiffusionControlNetPipeline,
                StableDiffusionControlNetImg2ImgPipeline,
                StableDiffusionControlNetInpaintPipeline,
                StableDiffusionXLControlNetPipeline,
                StableDiffusionXLControlNetImg2ImgPipeline,
                StableDiffusionXLControlNetInpaintPipeline
            ):
                kwargs.update(controlnet=self._controlnet)
            kwargs = self._prepare_tiny_autoencoder(kwargs)
            self._pipe = pipeline_class_.from_pipe(self._pipe, **kwargs)
        except Exception as e:
            self.logger.error(f"Error swapping pipeline: {e}")
        finally:
            self._send_pipeline_loaded_signal()
            self._move_pipe_to_device()

    def _generate(self):
        self.logger.debug("Generating image")
        # if self._current_model.path != model.path:
        #     self.logger.debug("Model has changed from %s to %s",
        #                       self._current_model.path,
        #                       model.path)
        #     if self._pipe is not None:
        #         self.reload()
        if self._pipe is None:
            raise PipeNotLoadedException()
        self._load_prompt_embeds()
        clear_memory()
        active_rect = QRect(
            self.active_grid_settings.pos_x,
            self.active_grid_settings.pos_y,
            self.application_settings_cached.working_width,
            self.application_settings_cached.working_height,
        )
        active_rect.translate(
            -self.drawing_pad_settings.x_pos,
            -self.drawing_pad_settings.y_pos
        )
        args = self._prepare_data(active_rect)
        self._current_state = HandlerState.GENERATING

        with torch.no_grad():
            results = self._pipe(**args)
        images = results.get("images", [])
        images, nsfw_content_detected = self._check_and_mark_nsfw_images(images)
        if images is not None:
            self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
                "step": self.generator_settings_cached.steps,
                "total": self.generator_settings_cached.steps,
            })

            if images is None:
                return

            if self.application_settings_cached.auto_export_images:
                self._export_images(images, args)

            return {
                "images": images,
                "data": args,
                "nsfw_content_detected": any(nsfw_content_detected),
                "active_rect": active_rect,
                "is_outpaint": self.is_outpaint
            }
        else:
            return {
                "images": [],
                "data": args,
                "nsfw_content_detected": False,
                "active_rect": active_rect,
                "is_outpaint": self.is_outpaint
            }
    
    def _initialize_metadata(self, images: List[Any], data: Dict) -> Optional[dict]:
        metadata = None
        if self.metadata_settings.export_metadata:
            metadata_dict = {}
            if self.metadata_settings.image_export_metadata_prompt:
                metadata_dict["prompt"] = self._current_prompt
                metadata_dict["prompt_2"] = self._current_prompt_2
            if self.metadata_settings.image_export_metadata_negative_prompt:
                metadata_dict["negative_prompt"] = self._current_negative_prompt
                metadata_dict["negative_prompt_2"] = self._current_negative_prompt_2
            if self.metadata_settings.image_export_metadata_scale:
                metadata_dict["scale"] = data.get("guidance_scale", 0)
            if self.metadata_settings.image_export_metadata_seed:
                metadata_dict["seed"] = self.generator_settings_cached.seed
            if self.metadata_settings.image_export_metadata_steps:
                metadata_dict["steps"] = self.generator_settings_cached.steps
            if self.metadata_settings.image_export_metadata_ddim_eta:
                metadata_dict["ddim_eta"] = self.generator_settings_cached.ddim_eta
            if self.metadata_settings.image_export_metadata_iterations:
                metadata_dict["num_inference_steps"] = data["num_inference_steps"]
            if self.metadata_settings.image_export_metadata_samples:
                metadata_dict["n_samples"] = self.generator_settings_cached.n_samples
            if self.metadata_settings.image_export_metadata_model:
                metadata_dict["model"] = self._current_model
            if self.metadata_settings.image_export_metadata_version:
                metadata_dict["version"] = self.generator_settings_cached.version
            if self.metadata_settings.image_export_metadata_scheduler:
                metadata_dict["scheduler"] = self.generator_settings_cached.scheduler
            if self.metadata_settings.image_export_metadata_strength:
                metadata_dict["strength"] = data.get("strength", 0)
            if self.metadata_settings.image_export_metadata_lora:
                metadata_dict["lora"] = self._loaded_lora
            if self.metadata_settings.image_export_metadata_embeddings:
                metadata_dict["embeddings"] = self._loaded_embeddings
            if self.metadata_settings.image_export_metadata_timestamp:
                metadata_dict["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if self.metadata_settings.image_export_metadata_controlnet and self.controlnet_enabled:
                metadata_dict.update({
                    "guess_mode": data["guess_mode"],
                    "control_guidance_start": data["control_guidance_start"],
                    "control_guidance_end": data["control_guidance_end"],
                    "controlnet_strength": data["strength"],
                    "controlnet_guidance_scale": data["guidance_scale"],
                    "controlnet_conditioning_scale": data["controlnet_conditioning_scale"],
                    "controlnet": self.controlnet_settings_cached.controlnet,
                })
            if self.is_txt2img:
                metadata_dict["action"] = "txt2img"
            elif self.is_img2img:
                metadata_dict["action"] = "img2img"
            elif self.is_outpaint:
                metadata_dict.update({
                    "action": "inpaint",
                    "mask_blur": self.mask_blur,
                })
            metadata_dict["tome_sd"] = self._memory_settings_flags["use_tome_sd"]
            metadata_dict["tome_ratio"] = self._memory_settings_flags["tome_ratio"]
            metadata = [metadata_dict for _ in range(len(images))]
        return metadata

    def _export_images(self, images: List[Any], data: Dict):
        extension = self.application_settings_cached.image_export_type
        filename = "image"
        file_path = os.path.expanduser(
            os.path.join(
                self.path_settings_cached.image_path,
                f"{filename}.{extension}"
            )
        )
        metadata = self._initialize_metadata(images, data)
        export_images(images, file_path, metadata)

    def _check_and_mark_nsfw_images(self, images) -> tuple:
        if not self._feature_extractor or not self._safety_checker:
            return images, [False] * len(images)

        self._safety_checker.to(self._device)

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

        self._safety_checker.to("cpu")

        return images, has_nsfw_concepts

    def _load_safety_checker(self):
        if not self.application_settings_cached.nsfw_filter or self.safety_checker_is_loading:
            return
        self._load_safety_checker_model()
        self._load_feature_extractor()

    def _load_safety_checker_model(self):
        self.logger.debug("Loading safety checker")
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        safety_checker_path = os.path.expanduser(
            os.path.join(
                self.path_settings_cached.base_path,
                "art",
                "models",
                "SD 1.5",
                "txt2img",
                "safety_checker"
            )
        )
        try:
            self._safety_checker = StableDiffusionSafetyChecker.from_pretrained(
                safety_checker_path,
                torch_dtype=self.data_type,
                device_map="cpu",
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
                self.path_settings_cached.base_path,
                "art",
                "models",
                "SD 1.5",
                "txt2img",
                "feature_extractor"
            )
        )
        try:
            self._feature_extractor = CLIPFeatureExtractor.from_pretrained(
                feature_extractor_path,
                torch_dtype=self.data_type,
                local_files_only=True,
                use_safetensors=True
            )
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED)
        except Exception as e:
            self.logger.error(f"Unable to load feature extractor {e}")
            self.change_model_status(ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED)

    def _load_generator(self):
        self.logger.debug("Loading generator")
        if self._generator is None:
            seed = int(self.generator_settings_cached.seed)
            self._generator = torch.Generator(device=self._device)
            self._generator.manual_seed(seed)

    def _load_controlnet(self):
        if not self.controlnet_enabled or self.controlnet_is_loading:
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
        if not self.controlnet_model:
            raise ValueError(f"Unable to find controlnet model {self.controlnet_settings_cached.controlnet}")
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)
        self._controlnet = ControlNetModel.from_pretrained(
            self.controlnet_path,
            torch_dtype=self.data_type,
            device=self._device,
            local_files_only=True,
            use_safetensors=True,
            use_fp16=True
        )

    def _load_controlnet_processor(self):
        if self._controlnet_processor is not None:
            return
        self.logger.debug(f"Loading controlnet processor {self.controlnet_model.name}")
        controlnet_data = controlnet_aux_models[self.controlnet_model.name]
        controlnet_class_: Any = controlnet_data["class"]
        checkpoint: bool = controlnet_data["checkpoint"]
        if checkpoint:
            self._controlnet_processor = controlnet_class_.from_pretrained(
                self.controlnet_processor_path,
                local_files_only=True
            )
        else:
            self._controlnet_processor = controlnet_class_()

    def _load_scheduler(self, scheduler=None):
        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)
        scheduler_name = scheduler or self.generator_settings_cached.scheduler
        base_path: str = self.path_settings_cached.base_path
        scheduler_version: str = self.version
        scheduler_path = os.path.expanduser(
            os.path.join(
                base_path,
                "art/models",
                scheduler_version,
                "txt2img",
                "scheduler",
                "scheduler_config.json"
            )
        )
        
        scheduler = Schedulers.objects.filter_by(
            display_name=scheduler_name
        ).first()
        if not scheduler:
            self.logger.error(f"Failed to find scheduler {scheduler_name}")
            return None
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

    def _prepare_quantization_settings(self, data: dict) -> dict:
        """
        Quantize the model if possible.
        """
        if self.is_sd_xl_turbo:
            return data
        
        path = os.path.expanduser(os.path.join(
            self.path_settings_cached.base_path,
            "art",
            "models",
            StableDiffusionVersion.SDXL1_0.value if self.is_sd_xl_or_turbo else StableDiffusionVersion.SD1_5.value,
            "inpaint" if self.is_outpaint else "txt2img"
        ))

        existing_file_path = os.path.join(path, "text_encoder", "model.fp16.safetensors")
        expected_file_path = os.path.join(path, "text_encoder", "model.safetensors")
        if not os.path.exists(expected_file_path) and os.path.exists(existing_file_path):
            os.rename(existing_file_path, expected_file_path)

        quant_config = TransformersBitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True
        )
        data["text_encoder"] = CLIPTextModel.from_pretrained(
            path,
            subfolder="text_encoder",
            quantization_config=quant_config,
            torch_dtype=torch.float16,
            use_safetensors=True
        )
        
        if self.is_sd_xl_or_turbo:
            """
            text encoder 2 is downloaded with the name model.fp16.safetensors
            which worked when we were not quantizing the model but now when we 
            are loading from pretrained it is looking for model.safetensors
            """
            existing_file_path = os.path.join(path, "text_encoder_2", "model.fp16.safetensors")
            expected_file_path = os.path.join(path, "text_encoder_2", "model.safetensors")
            if not os.path.exists(expected_file_path) and os.path.exists(existing_file_path):
                os.rename(existing_file_path, expected_file_path)
            data["text_encoder_2"] = CLIPTextModelWithProjection.from_pretrained(
                path,
                subfolder="text_encoder_2",
                quantization_config=quant_config,
                torch_dtype=torch.float16,
                use_safetensors=True
            )
        return data

    def _prepare_tiny_autoencoder(self, data: Dict) -> Optional[Dict]:
        if not self.is_outpaint:
            if self.is_sd_xl_or_turbo:
                version = StableDiffusionVersion.SDXL1_0.value
                repo_path = "madebyollin/sdxl-vae-fp16-fix"
                autoencoder_class_ = AutoencoderKL
            else:
                version = StableDiffusionVersion.SD1_5.value
                repo_path = "madebyollin/taesd"
                autoencoder_class_ = AutoencoderTiny
            path = os.path.expanduser(os.path.join(
                self.path_settings_cached.base_path,
                "art",
                "models",
                version,
                "tiny_autoencoder",
                repo_path
            ))
            if not os.path.exists(path):
                self.logger.error("Tiny autoencoder path does not exist")
                self.emit_signal(SignalCode.MISSING_REQUIRED_MODELS)
                self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.SD,
                    "status": ModelStatus.FAILED
                })
                return None
            data["vae"] = autoencoder_class_.from_pretrained(
                path,
                torch_dtype=torch.float16,
                use_safetensors=True
            )
        return data

    def _load_pipe(self):
        self.logger.debug("Loading pipe")
        data = {
            "torch_dtype": self.data_type,
            "use_safetensors": True,
            "local_files_only": True,
            "device": self._device,
        }

        if self.controlnet_enabled:
            data["controlnet"] = self._controlnet

        pipeline_class_ = self._pipeline_class

        data = self._prepare_quantization_settings(data)
        data = self._prepare_tiny_autoencoder(data)
        if data is None:
            return
        
        if self.is_sd_xl_turbo:
            config_path = os.path.expanduser(os.path.join(
                self.path_settings_cached.base_path,
                "art",
                "models",
                StableDiffusionVersion.SDXL1_0.value,
                self.generator_settings_cached.pipeline_action
            ))
        else:
            config_path = os.path.dirname(self.model_path)
        try:
            self._pipe = pipeline_class_.from_single_file(
                self.model_path,
                config=config_path,
                add_watermarker=False,
                **data
            )
        except FileNotFoundError as e:
            self.logger.error(
                f"Failed to load model from {self.model_path}: {e}"
            )
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            return
        except EnvironmentError as e:
            self.logger.warning(
                f"Failed to load model from {self.model_path}: {e}"
            )
        except ValueError as e:
            self.logger.error(
                f"Failed to load model from {self.model_path}: {e}"
            )
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            return
        self._send_pipeline_loaded_signal()
        self._move_pipe_to_device()
    
    def _send_pipeline_loaded_signal(self):
        pipeline_type = None
        if self._pipe:
            pipeline_class = self._pipe.__class__
            if pipeline_class in self.txt2img_pipelines:
                pipeline_type = "txt2img"
            elif pipeline_class in self.img2img_pipelines:
                pipeline_type = "img2img"
            elif pipeline_class in self.outpaint_pipelines:
                pipeline_type = "inpaint"
        self.emit_signal(
            SignalCode.SD_PIPELINE_LOADED_SIGNAL, 
            {"pipeline": pipeline_type}
        )

    def _move_pipe_to_device(self):
        if self._pipe is not None:
            try:
                self._pipe.to(self._device)
            except torch.OutOfMemoryError as e:
                self.logger.error(f"Failed to load model to device: {e}")
            except RuntimeError as e:
                self.logger.error(f"Failed to load model to device: {e}")

    def _load_lora(self):
        
        enabled_lora = Lora.objects.filter_by(
            version=self.version,
            enabled=True
        ).all()
        for lora in enabled_lora:
            self._load_lora_weights(lora)

    def _load_lora_weights(self, lora: Lora):
        if lora in self._disabled_lora or lora.path in self._loaded_lora:
            return
        do_disable_lora = False
        filename = os.path.basename(lora.path)
        try:
            lora_base_path = self.lora_base_path
            self.logger.info(
                f"Loading LORA weights from {lora_base_path}/{filename}"
            )
            adapter_name = os.path.splitext(filename)[0]
            adapter_name = adapter_name.replace(".", "_")
            self._pipe.load_lora_weights(
                lora_base_path,
                weight_name=filename,
                adapter_name=adapter_name
            )
            self._loaded_lora[lora.path] = lora
        except AttributeError as _e:
            self.logger.warning("This model does not support LORA")
            do_disable_lora = True
        except RuntimeError:
            self.logger.warning(f"LORA {filename} could not be loaded")
            do_disable_lora = True
        except ValueError:
            self.logger.warning(f"LORA {filename} could not be loaded")
            do_disable_lora = True
        if do_disable_lora:
            self._disabled_lora.append(lora)

    def _set_lora_adapters(self):
        self.logger.debug("Setting LORA adapters")
        
        loaded_lora_id = [lora.id for lora in self._loaded_lora.values()]
        enabled_lora = Lora.objects.filter(Lora.id.in_(loaded_lora_id)).all()
        adapter_weights = []
        adapter_names = []
        for lora in enabled_lora:
            adapter_weights.append(lora.scale / 100.0)
            adapter_names.append(os.path.splitext(os.path.basename(lora.path))[0])
        if len(adapter_weights) > 0:
            self._pipe.set_adapters(adapter_names, adapter_weights=adapter_weights)
            self.logger.debug("LORA adapters set")
        else:
            self.logger.debug("No LORA adapters to set")

    def _load_embeddings(self):
        if self._pipe is None:
            self.logger.error("Pipe is None, unable to load embeddings")
            return
        self.logger.debug("Loading embeddings")
        try:
            self._pipe.unload_textual_inversion()
        except RuntimeError as e:
            self.logger.error(f"Failed to unload embeddings: {e}")
        
        embeddings = Embedding.objects.filter_by(
            version=self.version
        ).all()
        
        for embedding in embeddings:
            embedding_path = embedding.path
            if embedding.active and embedding_path not in self._loaded_embeddings:
                if not os.path.exists(embedding_path):
                    self.logger.error(f"Embedding path {embedding_path} does not exist")
                else:
                    try:
                        self.logger.debug(f"Loading embedding {embedding_path}")
                        self._pipe.load_textual_inversion(
                            embedding_path,
                            token=embedding.name,
                            weight_name=embedding_path
                        )
                        self._loaded_embeddings.append(embedding_path)
                    except Exception as e:
                        self.logger.error(f"Failed to load embedding {embedding_path}: {e}")
        if len(self._loaded_embeddings) > 0:
            self.logger.debug("Embeddings loaded")
        else:
            self.logger.debug("No embeddings enabled")

    def _load_compel(self):
        if self.use_compel:
            try:
                self._load_textual_inversion_manager()
                self._load_compel_proc()
            except Exception as e:
                self.logger.error(f"Error creating compel proc: {e}")
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
        self.logger.debug("Loading textual inversion manager")
        self._textual_inversion_manager = DiffusersTextualInversionManager(self._pipe)

    def _load_compel_proc(self):
        self.logger.debug("Loading compel proc")
        parameters = {
            "truncate_long_prompts": False,
            "textual_inversion_manager": self._textual_inversion_manager
        }
        if self.is_sd_xl_or_turbo:
            tokenizer = [self._pipe.tokenizer, self._pipe.tokenizer_2]
            text_encoder = [self._pipe.text_encoder, self._pipe.text_encoder_2]
            parameters["returned_embeddings_type"] = ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED
            parameters["requires_pooled"] = [False, True]
        else:
            tokenizer = self._pipe.tokenizer
            text_encoder = self._pipe.text_encoder
        parameters.update({
            "tokenizer": tokenizer,
            "text_encoder": text_encoder
        })
        self._compel_proc = Compel(**parameters)

    def _make_memory_efficient(self):
        self._current_memory_settings = self.memory_settings.to_dict()

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
            ("tome_sd_applied", "use_tome_sd", self._apply_tome),
        ]

        for setting_name, attribute_name, apply_func in memory_settings:
            self._apply_memory_setting(setting_name, attribute_name, apply_func)

    def _finalize_load_stable_diffusion(self):
        safety_checker_ready = True
        if self.use_safety_checker:
            safety_checker_ready = (
                self._safety_checker is not None and
                self._feature_extractor is not None
            )
        if (
            self._pipe is not None
            and safety_checker_ready
        ):
            self._current_state = HandlerState.READY
            self.change_model_status(ModelType.SD, ModelStatus.LOADED)
        else:
            self.logger.error("Something went wrong with Stable Diffusion loading")
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            self.unload()
            self._clear_cached_properties()

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
            # self._move_stable_diffusion_to_cpu()
            self._pipe.enable_model_cpu_offload()
        else:
            self.logger.debug("Model cpu offload disabled")

    def _apply_tome(self, attr_val):
        if attr_val:
            tome_sd_ratio = self.memory_settings.tome_sd_ratio / 1000
            self.logger.debug(f"Applying ToMe SD weight merging with ratio {tome_sd_ratio}")
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

    def _unload_loras(self):
        self.logger.debug("Unloading lora")
        if self._pipe is not None:
            self._pipe.unload_lora_weights()
        self._loaded_lora = {}
        self._disabled_lora = []

    def _unload_lora(self, lora: Lora):
        if lora.path in self._loaded_lora:
            self.logger.debug(f"Unloading LORA {lora.path}")
            del self._loaded_lora[lora.path]
        if len(self._loaded_lora) > 0:
            self._set_lora_adapters()
        else:
            self._unload_loras()
            clear_memory()

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
        self._send_pipeline_loaded_signal()

    def _unload_generator(self):
        self.logger.debug("Unloading generator")
        del self._generator
        self._generator = None

    def _load_prompt_embeds(self):
        if not self.use_compel:
            if self._compel_proc is not None:
                self._unload_compel()
            return
        
        if self._compel_proc is None:
            self.logger.debug("Compel proc is not loading - attempting to load")
            self._load_compel()
        
        prompt = self.prompt
        negative_prompt = self.negative_prompt
        second_prompt = self.second_prompt
        second_negative_prompt = self.second_negative_prompt

        if (
            self._current_prompt != prompt
            or self._current_negative_prompt != negative_prompt
            or self._current_prompt_2 != second_prompt
            or self._current_negative_prompt_2 != second_negative_prompt
        ):
            self._unload_latents()
            self._current_prompt = prompt
            self._current_negative_prompt = negative_prompt
            self._current_prompt_2 = second_prompt
            self._current_negative_prompt_2 = second_negative_prompt
            self._unload_prompt_embeds()

        if (
            self._prompt_embeds is None or 
            self._negative_prompt_embeds is None or
            self._pooled_prompt_embeds is None or
            self._negative_pooled_prompt_embeds is None
        ):
            self.logger.debug("Loading prompt embeds")

            pooled_prompt_embeds = None
            negative_pooled_prompt_embeds = None

            if prompt != "" and second_prompt != "":
                compel_prompt = f'("{prompt}", "{second_prompt}").and()'
            elif prompt != "" and second_prompt == "":
                compel_prompt = prompt
            elif prompt == "" and second_prompt != "":
                compel_prompt = second_prompt
            else:
                compel_prompt = ""

            if negative_prompt != "" and second_negative_prompt != "":
                compel_negative_prompt = f'("{negative_prompt}", "{second_negative_prompt}").and()'
            elif negative_prompt != "" and second_negative_prompt == "":
                compel_negative_prompt = negative_prompt
            elif negative_prompt == "" and second_negative_prompt != "":
                compel_negative_prompt = second_negative_prompt
            else:
                compel_negative_prompt = ""

            if self.is_sd_xl_or_turbo:
                prompt_embeds, pooled_prompt_embeds = self._compel_proc.build_conditioning_tensor(compel_prompt)
                negative_prompt_embeds, negative_pooled_prompt_embeds = self._compel_proc.build_conditioning_tensor(
                    compel_negative_prompt
                )
            else:
                prompt_embeds = self._compel_proc.build_conditioning_tensor(compel_prompt)
                negative_prompt_embeds = self._compel_proc.build_conditioning_tensor(compel_negative_prompt)
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

            if self._prompt_embeds is not None:
                self._prompt_embeds.half().to(self._device)
            if self._negative_prompt_embeds is not None:
                self._negative_prompt_embeds.half().to(self._device)
            if self._pooled_prompt_embeds is not None:
                self._pooled_prompt_embeds.half().to(self._device)
            if self._negative_pooled_prompt_embeds is not None:
                self._negative_pooled_prompt_embeds.half().to(self._device)

    def _clear_memory_efficient_settings(self):
        self.logger.debug("Clearing memory efficient settings")
        for key in self._memory_settings_flags:
            if key.endswith("_applied"):
                self._memory_settings_flags[key] = None

    def _prepare_data(self, active_rect=None) -> Dict:
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        self.logger.debug("Preparing data")
        self._set_seed()

        args = {
            "width": int(self.application_settings_cached.working_width),
            "height": int(self.application_settings_cached.working_height),
            "clip_skip": int(self.generator_settings_cached.clip_skip),
            "num_inference_steps": int(self.generator_settings_cached.steps),
            "callback": self._callback,
            "callback_steps": 1,
            "generator": self._generator,
            "callback_on_step_end": self.__interrupt_callback,
        }

        if len(self._loaded_lora) > 0:
            args["cross_attention_kwargs"] = {"scale": self.lora_scale}
            self._set_lora_adapters()

        if self.use_compel:
            args.update({
                "prompt_embeds": self._prompt_embeds,
                "negative_prompt_embeds": self._negative_prompt_embeds,
            })

            if self.is_sd_xl_or_turbo:
                args.update({
                    "pooled_prompt_embeds": self._pooled_prompt_embeds,
                    "negative_pooled_prompt_embeds": self._negative_pooled_prompt_embeds
                })
        else:
            args.update({
                "prompt": self.prompt,
                "negative_prompt": self.negative_prompt
            })

        width = int(self.application_settings_cached.working_width)
        height = int(self.application_settings_cached.working_height)
        image = None
        mask = None

        if self.is_txt2img or self.is_outpaint or self.is_img2img:
            args.update({
                "width": width,
                "height": height
            })

        if self.is_img2img:
            image = self.img2img_image
            if args["num_inference_steps"] < MIN_NUM_INFERENCE_STEPS_IMG2IMG:
                args["num_inference_steps"] = MIN_NUM_INFERENCE_STEPS_IMG2IMG
        elif self.is_outpaint:
            image = self.outpaint_image
            if not image:
                image = self.drawing_pad_image
            mask = self.drawing_pad_mask

            # Crop the image based on the active grid location
            active_grid_x = active_rect.left()
            active_grid_y = active_rect.top()
            cropped_image = image.crop((active_grid_x, active_grid_y, width + active_grid_x, height + active_grid_y))

            # Create a new image with a black strip at the bottom
            new_image = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 255))
            new_image.paste(cropped_image, (0, 0))
            image = new_image.convert("RGB")

        args["guidance_scale"] = self.generator_settings_cached.scale / 100.0

        if not self.controlnet_enabled:
            if self.is_img2img:
                args["strength"] = self.generator_settings_cached.strength / 100.0
            elif self.is_outpaint:
                args["strength"] = self.outpaint_settings_cached.strength / 100.0

        # set the image to controlnet image if controlnet is enabled
        if self.controlnet_enabled:
            controlnet_image = self.controlnet_image
            if controlnet_image:
                controlnet_image = self._resize_image(controlnet_image, width, height)
                control_image = self._controlnet_processor(controlnet_image, to_pil=True)
                if control_image is not None:
                    self.update_settings_by_name(
                        "controlnet_settings",
                        "generated_image",
                        convert_image_to_binary(control_image)
                    )
                    if self.is_txt2img:
                        image = control_image
                    else:
                        args["control_image"] = control_image
                else:
                    raise ValueError("Controlnet image is None")

        if image is not None:
            image = self._resize_image(image, width, height)
            args["image"] = image

        if mask is not None and self.is_outpaint:
            mask = self._resize_image(mask, width, height)
            mask = self._pipe.mask_processor.blur(mask, blur_factor=self.mask_blur)
            args["mask_image"] = mask

        if self.controlnet_enabled:
            args.update({
                "guess_mode": False,
                "control_guidance_start": 0.0,
                "control_guidance_end": 1.0,
                "strength": self.controlnet_strength / 100.0,
                "guidance_scale": self.generator_settings_scale / 100.0,
                "controlnet_conditioning_scale": self.controlnet_conditioning_scale / 100.0
            })
        return args

    def _resize_image(self, image: Image, max_width: int, max_height: int) -> Optional[Image]:
        """
        Resize the image to ensure it is not larger than max_width and max_height,
        while maintaining the aspect ratio.

        :param image: The input PIL Image.
        :param max_width: The maximum allowed width.
        :param max_height: The maximum allowed height.
        :return: The resized PIL Image.
        """
        if image is None:
            return None

        # Get the original dimensions
        original_width, original_height = image.size

        # Check if resizing is necessary
        if original_width <= max_width and original_height <= max_height:
            return image

        # Calculate the aspect ratio
        aspect_ratio = original_width / original_height

        # Determine the new dimensions while maintaining the aspect ratio
        if aspect_ratio > 1:
            # Landscape orientation
            new_width = min(max_width, original_width)
            new_height = int(new_width / aspect_ratio)
        else:
            # Portrait orientation or square
            new_height = min(max_height, original_height)
            new_width = int(new_height * aspect_ratio)

        # Resize the image
        resized_image = image.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)
        return resized_image

    def _set_seed(self):
        seed = self.generator_settings_cached.seed
        self._generator.manual_seed(seed)

    def _callback(self, step: int, _time_step, latents):
        self.emit_signal(SignalCode.SD_PROGRESS_SIGNAL, {
            "step": step,
            "total": self.generator_settings_cached.steps
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
