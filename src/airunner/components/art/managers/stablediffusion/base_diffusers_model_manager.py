import os
from typing import Any, List, Dict, Optional, Type

import PIL
import diffusers
import tomesd
import torch
import torch.amp
from DeepCache import DeepCacheSDHelper
from PIL.Image import Image
from compel import (
    Compel,
    DiffusersTextualInversionManager,  # retained for backward compatibility if referenced elsewhere
)
from airunner.components.art.managers.stablediffusion.safe_textual_inversion_manager import (
    SafeDiffusersTextualInversionManager,
)
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    StableDiffusionControlNetPipeline,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionControlNetInpaintPipeline,
    ControlNetModel,
)

from airunner.components.art.data.ai_models import AIModels
from airunner.components.art.data.controlnet_model import ControlnetModel
from airunner.components.art.data.embedding import Embedding
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.schedulers import Schedulers
from airunner.components.art.workers.image_export_worker import (
    ImageExportWorker,
)
from airunner.settings import (
    AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT,
    AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT,
    AIRUNNER_PAINTING_NEGATIVE_PROMPT,
    AIRUNNER_PHOTO_REALISTIC_PROMPT,
    AIRUNNER_ILLUSTRATION_PROMPT,
    AIRUNNER_PAINTING_PROMPT,
    CUDA_ERROR,
)
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from transformers import (
    CLIPFeatureExtractor,
)
from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.enums import (
    GeneratorSection,
    ModelStatus,
    ModelType,
    HandlerState,
    EngineResponseCode,
    ModelAction,
    ImagePreset,
    StableDiffusionVersion,
)
from airunner.components.application.exceptions import (
    PipeNotLoadedException,
    InterruptedException,
)
from airunner.settings import (
    AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG,
    AIRUNNER_LOCAL_FILES_ONLY,
    AIRUNNER_MEM_USE_LAST_CHANNELS,
    AIRUNNER_MEM_USE_ATTENTION_SLICING,
    AIRUNNER_MEM_USE_ENABLE_VAE_SLICING,
    AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD,
    AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD,
    AIRUNNER_MEM_USE_TOME_SD,
    AIRUNNER_MEM_TOME_SD_RATIO,
    AIRUNNER_MEM_SD_DEVICE,
    AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS,
    AIRUNNER_MEM_USE_TILED_VAE,
    AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE,
)
from airunner.utils.application.create_worker import create_worker
from airunner.utils.memory import clear_memory, is_ampere_or_newer
from airunner.utils.image import (
    convert_binary_to_image,
    convert_image_to_binary,
)
from airunner.utils.application import get_torch_device

from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
from diffusers import SchedulerMixin
from airunner.components.art.managers.stablediffusion import (
    model_loader,
    prompt_utils,
    image_generation,
    utils,
)


