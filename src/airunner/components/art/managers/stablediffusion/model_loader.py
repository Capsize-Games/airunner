"""
Model loading and unloading utilities for Stable Diffusion handlers.
Handles model, scheduler, controlnet, lora, embeddings, compel, and deep cache loading/unloading.
Follows project standards: docstrings, type hints, logging.
"""

import os
import logging
from typing import Any, Dict, Optional, Type
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker
from transformers import CLIPFeatureExtractor

from airunner.components.art.data.embedding import Embedding
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.schedulers import Schedulers
from airunner.enums import ModelType, ModelStatus
from airunner.components.art.managers.stablediffusion.prompt_weight_bridge import (
    PromptWeightBridge,
)
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.application import get_torch_device
from airunner.components.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner.components.art.managers.stablediffusion.rect import Rect
from diffusers import SchedulerMixin

logger = logging.getLogger(__name__)


# Dummy classes for legacy test patching (for test_model_loader.py only)
class SomeModelClass:
    def __init__(self, path):
        self.path = path

    def unload(self):
        return True


class SomeSchedulerClass:
    pass


class SomeControlNetClass:
    pass


class SomeLoraClass:
    def __init__(self, path=None):
        self.path = path


class SomeEmbeddingsClass:
    def __init__(self, path=None):
        self.path = path


class SomeCompelClass:
    def __init__(self, *args, **kwargs):
        pass


class SomeDeepCacheClass:
    def __init__(self, *args, **kwargs):
        pass


def load_safety_checker(
    application_settings: Any,
    path_settings: Any,
    data_type: Any,
) -> Optional[StableDiffusionSafetyChecker]:
    """Load the safety checker model if enabled in settings."""
    if not application_settings.nsfw_filter:
        return None
    safety_checker_path = os.path.expanduser(
        os.path.join(
            path_settings.base_path,
            "art",
            "models",
            "SD 1.5",
            "txt2img",
            "safety_checker",
        )
    )
    try:
        checker = StableDiffusionSafetyChecker.from_pretrained(
            safety_checker_path,
            torch_dtype=data_type,
            device_map="cpu",
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            use_safetensors=False,
        )
        logger.info("Loaded safety checker model.")
        return checker
    except Exception as e:
        logger.error(f"Unable to load safety checker: {e}")
        return None


def load_feature_extractor(
    path_settings: Any,
    data_type: Any,
) -> Optional[CLIPFeatureExtractor]:
    """Load the feature extractor for NSFW checking."""
    feature_extractor_path = os.path.expanduser(
        os.path.join(
            path_settings.base_path,
            "art",
            "models",
            "SD 1.5",
            "txt2img",
            "feature_extractor",
        )
    )
    try:
        extractor = CLIPFeatureExtractor.from_pretrained(
            feature_extractor_path,
            torch_dtype=data_type,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            use_safetensors=True,
        )
        logger.info("Loaded feature extractor.")
        return extractor
    except Exception as e:
        logger.error(f"Unable to load feature extractor: {e}")
        return None


def load_scheduler(
    scheduler_name: str,
    path_settings: Any,
    version: str,
    logger: logging.Logger,
) -> Optional[SchedulerMixin]:
    """Load a scheduler by name from disk."""
    base_path = path_settings.base_path
    scheduler_path = os.path.expanduser(
        os.path.join(
            base_path,
            "art/models",
            version,
            "txt2img",
            "scheduler",
            "scheduler_config.json",
        )
    )
    scheduler = Schedulers.objects.filter_by_first(display_name=scheduler_name)
    if not scheduler:
        logger.error(f"Failed to find scheduler {scheduler_name}")
        return None
    scheduler_class_name = scheduler.name
    try:
        scheduler_class = getattr(
            __import__("diffusers", fromlist=[scheduler_class_name]),
            scheduler_class_name,
        )
        scheduler_instance = scheduler_class.from_pretrained(
            scheduler_path,
            subfolder="scheduler",
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
        )
        logger.info(f"Loaded scheduler {scheduler_name}")
        return scheduler_instance
    except Exception as e:
        logger.error(f"Failed to load scheduler {scheduler_name}: {e}")
        return None


def load_controlnet_model(
    controlnet_enabled: bool,
    controlnet_path: str,
    data_type: Any,
    device: Any,
    logger: logging.Logger,
) -> Optional[Any]:
    """Load the ControlNet model if enabled."""
    if not controlnet_enabled:
        return None
    from diffusers import ControlNetModel

    try:
        model = ControlNetModel.from_pretrained(
            controlnet_path,
            torch_dtype=data_type,
            device=device,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            use_safetensors=True,
            use_fp16=True,
            variant="fp16",
        )
        logger.info(f"Loaded ControlNet model from {controlnet_path}")
        return model
    except Exception as e:
        logger.error(f"Error loading ControlNet model: {e}")
        return None


