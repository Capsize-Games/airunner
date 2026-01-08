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
from airunner.utils.memory import clear_memory

from airunner.components.art.managers.stablediffusion import (
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
from airunner.components.model_management import ModelResourceManager


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
        ModelType.CONTROLNET: ModelStatus.UNLOADED,
        ModelType.LORA: ModelStatus.UNLOADED,
        ModelType.EMBEDDINGS: ModelStatus.UNLOADED,
        ModelType.SAFETY_CHECKER: ModelStatus.UNLOADED,
        ModelType.SCHEDULER: ModelStatus.UNLOADED,
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
        self._controlnet: Optional[Any] = None
        self._controlnet_processor: Any = None
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
        self._compel_proc: Optional[Any] = None
        self._loaded_lora: Dict = {}
        self._disabled_lora: List = []
        self._loaded_embeddings: List = []
        self._current_state: HandlerState = HandlerState.UNINITIALIZED
        self._deep_cache_helper: Optional[Any] = None
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

    @property
    def use_safety_checker(self) -> bool:
        """Get whether to use safety checker for NSFW detection.

        Returns:
            True if safety checker should be used.
        """
        return self.application_settings.nsfw_filter

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

    def _check_and_mark_nsfw_images(self, images):
        """
        Check images for NSFW content and mark detected images.

        Wrapper around the nsfw_checker utility that integrates
        safety checker functionality into the generation pipeline.
        Gets the loaded models from the SafetyCheckerWorker singleton.

        Args:
            images: List of PIL Images to check

        Returns:
            Tuple of (marked_images, nsfw_flags) where marked_images
            contains black overlays on NSFW detections and nsfw_flags
            is a list of booleans indicating which images were detected.
        """
        if not self.use_safety_checker:
            # Safety checker disabled, return unchanged
            return images, [False] * len(images)

        # Get the safety checker worker singleton instance
        try:
            from airunner.components.art.workers.safety_checker_worker import (
                SafetyCheckerWorker,
            )

            safety_worker = SafetyCheckerWorker.get_instance()
            if safety_worker is None:
                self.logger.warning(
                    "SafetyCheckerWorker not initialized, skipping NSFW check"
                )
                return images, [False] * len(images)

            # Check if models are loaded in the worker
            if (
                safety_worker.safety_checker is None
                or safety_worker.feature_extractor is None
            ):
                self.logger.warning(
                    "Safety checker models not loaded, skipping NSFW check"
                )
                return images, [False] * len(images)

            from airunner.components.art.utils.nsfw_checker import (
                check_and_mark_nsfw_images,
            )

            return check_and_mark_nsfw_images(
                images,
                safety_worker.feature_extractor,
                safety_worker.safety_checker,
                self._device,
            )
        except Exception as e:
            self.logger.error(f"NSFW check failed: {e}")
            return images, [False] * len(images)
        except Exception as e:
            self.logger.error(f"NSFW check failed: {e}")
            return images, [False] * len(images)

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
        self.logger.debug(
            f"[LOAD ENTRY] sd_is_loading={self.sd_is_loading}, "
            f"model_is_loaded={self.model_is_loaded}, "
            f"model_status={self.model_status}, model_type={self.model_type}"
        )
        if self.sd_is_loading or self.model_is_loaded:
            self.logger.debug("[LOAD ENTRY] Returning early - already loading or loaded")
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

        # Safety checker is now managed by WorkerManager before generation
        # Don't trigger it here to avoid race conditions

        if (
            self.controlnet_enabled
            and not self.controlnet_is_loading
            and self._pipe
            and not self._controlnet_model
        ):
            self.unload()

        self.load_controlnet()

        self.logger.debug("[LOAD] About to call _load_pipe()")
        if self._load_pipe():
            self.logger.debug("[LOAD] _load_pipe() returned True, continuing load sequence")
            self._send_pipeline_loaded_signal()
            self._move_pipe_to_device()
            self._load_scheduler()
            self._load_lora()
            self._load_embeddings()
            self._load_compel()
            # DeepCache disabled: incompatible with torch.compile() and provides
            # only 15% speedup vs torch.compile's 2-3x speedup
            # self._load_deep_cache()
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

        # Unload safety checker if it was loaded
        if self.use_safety_checker:
            from airunner.enums import SignalCode

            self.emit_signal(SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, {})

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
        self.logger.debug("[_load_pipe] ENTERING METHOD")
        try:
            pipeline_class = self._pipeline_class
            self.logger.debug(f"[_load_pipe] pipeline_class={pipeline_class}")
            section = self.section
            self.logger.debug(f"[_load_pipe] section={section}")
        except Exception as e:
            self.logger.error(f"[_load_pipe] Error accessing properties: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
        
        self.logger.debug(
            f"Loading pipe {pipeline_class} for {section}"
        )
        self.change_model_status(self.model_type, ModelStatus.LOADING)
        data = self._prepare_pipe_data()

        try:
            self._set_pipe(self.config_path, data)
            self.change_model_status(self.model_type, ModelStatus.LOADED)

            resource_manager = ModelResourceManager()
            resource_manager.model_loaded(self.model_path)
        except RuntimeError as e:
            error_msg = str(e)
            if "download triggered" in error_msg:
                # Download was triggered, WorkerManager will handle retry via HUGGINGFACE_DOWNLOAD_COMPLETE
                self.logger.info(f"Download triggered: {error_msg}")
                self.change_model_status(self.model_type, ModelStatus.UNLOADED)
            else:
                self.logger.error(f"Failed to load pipe: {e}")
                self.change_model_status(self.model_type, ModelStatus.FAILED)
            return False
        except Exception as e:
            self.logger.error(f"Failed to load pipe: {e}")
            self.change_model_status(self.model_type, ModelStatus.FAILED)
            return False
        return True

    def _set_lora_adapters(self):
        """Configure LoRA adapter weights and names on the pipeline.
        
        Only sets adapters if they were actually loaded into the pipeline.
        Validates that requested adapters exist before calling set_adapters.
        
        For Z-Image and other transformer-based pipelines, also checks the
        transformer's peft_config directly.
        """
        self.logger.debug("Setting LORA adapters")
        
        # Check if pipeline supports adapters and has any loaded
        if not hasattr(self._pipe, 'get_list_adapters'):
            self.logger.debug("Pipeline does not support LoRA adapters")
            return
            
        # Get adapters that are actually loaded in the pipeline
        available_adapters = set()
        try:
            pipeline_adapters = self._pipe.get_list_adapters()
            # get_list_adapters returns a dict like {'transformer': ['adapter1'], 'unet': ['adapter1']}
            for component_adapters in pipeline_adapters.values():
                available_adapters.update(component_adapters)
        except Exception as e:
            self.logger.debug(f"Could not get list of adapters from pipeline: {e}")
        
        # Also check transformer directly if it has peft_config (for Z-Image, FLUX, etc.)
        if not available_adapters and hasattr(self._pipe, 'transformer'):
            transformer = self._pipe.transformer
            if hasattr(transformer, 'peft_config') and transformer.peft_config:
                available_adapters.update(transformer.peft_config.keys())
                self.logger.debug(f"Found adapters in transformer.peft_config: {available_adapters}")
        
        # Also check unet directly if it has peft_config (for SD pipelines)
        if not available_adapters and hasattr(self._pipe, 'unet'):
            unet = self._pipe.unet
            if hasattr(unet, 'peft_config') and unet.peft_config:
                available_adapters.update(unet.peft_config.keys())
                self.logger.debug(f"Found adapters in unet.peft_config: {available_adapters}")
        
        if not available_adapters:
            self.logger.debug("No LoRA adapters loaded in pipeline")
            return
            
        loaded_lora_id = [lora.id for lora in self._loaded_lora.values()]
        enabled_lora = Lora.objects.filter(Lora.id.in_(loaded_lora_id))
        adapter_weights = []
        adapter_names = []
        for lora in enabled_lora:
            adapter_name = os.path.splitext(os.path.basename(lora.path))[0]
            adapter_name = adapter_name.replace(".", "_")
            # Only include adapters that are actually loaded in the pipeline
            if adapter_name in available_adapters:
                adapter_weights.append(lora.scale / 100.0)
                adapter_names.append(adapter_name)
            else:
                self.logger.warning(f"LoRA adapter '{adapter_name}' not found in pipeline, skipping")
                
        if len(adapter_weights) > 0:
            self._pipe.set_adapters(
                adapter_names, adapter_weights=adapter_weights
            )
            self.logger.debug(f"LORA adapters set: {adapter_names} with weights: {adapter_weights}")
        else:
            self.logger.debug("No LORA adapters to set")

    def _finalize_load_stable_diffusion(self):
        """
        Finalize Stable Diffusion loading after all components are ready.

        Verifies all required components are loaded and sets handler state
        to READY. Attaches ControlNet processor to pipeline if enabled.
        """
        if self._pipe is not None:
            self._current_state = HandlerState.READY
            self.change_model_status(self.model_type, ModelStatus.LOADED)
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
        # Include image_request so generation can be retried after download
        # WorkerManager will handle the download and retry generation via DO_GENERATE_SIGNAL
        self.emit_signal(
            SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
            {
                "repo_id": repo_id,
                "model_path": self.model_path,
                "missing_files": missing_files,
                "version": version,
                "pipeline_action": pipeline_action,
                "image_request": self.image_request,  # Pass image_request for retry
            },
        )

        return True, download_info