class BaseDiffusersModelManager(BaseModelManager):
    def __init__(self, *args, **kwargs):
        self._scheduler = None
        self._model_status = {
            ModelType.SD: ModelStatus.UNLOADED,
            ModelType.SAFETY_CHECKER: ModelStatus.UNLOADED,
            ModelType.CONTROLNET: ModelStatus.UNLOADED,
            ModelType.LORA: ModelStatus.UNLOADED,
            ModelType.EMBEDDINGS: ModelStatus.UNLOADED,
        }
        super().__init__(*args, **kwargs)
        self._pipeline: Optional[str] = None
        self._scheduler_name: Optional[str] = None
        self._scheduler: Type[SchedulerMixin]
        self._image_request: ImageRequest = None
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
        self._textual_inversion_manager: Optional[
            DiffusersTextualInversionManager
        ] = None
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
        self._application_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None
        self._current_memory_settings = None

        self.image_export_worker = create_worker(ImageExportWorker)

    def settings_changed(self):
        if self._pipe and self._pipe.__class__ is not self._pipeline_class:
            self._swap_pipeline()

    @property
    def active_rect(self) -> Rect:
        pos = self.active_grid_settings.pos
        active_rect = Rect(
            pos[0],
            pos[1],
            self.application_settings.working_width,
            self.application_settings.working_height,
        )
        drawing_pad_pos = self.drawing_pad_settings.pos
        active_rect.translate(
            -drawing_pad_pos[0],
            -drawing_pad_pos[1],
        )
        return active_rect

    @property
    def controlnet(self) -> Optional[ControlNetModel]:
        if self._controlnet is None:
            self._load_controlnet_model()
        return self._controlnet

    @controlnet.setter
    def controlnet(self, value: Optional[ControlNetModel]):
        if value is None:
            del self._controlnet
        self._controlnet = value

    @property
    def controlnet_processor(self) -> Any:
        if self._controlnet_processor is None:
            self._load_controlnet_processor()
        return self._controlnet_processor

    @controlnet_processor.setter
    def controlnet_processor(self, value: Optional[Any]):
        self._controlnet_processor = value

    @property
    def img2img_pipelines(
        self,
    ) -> List[Any]:
        return []

    @property
    def txt2img_pipelines(
        self,
    ) -> List[Any]:
        return []

    @property
    def controlnet_pipelines(
        self,
    ) -> List[Any]:
        return []

    @property
    def outpaint_pipelines(
        self,
    ) -> List[Any]:
        return []

    @property
    def use_compel(self) -> bool:
        compel = self.image_request.use_compel if self.image_request else None
        if compel is None:
            compel = self.generator_settings.use_compel
        return compel

    @property
    def generator(self) -> torch.Generator:
        if self._generator is None:
            self.logger.debug("Loading generator")
            self._generator = torch.Generator(device=self._device)
        return self._generator

    @property
    def controlnet_path(self) -> Optional[str]:
        if self.controlnet_model:
            version = self.version
            if version == StableDiffusionVersion.SDXL_TURBO.value:
                version = StableDiffusionVersion.SDXL1_0.value
            return os.path.join(
                self.path_settings.base_path,
                "art/models",
                version,
                "controlnet",
                os.path.expanduser(self.controlnet_model.path),
            )
        return None

    @property
    def controlnet_processor_path(self):
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art",
                "models",
                "controlnet_processors",
            )
        )

    @property
    def model_status(self) -> Dict[ModelType, ModelStatus]:
        return self._model_status

    @property
    def img2img_image_cached(self) -> Image:
        if self._img2img_image is None:
            self._img2img_image = self.img2img_image
        return self._img2img_image

    @property
    def image_request(self) -> ImageRequest:
        return self._image_request

    @image_request.setter
    def image_request(self, value: ImageRequest):
        self._image_request = value

    @property
    def controlnet_image(self) -> Image:
        img = self.controlnet_settings.image
        if img is not None:
            img = convert_binary_to_image(img)
        return img

    @property
    def controlnet_model(self) -> Optional[ControlnetModel]:
        if (
            self._controlnet_model is None
            or self._controlnet_model.version != self.version
            or self._controlnet_model.display_name
            != self.controlnet_settings.controlnet
        ):
            self.logger.debug(
                f"Loading controlnet model from database {self.controlnet_settings.controlnet} {self.version}"
            )
            self._controlnet_model = ControlnetModel.objects.filter_by_first(
                display_name=self.controlnet_settings.controlnet,
                version=self.version,
            )
        return self._controlnet_model

    @property
    def controlnet_enabled(self) -> bool:
        return (
            self.controlnet_settings.enabled
            and self.application_settings.controlnet_enabled
            and self.controlnet_settings.image is not None
        )

    @property
    def controlnet_strength(self) -> int:
        return self.controlnet_settings.strength

    @property
    def controlnet_conditioning_scale(self) -> int:
        return self.controlnet_settings.conditioning_scale

    @property
    def controlnet_is_loading(self) -> bool:
        return self.model_status[ModelType.CONTROLNET] is ModelStatus.LOADING

    @property
    def pipeline(self) -> str:
        return self.generator_settings.pipeline_action

    @property
    def operation_type(self) -> str:
        operation_type = self.pipeline
        if self.is_img2img:
            operation_type = "img2img"
        elif self.is_inpaint:
            operation_type = "inpaint"
        elif self.is_outpaint:
            operation_type = "outpaint"
        if self.controlnet_enabled:
            operation_type = f"{operation_type}_controlnet"
        return operation_type

    @property
    def scheduler_name(self) -> str:
        return self._scheduler_name

    @scheduler_name.setter
    def scheduler_name(self, value: str):
        self._scheduler_name = value

    @property
    def scheduler(self) -> Type[SchedulerMixin]:
        return self._scheduler

    @scheduler.setter
    def scheduler(self, value: Type[SchedulerMixin]):
        self._scheduler = value

    @property
    def real_model_version(self) -> str:
        """
        The real model version. Only use this when we need to
        check the real version of the model.
        """
        version = self.image_request.version if self.image_request else None
        if not version:
            version = self.generator_settings.version
        return version

    @property
    def version(self) -> str:
        return self.real_model_version

    @property
    def section(self) -> GeneratorSection:
        # Check if we have an inpaint model selected, prioritize that
        if (
            self.generator_settings.pipeline_action
            == GeneratorSection.INPAINT.value
        ):
            return GeneratorSection.INPAINT

        section = GeneratorSection.TXT2IMG
        if (
            self.img2img_image_cached is not None
            and self.image_to_image_settings.enabled
        ):
            section = GeneratorSection.IMG2IMG
        if (
            self.drawing_pad_settings.image is not None
            and self.outpaint_settings.enabled
        ):
            section = GeneratorSection.OUTPAINT
        return section

    @property
    def custom_path(
        self,
    ) -> Optional[str]:  # Changed return type to Optional[str]
        path_value = (
            self.image_request.custom_path if self.image_request else None
        )
        if path_value is None:
            path_value = self.generator_settings.custom_path
        if path_value is not None and path_value != "":
            expanded_path = os.path.expanduser(path_value)
            # Check if the expanded path exists
            if os.path.exists(expanded_path):
                return expanded_path
        return None  # Return None if path is None, empty, or doesn't exist

    @property
    def model_path(
        self,
    ) -> Optional[str]:  # Changed return type to Optional[str]
        custom_path = (
            self.custom_path
        )  # Use the property which already checks existence
        if custom_path is not None:
            return custom_path

        path = self.image_request.model_path if self.image_request else None
        if path is None or path == "":
            model_id = self.generator_settings.model
            if model_id is not None:
                model = AIModels.objects.get(model_id)
                if model is not None:
                    path = model.path

        # Ensure the final path exists if it's not None or empty
        if path and path != "":
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
            else:
                # Log a warning if the path is specified but doesn't exist
                self.logger.warning(
                    f"Model path specified but does not exist: {path}"
                )

        return None  # Return None if no valid path found

    @property
    def lora_base_path(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self.version,
                "lora",
            )
        )

    @property
    def lora_scale(self) -> float:
        return self.image_request.lora_scale / 100.0

    @property
    def data_type(self) -> torch.dtype:
        return torch.float16

    @property
    def use_safety_checker(self) -> bool:
        return self.application_settings.nsfw_filter

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
    def is_inpaint(self) -> bool:
        return self.section is GeneratorSection.INPAINT

    @property
    def safety_checker_is_loading(self):
        return (
            self.model_status[ModelType.SAFETY_CHECKER] is ModelStatus.LOADING
        )

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
    def _device_index(self):
        device = AIRUNNER_MEM_SD_DEVICE
        if device is None:
            device = self.memory_settings.default_gpu_sd
        return device

    @property
    def _device(self):
        return get_torch_device(self._device_index)

    @property
    def pipeline_map(
        self,
    ) -> Dict[str, Any]:
        return {
            "txt2img": StableDiffusionPipeline,
            "img2img": StableDiffusionImg2ImgPipeline,
            "inpaint": StableDiffusionInpaintPipeline,
            "outpaint": StableDiffusionInpaintPipeline,
            "txt2img_controlnet": StableDiffusionControlNetPipeline,
            "img2img_controlnet": StableDiffusionControlNetImg2ImgPipeline,
            "inpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
            "outpaint_controlnet": StableDiffusionControlNetInpaintPipeline,
        }

    @property
    def _pipeline_class(self):
        return self.pipeline_map.get(self.operation_type)

    @property
    def mask_blur(self) -> int:
        return self.outpaint_settings.mask_blur

    @property
    def do_join_prompts(self) -> bool:
        return (
            self.use_compel
            and self.image_request.additional_prompts is not None
            and len(self.image_request.additional_prompts) > 0
        )

    @property
    def prompt_preset(self) -> str:
        if self.image_request.image_preset is ImagePreset.PHOTOGRAPH:
            return AIRUNNER_PHOTO_REALISTIC_PROMPT
        elif self.image_request.image_preset is ImagePreset.ILLUSTRATION:
            return AIRUNNER_ILLUSTRATION_PROMPT
        elif self.image_request.image_preset is ImagePreset.PAINTING:
            return AIRUNNER_PAINTING_PROMPT
        return ""

    @property
    def negative_prompt_preset(self) -> str:
        if self.image_request.image_preset is ImagePreset.PHOTOGRAPH:
            return AIRUNNER_PHOTO_REALISTIC_NEGATIVE_PROMPT
        elif self.image_request.image_preset is ImagePreset.ILLUSTRATION:
            return AIRUNNER_ILLUSTRATION_NEGATIVE_PROMPT
        elif self.image_request.image_preset is ImagePreset.PAINTING:
            return AIRUNNER_PAINTING_NEGATIVE_PROMPT
        return ""

    @property
    def prompt(self) -> str:
        prompt = prompt_utils.format_prompt(
            self.image_request.prompt,
            prompt_utils.get_prompt_preset(self.image_request.image_preset),
            (
                self.image_request.additional_prompts
                if self.do_join_prompts
                else None
            ),
        )
        return prompt

    @property
    def negative_prompt(self) -> str:
        return prompt_utils.format_negative_prompt(
            self.image_request.negative_prompt,
            prompt_utils.get_negative_prompt_preset(
                self.image_request.image_preset
            ),
        )

    @property
    def config_path(self) -> str:
        path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models",
                self.version,
                self.pipeline,
            )
        )
        return path

    @property
    def compel_tokenizer(self) -> Any:
        return self._pipe.tokenizer

    @property
    def compel_text_encoder(self) -> Any:
        return self._pipe.text_encoder

    @property
    def compel_parameters(self) -> Dict[str, Any]:
        parameters = {
            "truncate_long_prompts": False,
            "textual_inversion_manager": self._textual_inversion_manager,
            "tokenizer": self.compel_tokenizer,
            "text_encoder": self.compel_text_encoder,
        }
        return parameters

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

    def load_controlnet(self) -> bool:
        """
        Public method to load the controlnet model.
        """
        # clear the controlnet settings so that we get the latest selected controlnet model
        if not self.controlnet_enabled or self.controlnet_is_loading:
            return False
        self._controlnet_model = None
        self._controlnet_settings = None
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)

        try:
            self._load_controlnet_model()
        except Exception as e:
            self.logger.error(
                f"Error loading controlnet {e} from {self.controlnet_path}"
            )
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)
            return False

        try:
            self._load_controlnet_processor()
        except Exception as e:
            self.logger.error(f"Error loading controlnet processor {e}")
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)
            return False

        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED)
        return True

    def unload_controlnet(self):
        """
        Public method to unload the controlnet model.
        """
        if self.controlnet_is_loading:
            return
        self._unload_controlnet()

    def _swap_pipeline(self):
        pipeline_class_ = self._pipeline_class
        if (
            self._pipe.__class__ is pipeline_class_ or self._pipe is None
        ):  # noqa
            return
        self.logger.info(
            "Swapping pipeline from %s to %s",
            self._pipe.__class__ if self._pipe else "",
            pipeline_class_,
        )
        try:
            self._unload_compel()
            self._unload_deep_cache()
            self._clear_memory_efficient_settings()
            clear_memory()
            original_config = dict(self._pipe.config)
            kwargs = {
                k: getattr(self._pipe, k) for k in original_config.keys()
            }

            if self.controlnet_enabled:
                kwargs["controlnet"] = self.controlnet
            else:
                kwargs.pop("controlnet", None)

            kwargs = {
                k: v
                for k, v in kwargs.items()
                if k
                in [
                    "vae",
                    "text_encoder",
                    "text_encoder_2",
                    "tokenizer",
                    "tokenizer_2",
                    "unet",
                    "controlnet",
                    "scheduler",
                    "feature_extractor",
                    "image_encoder",
                    "force_zeros_for_empty_prompt",
                ]
            }

            self._pipe = self._pipeline_class(**kwargs)
        except Exception as e:
            self.logger.error(f"Error swapping pipeline: {e}")
        finally:
            self._load_compel()
            self._load_deep_cache()
            self._make_memory_efficient()
            self._send_pipeline_loaded_signal()
            self._move_pipe_to_device()

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
        if self.model_path is None or self.model_path == "":
            self.logger.error("No model selected")
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            return
        self._load_safety_checker()

        if (
            self.controlnet_enabled
            and not self.controlnet_is_loading
            and self._pipe
            and not self._controlnet_model
        ):
            self.unload()

        self.load_controlnet()

        if self._load_pipe():
            self._send_pipeline_loaded_signal()
            self._move_pipe_to_device()
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
            HandlerState.GENERATING,
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
        self._send_pipeline_loaded_signal()
        self._clear_memory_efficient_settings()
        clear_memory()
        self.change_model_status(ModelType.SD, ModelStatus.UNLOADED)

    def handle_generate_signal(self, message: Optional[Dict] = None):
        self.image_request = message.get("image_request", None)

        if not self.image_request:
            raise ValueError("ImageRequest is None")

        if self.image_request.scheduler != self.scheduler_name:
            self._load_scheduler(self.image_request.scheduler)

        self._clear_cached_properties()

        if self._current_state not in (
            HandlerState.GENERATING,
            HandlerState.PREPARING_TO_GENERATE,
        ):
            self._generate()
            self._current_state = HandlerState.READY
            clear_memory()
        self.handle_requested_action()

        # Clear the image request so that we no longer
        # use its values in the next request.
        self.image_request = None

    def reload_lora(self):
        if self.model_status[
            ModelType.SD
        ] is not ModelStatus.LOADED or self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING,
        ):
            return
        self.change_model_status(ModelType.LORA, ModelStatus.LOADING)
        self._unload_loras()
        self._load_lora()
        self.api.art.lora_updated()
        self.change_model_status(ModelType.LORA, ModelStatus.LOADED)

    def reload_embeddings(self):
        if self.model_status[
            ModelType.SD
        ] is not ModelStatus.LOADED or self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING,
        ):
            return
        self.change_model_status(ModelType.EMBEDDINGS, ModelStatus.LOADING)
        self._load_embeddings()
        self.api.art.embedding_updated()
        self.change_model_status(ModelType.EMBEDDINGS, ModelStatus.LOADED)

    def load_embeddings(self):
        self._load_embeddings()

    def interrupt_image_generation(self):
        if self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING,
        ):
            self.do_interrupt_image_generation = True

    def _clear_cached_properties(self):
        self._outpaint_image = None
        self._img2img_image = None
        self._controlnet_settings = None
        self._controlnet_image_settings = None
        self._application_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None

    def _generate(self):
        self.logger.debug("Generating image")
        if self._pipe is None:
            raise PipeNotLoadedException()
        self._load_prompt_embeds()
        clear_memory()
        data = self._prepare_data(self.active_rect)
        self._current_state = HandlerState.GENERATING

        try:
            for results in self._get_results(data):

                # Benchmark getting images from results
                generated_images = results.get("images", [])

                images, nsfw_content_detected = (
                    self._check_and_mark_nsfw_images(generated_images)
                )

                if images is not None:
                    self.api.art.final_progress_update(
                        total=self.image_request.steps
                    )

                    data.update(
                        {
                            "current_prompt": self._current_prompt,
                            "current_prompt_2": self._current_prompt_2,
                            "current_negative_prompt": self._current_negative_prompt,
                            "current_negative_prompt_2": self._current_negative_prompt_2,
                            "image_request": self.image_request,
                            "model_path": self.model_path,
                            "version": self.version,
                            "scheduler_name": self.scheduler_name,
                            "loaded_lora": self._loaded_lora,
                            "loaded_embeddings": self._loaded_embeddings,
                            "controlnet_enabled": self.controlnet_enabled,
                            "is_txt2img": self.is_txt2img,
                            "is_img2img": self.is_img2img,
                            "is_inpaint": self.is_inpaint,
                            "is_outpaint": self.is_outpaint,
                            "mask_blur": self.mask_blur,
                            "memory_settings_flags": self._memory_settings_flags,
                            "application_settings": self.application_settings,
                            "path_settings": self.path_settings,
                            "metadata_settings": self.metadata_settings,
                            "controlnet_settings": self.controlnet_settings,
                        }
                    )

                    self.image_export_worker.add_to_queue(
                        {
                            "images": images,
                            "data": data,
                        }
                    )
                else:
                    images = images or []

                self._current_state = HandlerState.PREPARING_TO_GENERATE
                response = None
                code = EngineResponseCode.NONE
                try:
                    response = ImageResponse(
                        images=images,
                        data=data,
                        nsfw_content_detected=any(nsfw_content_detected),
                        active_rect=self.active_rect,
                        is_outpaint=self.is_outpaint,
                        node_id=self.image_request.node_id,
                    )
                    code = EngineResponseCode.IMAGE_GENERATED
                except PipeNotLoadedException as e:
                    self.logger.error(e)
                except InterruptedException as e:
                    code = EngineResponseCode.INTERRUPTED
                except Exception as e:
                    code = EngineResponseCode.ERROR
                    error_message = f"Error generating image: {e}"
                    response = error_message
                    if CUDA_ERROR in str(e):
                        code = EngineResponseCode.INSUFFICIENT_GPU_MEMORY
                        response = AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE
                    self.logger.error(error_message)
                if self.image_request.callback:
                    self.image_request.callback(response)
                self.api.worker_response(code=code, message=response)
        except InterruptedException as e:
            self.logger.debug("Image generation interrupted")
            self._current_state = HandlerState.READY
            self.api.worker_response(
                code=EngineResponseCode.INTERRUPTED,
                message="Image generation interrupted",
            )
            self.do_interrupt_image_generation = False

    def _get_results(self, data):
        with torch.no_grad(), torch.amp.autocast(
            "cuda", dtype=self.data_type, enabled=True
        ):
            total = 0
            while total < self.image_request.n_samples:
                if self.do_interrupt_image_generation:
                    raise InterruptedException()
                results = self._pipe(**data)
                yield results
                if not self.image_request.generate_infinite_images:
                    total += 1

    def _load_safety_checker(self):
        if (
            not self.application_settings.nsfw_filter
            or self.safety_checker_is_loading
        ):
            return
        self._safety_checker = model_loader.load_safety_checker(
            self.application_settings, self.path_settings, self.data_type
        )
        self._feature_extractor = model_loader.load_feature_extractor(
            self.path_settings, self.data_type
        )
        if self._safety_checker:
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.LOADED
            )
        else:
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.FAILED
            )

    def _unload_safety_checker(self):
        model_loader.unload_safety_checker(self._pipe, self.logger)
        self._safety_checker = None

    def _load_controlnet_model(self):
        if not self.controlnet_enabled:
            return
        self._controlnet = model_loader.load_controlnet_model(
            self.controlnet_enabled,
            self.controlnet_path,
            self.data_type,
            self._pipe.device if self._pipe else self._device,
            self.logger,
        )
        if self._controlnet:
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED)
        else:
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)

    def _unload_controlnet(self):
        self._controlnet = None
        # Add further cleanup if needed

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        if not scheduler_name:
            return
        self.scheduler = model_loader.load_scheduler(
            scheduler_name,
            self.path_settings,
            self.version,
            self.logger,
        )
        if self.scheduler:
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
        else:
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)

    def _load_lora(self):
        self.logger.debug("Loading LORA weights")
        enabled_lora = Lora.objects.filter_by(
            version=self.version, enabled=True
        )
        for lora in enabled_lora:
            if model_loader.load_lora_weights(
                self._pipe, lora, self.lora_base_path, self.logger
            ):
                self._loaded_lora[lora.path] = lora
            else:
                self._disabled_lora.append(lora)

    def _unload_loras(self):
        model_loader.unload_lora(self._pipe, self.logger)
        self._loaded_lora = {}
        self._disabled_lora = []

    def _load_embeddings(self):
        if self._pipe is None:
            self.logger.error("Pipe is None, unable to load embeddings")
            return
        model_loader.unload_embeddings(self._pipe, self.logger)
        embeddings = Embedding.objects.filter_by(version=self.version)
        for embedding in embeddings:
            if model_loader.load_embedding(self._pipe, embedding, self.logger):
                self._loaded_embeddings.append(embedding.path)
        if self._loaded_embeddings:
            self.logger.debug("Embeddings loaded")
        else:
            self.logger.debug("No embeddings enabled")

    def _unload_emebeddings(self):
        model_loader.unload_embeddings(self._pipe, self.logger)
        self._loaded_embeddings = []

    def _load_compel(self):
        if self.use_compel:
            self._compel_proc = model_loader.load_compel_proc(
                self.compel_parameters, self.logger
            )
        else:
            model_loader.unload_compel_proc(self._compel_proc, self.logger)
            self._compel_proc = None

    def _load_deep_cache(self):
        self._deep_cache_helper = model_loader.load_deep_cache_helper(
            self._pipe, self.logger
        )

    def _unload_deep_cache(self):
        model_loader.unload_deep_cache_helper(
            self._deep_cache_helper, self.logger
        )
        self._deep_cache_helper = None

    def _check_and_mark_nsfw_images(self, images):
        return image_generation.check_and_mark_nsfw_images(
            images, self._feature_extractor, self._safety_checker, self._device
        )

    def _resize_image(self, image, max_width, max_height):
        return utils.resize_image(image, max_width, max_height)

    def _load_safety_checker_model(self):
        self.logger.debug("Loading safety checker")
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        safety_checker_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art",
                "models",
                "SD 1.5",
                "txt2img",
                "safety_checker",
            )
        )
        try:
            self._safety_checker = (
                StableDiffusionSafetyChecker.from_pretrained(
                    safety_checker_path,
                    torch_dtype=self.data_type,
                    device_map="cpu",
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    use_safetensors=False,
                )
            )
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.LOADED
            )
        except Exception as e:
            self.logger.error(f"Unable to load safety checker: {e}")
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.FAILED
            )

    def _load_feature_extractor(self):
        self.logger.debug("Loading feature extractor")
        self.change_model_status(
            ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADING
        )
        feature_extractor_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art",
                "models",
                "SD 1.5",
                "txt2img",
                "feature_extractor",
            )
        )
        try:
            self._feature_extractor = CLIPFeatureExtractor.from_pretrained(
                feature_extractor_path,
                torch_dtype=self.data_type,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                use_safetensors=True,
            )
            self.change_model_status(
                ModelType.FEATURE_EXTRACTOR, ModelStatus.LOADED
            )
        except Exception as e:
            self.logger.error(f"Unable to load feature extractor {e}")
            self.change_model_status(
                ModelType.FEATURE_EXTRACTOR, ModelStatus.FAILED
            )

    def _load_controlnet_processor(self):
        if not self.controlnet_enabled:
            return
        self._controlnet_processor = model_loader.load_controlnet_processor(
            self.controlnet_enabled,
            self.controlnet_model,
            self.controlnet_processor_path,
            self.logger,
        )

    def _unload_controlnet_processor(self):
        model_loader.unload_controlnet_processor(
            self._controlnet_processor, self.logger
        )
        self._controlnet_processor = None

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        if not scheduler_name:
            return

        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)

        self.scheduler_name = scheduler_name or self.scheduler_name
        base_path: str = self.path_settings.base_path
        scheduler_version: str = self.version
        scheduler_path = os.path.expanduser(
            os.path.join(
                base_path,
                "art/models",
                scheduler_version,
                "txt2img",
                "scheduler",
                "scheduler_config.json",
            )
        )

        scheduler = Schedulers.objects.filter_by_first(
            display_name=scheduler_name
        )
        if not scheduler:
            self.logger.error(f"Failed to find scheduler {scheduler_name}")
            return None
        scheduler_class_name = scheduler.name
        scheduler_class = getattr(diffusers, scheduler_class_name)
        try:
            self.scheduler = scheduler_class.from_pretrained(
                scheduler_path,
                subfolder="scheduler",
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
            self.current_scheduler_name = scheduler_name
            self.logger.debug(f"Loaded scheduler {scheduler_name}")
        except Exception as e:
            self.logger.error(
                f"Failed to load scheduler {scheduler_name}: {e}"
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
            return
        if self._pipe:
            self._pipe.scheduler = self.scheduler

    def _load_pipe(self) -> bool:
        self.logger.debug(
            f"Loading pipe {self._pipeline_class} for {self.section}"
        )
        self.change_model_status(ModelType.SD, ModelStatus.LOADING)
        data = {
            "torch_dtype": self.data_type,
            "use_safetensors": True,
            "local_files_only": True,
            "device": self._device,
        }
        if self.controlnet_enabled:
            data.update(controlnet=self.controlnet)

        if self.controlnet_enabled:
            data["controlnet"] = self.controlnet

        if data is None:
            return

        try:
            self._set_pipe(self.config_path, data)
            self.change_model_status(ModelType.SD, ModelStatus.LOADED)
        except (
            FileNotFoundError,
            EnvironmentError,
            torch.OutOfMemoryError,
            ValueError,
            diffusers.loaders.single_file_utils.SingleFileComponentError,
        ) as e:
            code = EngineResponseCode.ERROR
            error_message = f"Failed to load model from {self.model_path}: {e}"
            response = error_message
            if CUDA_ERROR in str(e):
                code = EngineResponseCode.INSUFFICIENT_GPU_MEMORY
                response = AIRUNNER_CUDA_OUT_OF_MEMORY_MESSAGE
            self.logger.error(error_message)
            self.api.worker_response(code, response)
            self.change_model_status(ModelType.SD, ModelStatus.FAILED)
            return False
        return True

    def _set_pipe(self, config_path: str, data: Dict):
        pipeline_class_ = self._pipeline_class
        self.logger.info(
            f"Loading {pipeline_class_.__class__} from {self.model_path}"
        )
        self._pipe = pipeline_class_.from_single_file(
            self.model_path,
            config=config_path,
            add_watermarker=False,
            **data,
        )

    def _send_pipeline_loaded_signal(self):
        pipeline_type = None
        if self._pipe:
            pipeline_class = self._pipe.__class__
            if pipeline_class in self.txt2img_pipelines:
                pipeline_type = GeneratorSection.TXT2IMG
            elif pipeline_class in self.img2img_pipelines:
                pipeline_type = GeneratorSection.IMG2IMG
            elif pipeline_class in self.outpaint_pipelines:
                pipeline_type = GeneratorSection.INPAINT
        if pipeline_type is not None:
            self.api.art.pipeline_loaded(pipeline_type)

    def _move_pipe_to_device(self):
        if self._pipe is not None:
            try:
                self._pipe.to(self._device)
            except torch.OutOfMemoryError as e:
                self.logger.error(f"Failed to load model to device: {e}")
            except RuntimeError as e:
                self.logger.error(f"Failed to load model to device: {e}")

    def _load_lora_weights(self, lora: Lora):
        if lora in self._disabled_lora or lora.path in self._loaded_lora:
            return
        do_disable_lora = False
        filename = os.path.basename(lora.path)
        try:
            lora_base_path = self.lora_base_path
            adapter_name = os.path.splitext(filename)[0]
            adapter_name = adapter_name.replace(".", "_")
            self._pipe.load_lora_weights(
                lora_base_path, weight_name=filename, adapter_name=adapter_name
            )
            self._loaded_lora[lora.path] = lora
        except AttributeError as _e:
            message = "This model does not support LORA"
            do_disable_lora = True
        except RuntimeError:
            message = f"LORA {filename} could not be loaded"
            do_disable_lora = True
        except ValueError:
            message = f"LORA {filename} could not be loaded"
            do_disable_lora = True
        if do_disable_lora:
            self.logger.warning(message)
            self._disabled_lora.append(lora)

    def _set_lora_adapters(self):
        self.logger.debug("Setting LORA adapters")
        loaded_lora_id = [lora.id for lora in self._loaded_lora.values()]
        enabled_lora = Lora.objects.filter(Lora.id.in_(loaded_lora_id))
        adapter_weights = []
        adapter_names = []
        for lora in enabled_lora:
            adapter_weights.append(lora.scale / 100.0)
            adapter_name = os.path.splitext(os.path.basename(lora.path))[0]
            adapter_name = adapter_name.replace(".", "_")
            adapter_names.append(adapter_name)
        if len(adapter_weights) > 0:
            self._pipe.set_adapters(
                adapter_names, adapter_weights=adapter_weights
            )
            self.logger.debug("LORA adapters set")
        else:
            self.logger.debug("No LORA adapters to set")

    def _load_embeddings(self):
        if self._pipe is None:
            self.logger.error("Pipe is None, unable to load embeddings")
            return
        embeddings = Embedding.objects.filter_by(version=self.version)
        embeddings_changed = False
        for embedding in embeddings:
            if not embedding.path:
                continue
            if (
                os.path.exists(embedding.path)
                and embedding.path not in self._loaded_embeddings
                and embedding.active
            ):
                embeddings_changed = True
                self._load_embedding(embedding)
            elif embedding.path in self._loaded_embeddings and (
                not os.path.exists(embedding.path) or not embedding.active
            ):
                embeddings_changed = True
                self._unload_embedding(embedding)
        self.logger.info(f"Loaded embeddings: {self._loaded_embeddings}")
        if embeddings_changed:
            # Invalidate cached prompt embeddings to ensure new embeddings are applied
            self._unload_prompt_embeds()

    def _load_embedding(self, embedding):
        file_name = os.path.basename(embedding.path)
        path_name = os.path.dirname(embedding.path)
        self._pipe.load_textual_inversion(
            path_name,
            weight_name=file_name,
            token=embedding.trigger_word.split(","),
        )
        self._loaded_embeddings.append(embedding.path)

    def _unload_embedding(self, embedding):
        self._pipe.unload_textual_inversion(embedding.path)
        self._loaded_embeddings.remove(embedding.path)

    def _load_compel(self):
        if self.use_compel:
            try:
                self._load_textual_inversion_manager()
            except Exception as e:
                self.logger.error(
                    f"Error creating textual inversion manager: {e}"
                )

            try:
                self._load_compel_proc()
            except Exception as e:
                self.logger.error(f"Error creating compel proc: {e}")
        else:
            self._unload_compel()

    def _load_deep_cache(self):
        self._deep_cache_helper = DeepCacheSDHelper(pipe=self._pipe)
        self._deep_cache_helper.set_params(cache_interval=3, cache_branch_id=0)
        try:
            self._deep_cache_helper.enable()
        except AttributeError as e:
            self.logger.error(f"Failed to enable deep cache: {e}")

    def _load_textual_inversion_manager(self):
        self.logger.debug(
            "Loading safe textual inversion manager (caps token expansion at model max length)"
        )
        try:
            self._textual_inversion_manager = SafeDiffusersTextualInversionManager(
                self._pipe, logger=self.logger  # type: ignore[arg-type]
            )
        except Exception as e:
            # Fallback to upstream if something unexpected happens
            self.logger.error(
                f"Safe manager failed, falling back to upstream: {e}"
            )
            self._textual_inversion_manager = DiffusersTextualInversionManager(
                self._pipe
            )

    def _load_compel_proc(self):
        self.logger.debug("Loading compel proc")
        self._compel_proc = Compel(**self.compel_parameters)

    def _finalize_load_stable_diffusion(self):
        safety_checker_ready = True
        if self.use_safety_checker:
            safety_checker_ready = (
                self._safety_checker is not None
                and self._feature_extractor is not None
            )
        if self._pipe is not None and safety_checker_ready:
            self._current_state = HandlerState.READY
        else:
            self.logger.error(
                "Something went wrong with Stable Diffusion loading"
            )
            self.unload()
            self._clear_cached_properties()

        if (
            self.controlnet is not None
            and self.controlnet_processor is not None
            and self._pipe
        ):
            self._pipe.__controlnet = self.controlnet
            self._pipe.processor = self.controlnet_processor

    # MEMORY SETTINGS
    def _make_memory_efficient(self):
        self._current_memory_settings = self.memory_settings.to_dict()
        if not self._pipe:
            self.logger.error("Pipe is None, unable to apply memory settings")
            return

        # Apply all memory efficient settings using the helper method
        self._apply_memory_setting(
            "last_channels_applied",
            "use_last_channels",
            self._apply_last_channels,
        )
        self._apply_memory_setting(
            "vae_slicing_applied",
            "use_enable_vae_slicing",
            self._apply_vae_slicing,
        )
        self._apply_memory_setting(
            "attention_slicing_applied",
            "use_attention_slicing",
            self._apply_attention_slicing,
        )
        self._apply_memory_setting(
            "tiled_vae_applied", "use_tiled_vae", self._apply_tiled_vae
        )
        self._apply_memory_setting(
            "accelerated_transformers_applied",
            "use_accelerated_transformers",
            self._apply_accelerated_transformers,
        )
        self._apply_memory_setting(
            "cpu_offload_applied",
            "use_enable_sequential_cpu_offload",
            self._apply_cpu_offload,
        )
        self._apply_memory_setting(
            "model_cpu_offload_applied",
            "enable_model_cpu_offload",
            self._apply_model_offload,
        )
        self._apply_memory_setting(
            "tome_sd_applied", "use_tome_sd", self._apply_tome
        )

    def _apply_memory_setting(self, setting_name, attribute_name, apply_func):
        attr_val = getattr(self.memory_settings, attribute_name)
        if self._memory_settings_flags[setting_name] != attr_val:
            apply_func(attr_val)
            self._memory_settings_flags[setting_name] = attr_val

    def _apply_last_channels(self, attr_val):
        enabled = AIRUNNER_MEM_USE_LAST_CHANNELS
        if enabled is None:
            enabled = attr_val
        self.logger.debug(
            f"{'Enabling' if enabled else 'Disabling'} torch.channels_last"
        )
        self._pipe.unet.to(
            memory_format=(
                torch.channels_last if enabled else torch.contiguous_format
            )
        )

    def _apply_vae_slicing(self, attr_val):
        enabled = AIRUNNER_MEM_USE_ENABLE_VAE_SLICING
        if enabled is None:
            enabled = attr_val
        try:
            if enabled:
                self.logger.debug("Enabling vae slicing")
                self._pipe.enable_vae_slicing()
            else:
                self.logger.debug("Disabling vae slicing")
                self._pipe.disable_vae_slicing()
        except AttributeError as e:
            self.logger.error("Failed to apply vae slicing")
            self.logger.error(e)

    def _apply_attention_slicing(self, attr_val):
        enabled = AIRUNNER_MEM_USE_ATTENTION_SLICING
        if enabled is None:
            enabled = attr_val
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
        enabled = AIRUNNER_MEM_USE_TILED_VAE
        if enabled is None:
            enabled = attr_val
        try:
            if enabled:
                self.logger.debug("Enabling tiled vae")
                self._pipe.vae.enable_tiling()
            else:
                self.logger.debug("Disabling tiled vae")
                self._pipe.vae.disable_tiling()
        except AttributeError:
            self.logger.warning("Tiled vae not supported for this model")

    def _apply_accelerated_transformers(self, attr_val):
        enabled = AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS
        if enabled is None:
            enabled = attr_val

        if not is_ampere_or_newer(self._device_index):
            enabled = False

        from diffusers.models.attention_processor import (
            AttnProcessor,
            AttnProcessor2_0,
        )

        self.logger.debug(
            f"{'Enabling' if enabled else 'Disabling'} accelerated transformers"
        )
        self._pipe.unet.set_attn_processor(
            AttnProcessor2_0() if enabled else AttnProcessor()
        )

    def _apply_cpu_offload(self, attr_val):
        enabled = AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

        # Disable sequential CPU offload only for SDXL models when compel is enabled
        # due to compatibility issues with compel prompt processing and meta tensor handling
        if enabled and "SDXL" in self.version and self.use_compel:
            self.logger.warning(
                "Disabling sequential CPU offload for SDXL model with compel due to compatibility issues"
            )
            enabled = False

        if enabled and not self.memory_settings.enable_model_cpu_offload:
            self._pipe.to("cpu")
            try:
                self.logger.debug("Enabling sequential cpu offload")
                self._pipe.enable_sequential_cpu_offload(self._device_index)
            except NotImplementedError as e:
                self.logger.warning(
                    f"Error applying sequential cpu offload: {e}"
                )
                self._pipe.to(self._device)
        else:
            self.logger.debug("Sequential cpu offload disabled")

    def _apply_model_offload(self, attr_val):
        enabled = AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD
        if enabled is None:
            enabled = attr_val

        # Add warning for SDXL models with model CPU offload when using compel
        if enabled and "SDXL" in self.version and self.use_compel:
            self.logger.warning(
                "Model CPU offload with SDXL + compel may cause stability issues"
            )

        if (
            enabled
            and not self.memory_settings.use_enable_sequential_cpu_offload
        ):
            self.logger.debug("Enabling model cpu offload")
            # self._move_stable_diffusion_to_cpu()
            self._pipe.enable_model_cpu_offload(self._device_index)
        else:
            self.logger.debug("Model cpu offload disabled")

    def _apply_tome(self, attr_val):
        enabled = AIRUNNER_MEM_USE_TOME_SD
        if enabled is None:
            enabled = attr_val
        if enabled:
            ratio = AIRUNNER_MEM_TOME_SD_RATIO
            if ratio is None:
                ratio = self.memory_settings.tome_sd_ratio / 1000
            else:
                ratio = float(ratio)
            self.logger.debug(
                f"Applying ToMe SD weight merging with ratio {ratio}"
            )
            self._remove_tome_sd()
            try:
                tomesd.apply_patch(self._pipe, ratio=ratio)
            except Exception as e:
                self.logger.error(
                    f"Error applying ToMe SD weight merging: {e}"
                )
        else:
            self._remove_tome_sd()

    def _remove_tome_sd(self):
        self.logger.debug("Removing ToMe SD weight merging")
        try:
            tomesd.remove_patch(self._pipe)
        except Exception as e:
            self.logger.error(f"Error removing ToMe SD weight merging: {e}")

    # END MEMORY SETTINGS

    def _unload_safety_checker(self):
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)
        self._unload_safety_checker_model()
        self._unload_feature_extractor_model()
        self.change_model_status(
            ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED
        )

    def _unload_safety_checker_model(self):
        self.logger.debug("Unloading safety checker model")
        if self._pipe is not None and hasattr(self._pipe, "safety_checker"):
            del self._pipe.safety_checker
            self._pipe.safety_checker = None
        if self._safety_checker:
            try:
                self._safety_checker.to("cpu")
            except RuntimeError as e:
                self.logger.warning(
                    f"Failed to load model from {self.model_path}: {e}"
                )
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
        self.controlnet = None

    def _unload_controlnet_processor(self):
        model_loader.unload_controlnet_processor(
            self._controlnet_processor, self.logger
        )
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

    def _unload_textual_inversion(self):
        self.logger.info("Attempting to unload textual inversion")
        try:
            self._pipe.unload_textual_inversion()
            self.logger.info("Textual inversion unloaded")
        except Exception as e:
            self.logger.error(f"Failed to unload textual inversion: {e}")
            pass

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

    def _unload_generator(self):
        self.logger.debug("Unloading generator")
        del self._generator
        self._generator = None

    def _load_prompt_embeds(self):
        """
        Override this method to load the prompt embeds.
        """

    def _build_conditioning_tensors(
        self, compel_prompt, compel_negative_prompt
    ):
        prompt_embeds = self._compel_proc.build_conditioning_tensor(
            compel_prompt
        )
        negative_prompt_embeds = self._compel_proc.build_conditioning_tensor(
            compel_negative_prompt
        )
        return prompt_embeds, None, negative_prompt_embeds, None

    def _clear_memory_efficient_settings(self):
        self.logger.debug("Clearing memory efficient settings")
        for key in self._memory_settings_flags:
            if key.endswith("_applied"):
                self._memory_settings_flags[key] = None

    def _prepare_compel_data(self, data: Dict) -> Dict:
        data.update(
            {
                "prompt_embeds": self._prompt_embeds,
                "negative_prompt_embeds": self._negative_prompt_embeds,
            }
        )
        return data

    def _prepare_data(self, active_rect=None) -> Dict:
        """
        Here we are loading the arguments for the Stable Diffusion generator.
        :return:
        """
        self.logger.debug("Preparing data")
        self._set_seed()

        data = {
            "width": int(self.application_settings.working_width),
            "height": int(self.application_settings.working_height),
            "clip_skip": int(self.image_request.clip_skip),
            "num_inference_steps": int(self.image_request.steps),
            "callback_on_step_end": self.__interrupt_callback,
            "generator": self.generator,
            # Use 1 as default if images_per_batch is None
            "num_images_per_prompt": (
                int(self.image_request.images_per_batch)
                if self.image_request.images_per_batch is not None
                else 1
            ),
        }

        if len(self._loaded_lora) > 0:
            data["cross_attention_kwargs"] = {"scale": self.lora_scale}
            self._set_lora_adapters()

        if self.use_compel:
            data = self._prepare_compel_data(data)

        else:
            data.update(
                {
                    "prompt": self.prompt,
                    "negative_prompt": self.negative_prompt,
                }
            )

        width = int(self.application_settings.working_width)
        height = int(self.application_settings.working_height)
        image = None
        mask = None

        if self.is_txt2img or self.is_outpaint or self.is_img2img:
            data.update({"width": width, "height": height})

        if self.is_img2img:
            image = self.img2img_image
            if (
                data["num_inference_steps"]
                < AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
            ):
                data["num_inference_steps"] = (
                    AIRUNNER_MIN_NUM_INFERENCE_STEPS_IMG2IMG
                )
        elif self.is_inpaint:
            image = self.img2img_image_cached or self.drawing_pad_image
            mask = self.drawing_pad_mask
            if not image:
                raise ValueError("No image provided for inpainting")
            if not mask:
                raise ValueError("No mask provided for inpainting")
        elif self.is_outpaint:
            image = self.outpaint_image
            if not image:
                image = self.drawing_pad_image
            mask = self.drawing_pad_mask

            # Crop the image based on the active grid location
            active_grid_x = active_rect.left()
            active_grid_y = active_rect.top()
            cropped_image = image.crop(
                (
                    active_grid_x,
                    active_grid_y,
                    width + active_grid_x,
                    height + active_grid_y,
                )
            )

            # Create a new image with a black strip at the bottom
            new_image = PIL.Image.new("RGBA", (width, height), (0, 0, 0, 255))
            new_image.paste(cropped_image, (0, 0))
            image = new_image.convert("RGB")

        data["guidance_scale"] = self.image_request.scale

        # set the image to controlnet image if controlnet is enabled
        if self.controlnet_enabled:
            controlnet_image = self.controlnet_image
            if controlnet_image:
                controlnet_image = self._resize_image(
                    controlnet_image, width, height
                )
                control_image = self._controlnet_processor(
                    controlnet_image,
                    to_pil=True,
                    image_resolution=min(width, height),
                    detect_resolution=min(width, height),
                )
                if control_image is not None:
                    self.update_controlnet_settings(
                        generated_image=convert_image_to_binary(control_image),
                    )
                    if self.is_txt2img:
                        image = control_image
                    else:
                        data["control_image"] = control_image
                else:
                    raise ValueError("Controlnet image is None")

        if image is not None:
            image = self._resize_image(image, width, height)
            data["image"] = image

        if mask is not None and (self.is_outpaint or self.is_inpaint):
            mask = self._resize_image(mask, width, height)
            if self.is_outpaint:
                mask = self._pipe.mask_processor.blur(
                    mask, blur_factor=self.mask_blur
                )
            data["mask_image"] = mask

        if self.controlnet_enabled:
            data.update(
                {
                    "guess_mode": False,
                    "control_guidance_start": 0.0,
                    "control_guidance_end": 1.0,
                    "strength": self.controlnet_strength / 100.0,
                    "guidance_scale": self.image_request.scale,
                    "controlnet_conditioning_scale": self.controlnet_conditioning_scale
                    / 100.0,
                }
            )
        elif self.is_inpaint:
            data.update(
                {
                    "strength": self.outpaint_settings.strength / 100.0,
                }
            )
        elif self.is_outpaint:
            data.update(
                {
                    "strength": self.outpaint_settings.strength / 100.0,
                }
            )
        elif self.is_img2img:
            data.update(
                {
                    "strength": self.image_to_image_settings.strength / 100.0,
                }
            )
        return data

    @staticmethod
    def _resize_image(
        image: Image, max_width: int, max_height: int
    ) -> Optional[Image]:
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
        resized_image = image.resize(
            (new_width, new_height), PIL.Image.Resampling.LANCZOS
        )
        return resized_image

    def _set_seed(self):
        seed = self.image_request.seed
        self.generator.manual_seed(seed)

    def _callback(self, _pipe, _i, _t, callback_kwargs):
        self.api.art.progress_update(step=_i, total=self.image_request.steps)
        return callback_kwargs

    def __interrupt_callback(self, _pipe, _i, _t, callback_kwargs):
        if self.do_interrupt_image_generation:
            self.do_interrupt_image_generation = False
            raise InterruptedException()
        else:
            self._callback(_pipe, _i, _t, callback_kwargs)
        return callback_kwargs