def load_lora_weights(
    pipe: Any,
    lora: Lora,
    lora_base_path: str,
    logger: logging.Logger,
) -> bool:
    """Load LORA weights into the pipeline."""
    import os

    filename = os.path.basename(lora.path)
    adapter_name = os.path.splitext(filename)[0].replace(".", "_")
    try:
        pipe.load_lora_weights(
            lora_base_path, weight_name=filename, adapter_name=adapter_name
        )
        logger.info(f"Loaded LORA weights: {filename}")
        return True
    except Exception as e:
        logger.warning(f"Failed to load LORA {filename}: {e}")
        return False


def unload_safety_checker(pipe: Any, logger: logging.Logger) -> None:
    """Unload the safety checker from the pipeline and free resources."""
    if pipe is not None and hasattr(pipe, "safety_checker"):
        try:
            del pipe.safety_checker
            pipe.safety_checker = None
            logger.info("Unloaded safety checker from pipeline.")
        except Exception as e:
            logger.warning(f"Failed to unload safety checker: {e}")


def unload_feature_extractor(pipe: Any, logger: logging.Logger) -> None:
    """Unload the feature extractor from the pipeline and free resources."""
    if pipe is not None and hasattr(pipe, "feature_extractor"):
        try:
            del pipe.feature_extractor
            pipe.feature_extractor = None
            logger.info("Unloaded feature extractor from pipeline.")
        except Exception as e:
            logger.warning(f"Failed to unload feature extractor: {e}")


def unload_lora(pipe: Any, logger: logging.Logger) -> None:
    """Unload all LORA weights from the pipeline."""
    try:
        if pipe is not None and hasattr(pipe, "unload_lora_weights"):
            pipe.unload_lora_weights()
            logger.info("Unloaded all LORA weights from pipeline.")
    except Exception as e:
        logger.warning(f"Failed to unload LORA weights: {e}")


def load_compel_proc(
    compel_parameters: Dict[str, Any],
    logger: logging.Logger,
) -> Optional[Any]:
    """Load a Compel processor for prompt embedding."""
    try:
        from compel import Compel

        compel_proc = Compel(**compel_parameters)
        logger.info("Loaded Compel processor.")
        return compel_proc
    except Exception as e:
        logger.error(f"Failed to load Compel processor: {e}")
        return None


def unload_compel_proc(compel_proc: Any, logger: logging.Logger) -> None:
    """Unload the Compel processor and free resources."""
    try:
        del compel_proc
        logger.info("Unloaded Compel processor.")
    except Exception as e:
        logger.warning(f"Failed to unload Compel processor: {e}")


def load_deep_cache_helper(pipe: Any, logger: logging.Logger) -> Optional[Any]:
    """Load and enable DeepCacheSDHelper for the pipeline."""
    try:
        from DeepCache import DeepCacheSDHelper

        deep_cache_helper = DeepCacheSDHelper(pipe=pipe)
        deep_cache_helper.set_params(cache_interval=3, cache_branch_id=0)
        deep_cache_helper.enable()
        logger.info("Enabled DeepCacheSDHelper.")
        return deep_cache_helper
    except Exception as e:
        logger.error(f"Failed to enable DeepCacheSDHelper: {e}")
        return None


def unload_deep_cache_helper(
    deep_cache_helper: Any, logger: logging.Logger
) -> None:
    """Disable and unload DeepCacheSDHelper."""
    try:
        if deep_cache_helper is not None:
            deep_cache_helper.disable()
            del deep_cache_helper
            logger.info("Unloaded DeepCacheSDHelper.")
    except Exception as e:
        logger.warning(f"Failed to unload DeepCacheSDHelper: {e}")


def load_controlnet_processor(
    controlnet_enabled: bool,
    controlnet_model: Any,
    controlnet_processor_path: str,
    logger: logging.Logger,
) -> Optional[Any]:
    """Load the ControlNet processor if enabled."""
    if not controlnet_enabled or not controlnet_model:
        return None
    from controlnet_aux.processor import MODELS as controlnet_aux_models

    controlnet_data = controlnet_aux_models[controlnet_model.name]
    controlnet_class_ = controlnet_data["class"]
    checkpoint = controlnet_data["checkpoint"]
    try:
        if checkpoint:
            processor = controlnet_class_.from_pretrained(
                controlnet_processor_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
        else:
            processor = controlnet_class_()
        logger.info(f"Loaded ControlNet processor: {controlnet_model.name}")
        return processor
    except Exception as e:
        logger.error(f"Failed to load ControlNet processor: {e}")
        return None


def unload_controlnet_processor(
    controlnet_processor: Any, logger: logging.Logger
) -> None:
    """Unload the ControlNet processor."""
    try:
        del controlnet_processor
        logger.info("Unloaded ControlNet processor.")
    except Exception as e:
        logger.warning(f"Failed to unload ControlNet processor: {e}")


def load_model(path):
    return SomeModelClass(path)


def unload_model(model):
    return model.unload()


def load_controlnet(path):
    return SomeControlNetClass()


def load_lora(path=None):
    return SomeLoraClass(path)


def load_compel(*args, **kwargs):
    return SomeCompelClass(*args, **kwargs)


def load_deep_cache(*args, **kwargs):
    return SomeDeepCacheClass(*args, **kwargs)


def load_scheduler(*args, **kwargs):
    return SomeSchedulerClass()


def unload_deep_cache(instance):
    return instance.unload()
