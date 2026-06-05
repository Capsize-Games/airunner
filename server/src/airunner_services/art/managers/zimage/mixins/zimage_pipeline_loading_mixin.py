"""Z-Image pipeline loading mixin."""

import gc
from typing import Any, Dict, Optional

import torch

from airunner_services.art.managers.zimage.mixins.zimage_pretrained_loader_helper import (
    ZImagePretrainedLoaderHelper,
)
from airunner_services.art.managers.zimage.mixins.zimage_bundle_helper import (
    ZImageBundleHelper,
)
from airunner_services.art.managers.zimage.mixins.zimage_single_file_loader_helper import (
    ZImageSingleFileLoaderHelper,
)
from airunner_services.art.managers.zimage.mixins.zimage_runtime_loader_helper import (
    ZImageRuntimeLoaderHelper,
)
from airunner_services.art.managers.zimage.mixins.zimage_pipeline_lifecycle_helper import (
    ZImagePipelineLifecycleHelper,
)


def _clear_gpu_memory() -> None:
    """Aggressively clear GPU memory."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    gc.collect()


class ZImagePipelineLoadingMixin:
    """Mixin for Z-Image pipeline loading operations.

    Overrides the base _set_pipe method to handle Z-Image's specific
    requirements for loading from single-file checkpoints, particularly
    the need to load the text encoder separately.
    """

    def _get_pretrained_loader_helper(self) -> ZImagePretrainedLoaderHelper:
        """Return the cached pretrained loader helper."""
        helper = getattr(self, "_pretrained_loader_helper", None)
        if helper is None:
            helper = ZImagePretrainedLoaderHelper(self)
            self._pretrained_loader_helper = helper
        return helper

    def _get_bundle_helper(self) -> ZImageBundleHelper:
        """Return the cached bundle helper."""
        helper = getattr(self, "_bundle_helper", None)
        if helper is None:
            helper = ZImageBundleHelper(self)
            self._bundle_helper = helper
        return helper

    def _get_single_file_loader_helper(self) -> ZImageSingleFileLoaderHelper:
        """Return the cached single-file loader helper."""
        helper = getattr(self, "_single_file_loader_helper", None)
        if helper is None:
            helper = ZImageSingleFileLoaderHelper(self)
            self._single_file_loader_helper = helper
        return helper

    def _get_runtime_loader_helper(self) -> ZImageRuntimeLoaderHelper:
        """Return the cached runtime loader helper."""
        helper = getattr(self, "_runtime_loader_helper", None)
        if helper is None:
            helper = ZImageRuntimeLoaderHelper(self)
            self._runtime_loader_helper = helper
        return helper

    def _get_lifecycle_helper(self) -> ZImagePipelineLifecycleHelper:
        """Return the cached pipeline lifecycle helper."""
        helper = getattr(self, "_lifecycle_helper", None)
        if helper is None:
            helper = ZImagePipelineLifecycleHelper(self)
            self._lifecycle_helper = helper
        return helper

    def _clear_gpu_memory(self) -> None:
        """Clear GPU memory through the module-level helper."""
        _clear_gpu_memory()

    def _check_and_trigger_download(self) -> tuple[bool, dict]:
        """Check Z-Image files against the active runtime mode."""
        return self._get_bundle_helper().check_and_trigger_download()

    def _set_pipe(self, config_path: str, data: Dict):
        """Load Z-Image pipeline from the selected model file."""
        self._get_lifecycle_helper().set_pipe(config_path, data)

    def _load_from_pretrained(
        self, model_path: str, pipeline_class: Any, data: Dict
    ):
        """Load Z-Image from one pretrained directory."""
        self._get_pretrained_loader_helper().load_from_pretrained(
            model_path,
            pipeline_class,
            data,
        )

    def _load_from_single_file(
        self,
        model_path: str,
        pipeline_class: Any,
        data: Dict,
        *,
        is_fp8_checkpoint: Optional[bool] = None,
    ):
        """Load Z-Image from one single safetensors checkpoint."""
        self._get_single_file_loader_helper().load_from_single_file(
            model_path,
            pipeline_class,
            data,
            is_fp8_checkpoint=is_fp8_checkpoint,
        )

    def _verify_pipeline_loaded(self) -> bool:
        """Verify that the pipeline was loaded correctly."""
        return self._get_lifecycle_helper().verify_pipeline_loaded()

    def _swap_pipeline(self):
        """Swap between Z-Image pipeline types."""
        self._get_lifecycle_helper().swap_pipeline()
