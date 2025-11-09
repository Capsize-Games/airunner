import os
from typing import Any, List, Dict, Optional

import torch
from compel import (
    DiffusersTextualInversionManager,
)

from airunner.components.art.data.lora import Lora
from airunner.components.art.utils.model_file_checker import (
    ModelFileChecker,
)
from airunner.components.art.workers.image_export_worker import (
    ImageExportWorker,
)
from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.enums import (
    ModelStatus,
    ModelType,
    HandlerState,
    ModelAction,
    SignalCode,
)
from airunner.utils.application.create_worker import create_worker
from airunner.utils.memory import clear_memory

from airunner.components.art.managers.stablediffusion import (
    image_generation,
    utils,
)
from airunner.components.art.managers.stablediffusion.mixins import (
    SDPropertiesMixin,
    SDPipelineManagementMixin,
    SDModelLoadingMixin,
    SDModelUnloadingMixin,
    SDMemoryManagementMixin,
    SDGenerationPreparationMixin,
    SDImageGenerationMixin,
)


class BaseDiffusersModelManager(
    BaseModelManager,
    SDPropertiesMixin,
    SDPipelineManagementMixin,
    SDModelLoadingMixin,
    SDModelUnloadingMixin,
    SDMemoryManagementMixin,
    SDGenerationPreparationMixin,
    SDImageGenerationMixin,
):
    """
    Base manager for Stable Diffusion models using diffusers library.

    This class coordinates the loading, configuration, and generation of
    images using Stable Diffusion pipelines. Functionality is organized
    into focused mixins for maintainability.

    Mixins:
        SDPropertiesMixin: Property accessors for all model components
        SDPipelineManagementMixin: Pipeline swapping and management
        SDModelLoadingMixin: Loading all model components
        SDModelUnloadingMixin: Unloading all model components
        SDMemoryManagementMixin: VRAM optimization strategies
        SDGenerationPreparationMixin: Data preparation for generation
        SDImageGenerationMixin: Image generation loop and callbacks
    """

    model_type: ModelType = ModelType.SD
    _model_status = {
        ModelType.SAFETY_CHECKER: ModelStatus.UNLOADED,
        ModelType.CONTROLNET: ModelStatus.UNLOADED,
        ModelType.LORA: ModelStatus.UNLOADED,
        ModelType.EMBEDDINGS: ModelStatus.UNLOADED,
    }

    def __init__(self, *args, **kwargs):
        self._scheduler = None
        super().__init__(*args, **kwargs)
        self._initialize_model_status()
        self._pipeline: Optional[str] = None
        self._scheduler_name: Optional[str] = None
        self.current_scheduler_name: str = ""
        self.do_change_scheduler: bool = False
        self._resolved_model_version: Optional[str] = None
        self._image_request = None
        self._controlnet_model = None
        self._controlnet: Optional = None
        self._controlnet_processor: Any = None
        self._safety_checker: Optional = None
        self._feature_extractor: Optional = None
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
        self._compel_proc: Optional = None
        self._loaded_lora: Dict = {}
        self._disabled_lora: List = []
        self._loaded_embeddings: List = []
        self._current_state: HandlerState = HandlerState.UNINITIALIZED
        self._deep_cache_helper: Optional = None
        self.do_interrupt_image_generation: bool = False

        # Cached properties from database
        self._outpaint_image = None
        self._img2img_image = None
        self._controlnet_settings = None
        self._controlnet_image_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None
        self._current_memory_settings = None

        self.image_export_worker = create_worker(ImageExportWorker)

    def _initialize_model_status(self):
        """Initialize model status for this manager's model type."""
        self._model_status[self.model_type] = ModelStatus.UNLOADED

    def settings_changed(self, data: Dict):
        """
        Handle settings changes.

        Args:
            data: Dictionary containing updated settings including image_request
        """
        self.image_request = data.get("image_request", self.image_request)
        if self._pipe and self._pipe.__class__ is not self._pipeline_class:
            self._swap_pipeline()

    @property
    def img2img_pipelines(self) -> List[Any]:
        """Return list of img2img pipeline classes (overridden in subclasses)."""
        return []

    @property
    def txt2img_pipelines(self) -> List[Any]:
        """Return list of txt2img pipeline classes (overridden in subclasses)."""
        return []

    @property
    def controlnet_pipelines(self) -> List[Any]:
        """Return list of controlnet pipeline classes (overridden in subclasses)."""
        return []

    @property
    def outpaint_pipelines(self) -> List[Any]:
        """Return list of outpaint pipeline classes (overridden in subclasses)."""
        return []

    @property
    def use_compel(self) -> bool:
        """Get whether to use Compel for prompt weighting.

        Returns:
            True if Compel should be used for prompt processing.
        """
        if self.image_request:
            return self.image_request.use_compel
        return True  # Default to True if no image_request

    def _get_scheduler_base_config(
        self, scheduler_class
    ) -> Optional[Dict[str, Any]]:
        """Get base configuration for a scheduler from the current pipeline.

        Args:
            scheduler_class: The scheduler class to get config for

        Returns:
            Dictionary with scheduler config or None if not available
        """
        if (
            self._pipe
            and hasattr(self._pipe, "scheduler")
            and self._pipe.scheduler
        ):
            return self._pipe.scheduler.config
        return None

    def reload(self):
        """Reload the model by unloading and loading again."""
        self.logger.debug("Reloading stable diffusion")
        self._clear_cached_properties()
        self.unload()
        self.load()

    def load(self):
        """
        Load the Stable Diffusion model and all components.

        Coordinates loading of:
        - Safety checker
        - ControlNet (if enabled)
        - Main pipeline
        - Scheduler
        - LoRA weights
        - Embeddings
        - Compel processor
        - DeepCache helper
        - Memory optimizations
        """
        if self.sd_is_loading or self.model_is_loaded:
            return
        if self.model_path is None or self.model_path == "":
            self.logger.error("No model selected")
            self.change_model_status(self.model_type, ModelStatus.FAILED)
            return

        # Check for missing files and trigger download if needed
        should_download, download_info = self._check_and_trigger_download()
        if should_download:
            # Download in progress, will retry load after completion
            return

        # Integrate with ModelResourceManager
        from airunner.components.model_management import ModelResourceManager

        resource_manager = ModelResourceManager()
        prepare_result = resource_manager.prepare_model_loading(
            model_id=self.model_path,
            model_type="text_to_image",
        )

        if not prepare_result["can_load"]:
            self.logger.error(
                f"Cannot load SD model: {prepare_result.get('reason', 'Unknown reason')}"
            )
            self.change_model_status(self.model_type, ModelStatus.FAILED)
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

            # Mark model as loaded
            resource_manager.model_loaded(self.model_path)

    def load_controlnet(self):
        """
        Load ControlNet model if enabled.

        Public method to load ControlNet model and processor.
        Skips loading if ControlNet is not enabled or already loading.
        """
        if not self.controlnet_enabled or self.controlnet_is_loading:
            return

        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)
        try:
            self._load_controlnet_model()
            self._load_controlnet_processor()
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADED)
        except Exception as e:
            self.logger.error(f"Failed to load ControlNet: {e}", exc_info=True)
            self.change_model_status(ModelType.CONTROLNET, ModelStatus.FAILED)

    def unload(self):
        """
        Unload the Stable Diffusion model and all components.

        Performs ordered unloading to minimize memory usage:
        1. Lightweight components (DeepCache, Compel, embeddings, scheduler)
        2. GPU components (LoRA, ControlNet, safety checker)
        3. Main pipeline
        4. Generator

        Includes aggressive memory clearing between steps.
        """
        if self.sd_is_loading or self.sd_is_unloaded:
            return
        elif self._current_state in (
            HandlerState.PREPARING_TO_GENERATE,
            HandlerState.GENERATING,
        ):
            self.interrupt_image_generation()
            self.requested_action = ModelAction.CLEAR
        self.change_model_status(self.model_type, ModelStatus.LOADING)

        # Unload lightweight components first
        self._unload_deep_cache()
        self._unload_compel()
        self._unload_emebeddings()
        self._unload_scheduler()

        # Unload heavier GPU components
        self._unload_loras()
        self._unload_controlnet()
        self._unload_safety_checker()

        # Clear memory after unloading auxiliary models
        clear_memory(self._device_index)

        # Unload the main pipeline (largest component)
        self._unload_pipe()

        # Aggressive clear after pipe unload
        clear_memory(self._device_index)

        # Unload generator after pipe
        self._unload_generator()

        self._send_pipeline_loaded_signal()
        self._clear_memory_efficient_settings()

        # Final memory clear to ensure everything is released
        clear_memory(self._device_index)

        self.change_model_status(self.model_type, ModelStatus.UNLOADED)

        # Cleanup via ModelResourceManager
        from airunner.components.model_management import ModelResourceManager

        resource_manager = ModelResourceManager()
        resource_manager.model_unloaded(self.model_path)

    def reload_lora(self):
        """Reload LoRA weights without reloading the entire model."""
        if self.model_status[
            self.model_type
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
        """Reload embeddings without reloading the entire model."""
        if self.model_status[
            self.model_type
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
        """Load embeddings (wrapper for mixin method)."""
        self._load_embeddings()

    def _clear_cached_properties(self):
        """Clear cached database-backed properties."""
        self._outpaint_image = None
        self._img2img_image = None
        self._controlnet_settings = None
        self._controlnet_image_settings = None
        self._application_settings = None
        self._drawing_pad_settings = None
        self._outpaint_settings = None
        self._path_settings = None

    def _check_and_mark_nsfw_images(self, images):
        """
        Check images for NSFW content using safety checker.

        Args:
            images: List of PIL images to check

        Returns:
            Tuple of (processed_images, nsfw_detected_flags)
        """
        return image_generation.check_and_mark_nsfw_images(
            images, self._feature_extractor, self._safety_checker, self._device
        )

    def _resize_image(self, image, max_width, max_height):
        """
        Resize image maintaining aspect ratio.

        Args:
            image: PIL Image to resize
            max_width: Maximum width
            max_height: Maximum height

        Returns:
            Resized PIL Image
        """
        return utils.resize_image(image, max_width, max_height)

    def _prepare_pipe_data(self) -> Dict[str, Any]:
        """
        Prepare data dictionary for pipeline loading.

        Returns:
            Dictionary with torch_dtype, safetensors flags, device, and
            optional controlnet configuration
        """
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

        return data

    def _load_pipe(self) -> bool:
        """
        Load the main diffusers pipeline.

        Returns:
            True if loaded successfully, False otherwise
        """
        self.logger.debug(
            f"Loading pipe {self._pipeline_class} for {self.section}"
        )
        self.change_model_status(self.model_type, ModelStatus.LOADING)
        data = self._prepare_pipe_data()

        try:
            self._set_pipe(self.config_path, data)
            self.change_model_status(self.model_type, ModelStatus.LOADED)

            # Notify ModelResourceManager that model loaded successfully
            from airunner.components.model_management import (
                ModelResourceManager,
            )

            resource_manager = ModelResourceManager()
            resource_manager.model_loaded(self.model_path)
        except Exception as e:
            self.logger.error(f"Failed to load pipe: {e}")
            self.change_model_status(self.model_type, ModelStatus.FAILED)
            return False
        return True

    def _set_lora_adapters(self):
        """Configure LoRA adapter weights and names on the pipeline."""
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

    def _finalize_load_stable_diffusion(self):
        """
        Finalize Stable Diffusion loading after all components are ready.

        Verifies all required components are loaded and sets handler state
        to READY. Attaches ControlNet processor to pipeline if enabled.
        """
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

    def _check_and_trigger_download(self) -> tuple:
        """Check for missing model files and trigger download if needed.

        Returns:
            Tuple of (should_wait_for_download, download_info)
        """
        # Get model version and pipeline action from settings
        version = getattr(self, "version", None)
        pipeline_action = getattr(self, "pipeline_action", "txt2img")

        if not version:
            # Can't check without version info
            return False, {}

        # Check if files are missing
        should_download, download_info = (
            ModelFileChecker.should_trigger_download(
                model_path=self.model_path,
                model_type="art",
                version=version,
                pipeline_action=pipeline_action,
            )
        )

        if not should_download:
            if "error" in download_info:
                self.logger.error(
                    f"Model files missing: {download_info.get('error')}"
                )
            return False, download_info

        # Files are missing and we have a HuggingFace repo ID
        repo_id = download_info.get("repo_id")
        missing_files = download_info.get("missing_files", [])

        self.logger.info(
            f"Missing {len(missing_files)} files for {repo_id}, triggering download"
        )
        self.logger.debug(f"Missing files: {missing_files}")

        # Emit signal to trigger download dialog
        self.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            {
                "repo_id": repo_id,
                "model_path": self.model_path,
                "missing_files": missing_files,
                "version": version,
                "pipeline_action": pipeline_action,
            },
        )

        # Register handler for download completion to retry load
        self.register(
            SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
            self._on_model_download_complete,
        )

        return True, download_info

    def _on_model_download_complete(self, data: Dict):
        """Handle model download completion and retry loading.

        Args:
            data: Download completion data with model_path
        """
        downloaded_path = data.get("model_path", "")

        # Check if this download was for our model
        if downloaded_path and downloaded_path in self.model_path:
            self.logger.info(
                f"Model download complete for {downloaded_path}, retrying load"
            )

            # Unregister handler
            self.unregister(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_model_download_complete,
            )

            # Retry loading
            self.load()
