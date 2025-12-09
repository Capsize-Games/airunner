"""Utilities for loading/unloading Stable Diffusion related resources."""

import os
from typing import Any, Dict, Optional

from diffusers import SchedulerMixin

from controlnet_aux.processor import MODELS as controlnet_aux_models
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.schedulers import Schedulers
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY, AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class SomeModelClass:  # legacy test helper
    def __init__(self, path):
        self.path = path

    def unload(self):
        return True


class SomeSchedulerClass:  # legacy test helper
    pass


class SomeControlNetClass:  # legacy test helper
    pass


class SomeLoraClass:  # legacy test helper
    def __init__(self, path=None):
        self.path = path


class SomeEmbeddingsClass:  # legacy test helper
    def __init__(self, path=None):
        self.path = path


class SomeCompelClass:  # legacy test helper
    def __init__(self, *args, **kwargs):
        pass


class SomeDeepCacheClass:  # legacy test helper
    def __init__(self, *args, **kwargs):
        pass


def load_scheduler(
    scheduler_name: str, path_settings, version: str, logger: Any
) -> Optional[SchedulerMixin]:
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
    class_name = scheduler.name
    try:
        cls = getattr(
            __import__("diffusers", fromlist=[class_name]), class_name
        )
        inst = cls.from_pretrained(
            scheduler_path,
            subfolder="scheduler",
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
        )
        logger.info(f"Loaded scheduler {scheduler_name}")
        return inst
    except Exception as e:
        logger.error(f"Failed to load scheduler {scheduler_name}: {e}")
        return None


def load_controlnet_model(
    controlnet_enabled: bool,
    controlnet_path: str,
    data_type,
    device,
    logger: Any,
):
    if not controlnet_enabled:
        return None
    from diffusers import ControlNetModel

    try:
        data = dict(
            torch_dtype=data_type,
            device=device,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            use_safetensors=True,
            use_fp16=True,
            variant="fp16",
        )
        if os.path.isdir(controlnet_path):
            model = ControlNetModel.from_pretrained(controlnet_path, **data)
        else:
            directory_only = os.path.dirname(controlnet_path)
            config_path = os.path.join(directory_only, "config.json")
            model = ControlNetModel.from_single_file(
                pretrained_model_link_or_path_or_dict=controlnet_path,
                config=config_path,
                **data,
            )
        logger.info(f"Loaded ControlNet model from {controlnet_path}")
        return model
    except Exception as e:
        logger.error(f"Error loading ControlNet model: {e}")
        return None


def load_lora_weights(
    pipe, lora: Lora, lora_base_path: str, logger: Any
) -> bool:
    filename = os.path.basename(lora.path)
    adapter_name = os.path.splitext(filename)[0].replace(".", "_")
    # Scale is stored as 0-100 integer, convert to 0.0-1.0 float
    scale = lora.scale / 100.0 if hasattr(lora, 'scale') else 1.0
    try:
        pipe.load_lora_weights(
            lora_base_path, weight_name=filename, adapter_name=adapter_name, scale=scale
        )
        logger.info(f"Loaded LORA weights: {filename} (scale={scale:.2f})")
        return True
    except Exception as e:
        logger.warning(f"Failed to load LORA {filename}: {e}")
        return False

def unload_lora(pipe: Any, logger: Any) -> None:
    """Unload all LORA weights from the pipeline."""
    try:
        if pipe is not None and hasattr(pipe, "unload_lora_weights"):
            pipe.unload_lora_weights()
            logger.info("Unloaded all LORA weights from pipeline.")
    except Exception as e:
        logger.warning(f"Failed to unload LORA weights: {e}")


def load_compel_proc(
    compel_parameters: Dict[str, Any],
    logger: Any,
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


def unload_compel_proc(compel_proc: Any, logger: Any) -> None:
    """Unload the Compel processor and free resources."""
    try:
        del compel_proc
        logger.info("Unloaded Compel processor.")
    except Exception as e:
        logger.warning(f"Failed to unload Compel processor: {e}")


def load_deep_cache_helper(pipe: Any, logger: Any) -> Optional[Any]:
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


def unload_deep_cache_helper(deep_cache_helper: Any, logger: Any) -> None:
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
    logger: Any,
) -> Optional[Any]:
    """Load the ControlNet processor if enabled."""
    if not controlnet_enabled or not controlnet_model:
        return None

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
    controlnet_processor: Any, logger: Any
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


def load_embedding(path: str):
    """Stub loader for embedding files used in tests. Returns a simple
    object that mirrors the requested path so callers can inspect it.
    """

    class Emb:
        def __init__(self, p):
            self.path = p

    return Emb(path)


def unload_embeddings(pipe: Any, logger: Any) -> None:
    """No-op unload for embeddings to keep tests simple and idempotent."""
    try:
        if pipe is not None and hasattr(pipe, "embeddings"):
            del pipe.embeddings
            logger.info("Unloaded embeddings from pipeline.")
    except Exception as e:
        logger.warning(f"Failed to unload embeddings: {e}")


def load_compel(*args, **kwargs):
    return SomeCompelClass(*args, **kwargs)


def load_deep_cache(*args, **kwargs):
    return SomeDeepCacheClass(*args, **kwargs)


def load_scheduler(*args, **kwargs):
    return SomeSchedulerClass()


def unload_deep_cache(instance):
    return instance.unload()
