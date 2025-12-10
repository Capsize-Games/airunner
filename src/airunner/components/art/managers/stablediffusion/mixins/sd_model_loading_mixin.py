"""
Mixin providing model loading operations for Stable Diffusion.

This mixin handles loading of all SD model components including safety checker,
ControlNet, LoRA, embeddings, Compel, DeepCache, and schedulers.
"""

import os
from typing import Dict, Optional

import diffusers
from DeepCache import DeepCacheSDHelper
from compel import (
    Compel,
    DiffusersTextualInversionManager,
)
from transformers import CLIPFeatureExtractor
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker

from airunner.components.art.data.embedding import Embedding
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.schedulers import Schedulers
from airunner.components.art.managers.stablediffusion.safe_textual_inversion_manager import (
    SafeDiffusersTextualInversionManager,
)
from airunner.components.art.managers.stablediffusion import model_loader
from airunner.enums import ModelStatus, ModelType
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


class SDModelLoadingMixin:
    """Mixin providing model loading operations for Stable Diffusion."""

    def _load_controlnet_model(self):
        """
        Load ControlNet model for conditional image generation.

        Only loads if ControlNet is enabled in current request.
        """
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

    def _load_lora(self):
        """
        Load all enabled LoRA models for current SD version.

        Tracks loaded and disabled LoRAs separately.
        """
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

    def _load_embeddings(self):
        """
        Load textual inversion embeddings for current SD version.

        Automatically loads/unloads embeddings based on active status.
        Invalidates cached prompt embeddings when embeddings change.
        """
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
            # Invalidate cached prompt embeddings
            self._unload_prompt_embeds()

    def _load_embedding(self, embedding):
        """
        Load single textual inversion embedding.

        Args:
            embedding: Embedding database record with path and trigger word.
        """
        file_name = os.path.basename(embedding.path)
        path_name = os.path.dirname(embedding.path)
        self._pipe.load_textual_inversion(
            path_name,
            weight_name=file_name,
            token=embedding.trigger_word.split(","),
        )
        self._loaded_embeddings.append(embedding.path)

    def _load_compel(self):
        """
        Load Compel for prompt weighting and blending.

        Only loads if use_compel is enabled. Creates textual inversion
        manager and Compel processor.
        """
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
        """
        Load DeepCache for accelerated inference.

        Enables caching to speed up generation at cost of slight quality.
        """
        self._deep_cache_helper = DeepCacheSDHelper(pipe=self._pipe)
        self._deep_cache_helper.set_params(cache_interval=3, cache_branch_id=0)
        try:
            self._deep_cache_helper.enable()
        except AttributeError as e:
            self.logger.error(f"Failed to enable deep cache: {e}")

    def _load_controlnet_processor(self):
        """
        Load ControlNet image preprocessor.

        Loads appropriate processor for current ControlNet model type
        (e.g., Canny, depth, OpenPose).
        """
        if not self.controlnet_enabled:
            return
        self._controlnet_processor = model_loader.load_controlnet_processor(
            self.controlnet_enabled,
            self.controlnet_model,
            self.controlnet_processor_path,
            self.logger,
        )

    def _load_scheduler(self, scheduler_name: Optional[str] = None):
        """
        Load noise scheduler for diffusion process.

        Args:
            scheduler_name: Optional scheduler name to load.
                           Uses request scheduler if not provided.
        """
        requested_name = (
            scheduler_name
            or (self.image_request.scheduler if self.image_request else None)
            or self.scheduler_name
        )
        if not requested_name:
            self.logger.debug(
                "No scheduler specified; skipping scheduler load."
            )
            return

        self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADING)

        scheduler_record = Schedulers.objects.filter_by_first(
            display_name=requested_name
        )
        if not scheduler_record:
            self.logger.error(f"Failed to find scheduler {requested_name}")
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
            return

        scheduler_class_name = scheduler_record.name
        scheduler_class = getattr(diffusers, scheduler_class_name, None)
        if scheduler_class is None:
            self.logger.error(
                "Scheduler class %s not found in diffusers for %s",
                scheduler_class_name,
                requested_name,
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)
            return

        try:
            base_config = self._get_scheduler_base_config(scheduler_class)
            if base_config is None:
                self.logger.warning(
                    "No base config available for scheduler %s, using defaults",
                    requested_name,
                )
                base_config = {}

            self._scheduler = scheduler_class.from_config(base_config)

            if self._pipe is not None:
                self._pipe.scheduler = self._scheduler

            self._scheduler_name = requested_name
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.LOADED)
            self.logger.info(f"Loaded scheduler: {requested_name}")

        except Exception as e:
            self.logger.error(
                f"Failed to load scheduler {requested_name}: {e}"
            )
            self.change_model_status(ModelType.SCHEDULER, ModelStatus.FAILED)

    def _load_lora_weights(self, lora: Lora):
        """
        Load single LoRA weights file into pipeline.

        Args:
            lora: LoRA database record with path and scale.
        """
        if lora in self._disabled_lora or lora.path in self._loaded_lora:
            return
        do_disable_lora = False
        filename = os.path.basename(lora.path)
        try:
            lora_base_path = self.lora_base_path
            adapter_name = os.path.splitext(filename)[0]
            adapter_name = adapter_name.replace(".", "_")
            self._pipe.load_lora_weights(
                lora_base_path,
                weight_name=filename,
                adapter_name=adapter_name,
                scale=getattr(lora, "scale", 1.0),
            )
            self._loaded_lora[lora.path] = lora
        except AttributeError:
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

    def _load_textual_inversion_manager(self):
        """
        Load textual inversion manager for Compel.

        Uses SafeDiffusersTextualInversionManager to cap token expansion
        at model max length. Falls back to upstream manager if needed.
        """
        self.logger.debug(
            "Loading safe textual inversion manager "
            "(caps token expansion at model max length)"
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
        """
        Load Compel processor for prompt weighting.

        Creates Compel instance with current tokenizer and text encoder.
        """
        self.logger.debug("Loading compel proc")
        self._compel_proc = Compel(**self.compel_parameters)

    def _load_safety_checker(self):
        """
        Load safety checker and feature extractor for NSFW detection.

        Only loads if use_safety_checker is True in application settings.
        Loads both StableDiffusionSafetyChecker and CLIPFeatureExtractor.
        Automatically downloads missing files from HuggingFace if needed.
        """
        self.logger.info(
            f"_load_safety_checker called. use_safety_checker={self.use_safety_checker}"
        )

        if not self.use_safety_checker:
            self.logger.info(
                "Safety checker disabled in settings, skipping load"
            )
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED
            )
            return True

        self.logger.info("Safety checker enabled, proceeding with load...")
        self.change_model_status(ModelType.SAFETY_CHECKER, ModelStatus.LOADING)

        # Safety checker is stored as a standalone model
        safety_checker_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models/Safety Checker",
            )
        )

        self.logger.info(f"Safety checker path: {safety_checker_path}")

        # Ensure directory exists
        os.makedirs(safety_checker_path, exist_ok=True)

        # Check for missing files and trigger download if needed
        try:
            from airunner.components.art.utils.model_file_checker import (
                ModelFileChecker,
            )

            # Check safety checker files
            self.logger.info(
                f"Checking for missing safety checker files at: {safety_checker_path}"
            )
            should_download_checker, download_info_checker = (
                ModelFileChecker.should_trigger_download(
                    model_path=safety_checker_path,
                    model_type="art",
                    version="Safety Checker",
                    pipeline_action="safety_checker",
                )
            )

            self.logger.info(
                f"should_download_checker={should_download_checker}, "
                f"download_info={download_info_checker}"
            )

            if should_download_checker:
                self.logger.info(
                    f"Safety checker files missing, triggering download: "
                    f"{download_info_checker.get('missing_files', [])}"
                )

                from airunner.enums import SignalCode

                # Request download via global HuggingFace download worker
                self.emit_signal(
                    SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
                    {
                        "repo_id": download_info_checker.get(
                            "repo_id",
                            "CompVis/stable-diffusion-safety-checker",
                        ),
                        "model_path": safety_checker_path,
                        "model_type": "art",
                        "version": "Safety Checker",
                        "pipeline_action": "safety_checker",
                        "missing_files": download_info_checker.get(
                            "missing_files", []
                        ),
                        "image_request": getattr(self, "image_request", None),
                    },
                )

                # Register for download completion/failure to retry or log
                self._unregister_safety_checker_download_handlers()
                self.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_safety_checker_download_complete,
                )
                self.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._on_safety_checker_download_failed,
                )
                return False

            # Try to load the models
            self.logger.info(
                f"Loading safety checker from: {safety_checker_path}"
            )
            self._safety_checker = (
                StableDiffusionSafetyChecker.from_pretrained(
                    safety_checker_path,
                    torch_dtype=self.data_type,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
            )
            if self._safety_checker:
                self._safety_checker.to(self._device)
                self.logger.info("Safety checker loaded successfully")

            # Load feature extractor (uses same preprocessor_config.json as safety checker)
            self.logger.info(
                f"Loading feature extractor from: {safety_checker_path}"
            )
            self._feature_extractor = CLIPFeatureExtractor.from_pretrained(
                safety_checker_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
            if self._feature_extractor:
                self.logger.info("Feature extractor loaded successfully")

            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.LOADED
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to load safety checker: {e}")
            self._safety_checker = None
            self._feature_extractor = None
            self.change_model_status(
                ModelType.SAFETY_CHECKER, ModelStatus.FAILED
            )
            return False

    def _on_safety_checker_download_complete(self, data: Dict):
        """Retry safety checker load after custom downloader finishes."""

        expected_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models/Safety Checker",
            )
        )
        downloaded_path = data.get("model_path", "")

        if not downloaded_path:
            self.logger.warning(
                "Download complete signal received but no model_path provided"
            )
            return

        if os.path.abspath(downloaded_path) != os.path.abspath(expected_path):
            self.logger.debug(
                f"Download complete for different path: {downloaded_path} vs {expected_path}"
            )
            return

        self.logger.info(
            "Safety checker download complete, unregistering handlers"
        )

        self._unregister_safety_checker_download_handlers()

        # If generation is in progress, WorkerManager will retry automatically
        if getattr(self, "image_request", None) is not None:
            self.logger.info(
                "Pending image request detected; letting WorkerManager retry load"
            )
            return

        # Only retry load if model is not already loaded
        if self._safety_checker is None or self._feature_extractor is None:
            self.logger.info(
                "Safety checker/feature extractor not loaded, retrying full model load"
            )
            self.load()
        else:
            self.logger.info(
                "Safety checker and feature extractor already loaded, skipping retry"
            )

    def _on_safety_checker_download_failed(self, data: Dict):
        """Log failure from custom downloader and clean up handlers."""

        expected_path = os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "art/models/Safety Checker",
            )
        )
        failed_path = data.get("model_path") or data.get("output_dir")

        if failed_path and os.path.abspath(failed_path) != os.path.abspath(
            expected_path
        ):
            return

        error = data.get("error", "Unknown error")
        self.logger.error(f"Safety checker download failed: {error}")

        self._unregister_safety_checker_download_handlers()

    def _unregister_safety_checker_download_handlers(self) -> None:
        from airunner.enums import SignalCode

        for code, handler in (
            (
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_safety_checker_download_complete,
            ),
            (
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                self._on_safety_checker_download_failed,
            ),
        ):
            try:
                self.mediator.unregister(code, handler)
            except Exception:
                pass
