"""Worker for loading and managing the NSFW safety checker."""

import os
from typing import Optional, Dict, Any

import torch
from transformers import CLIPFeatureExtractor
from diffusers.pipelines.stable_diffusion import StableDiffusionSafetyChecker

from airunner.components.application.workers.worker import Worker
from airunner.enums import SignalCode, ModelStatus, ModelType
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


class SafetyCheckerWorker(Worker):
    """Worker for NSFW safety checker model.

    Handles loading, unloading, and filtering images for NSFW content.
    Operates independently of SD model workers following signal-based architecture.
    """

    # Class-level instance reference for singleton access
    _instance: Optional["SafetyCheckerWorker"] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the class-level instance reference
        SafetyCheckerWorker._instance = self
        self._safety_checker: Optional[Any] = None
        self._feature_extractor: Optional[Any] = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._data_type = (
            torch.float16 if torch.cuda.is_available() else torch.float32
        )

        # Register signal handlers
        self.register(SignalCode.SAFETY_CHECKER_LOAD_SIGNAL, self.handle_load)
        self.register(
            SignalCode.SAFETY_CHECKER_UNLOAD_SIGNAL, self.handle_unload
        )
        self.register(
            SignalCode.SAFETY_CHECKER_FILTER_REQUEST,
            self.handle_filter_request,
        )

    @classmethod
    def get_instance(cls) -> Optional["SafetyCheckerWorker"]:
        """Get the singleton instance of SafetyCheckerWorker.

        Returns:
            The SafetyCheckerWorker instance or None if not initialized.
        """
        return cls._instance

    @property
    def safety_checker(self):
        """Get the loaded safety checker model."""
        return self._safety_checker

    @property
    def feature_extractor(self):
        """Get the loaded feature extractor."""
        return self._feature_extractor

    def handle_load(self, data: Optional[Dict] = None):
        """Load the safety checker and feature extractor models.

        Args:
            data: Optional data dictionary (unused)
        """
        if (
            self._safety_checker is not None
            and self._feature_extractor is not None
        ):
            self.logger.info("Safety checker already loaded")
            self._emit_status(ModelStatus.LOADED)
            return

        self.logger.info("Loading safety checker models")
        self._emit_status(ModelStatus.LOADING)

        try:
            # Safety checker is stored as a standalone model
            from airunner.components.settings.data.path_settings import (
                PathSettings,
            )

            path_settings = PathSettings.objects.first()

            safety_checker_path = os.path.expanduser(
                os.path.join(
                    path_settings.base_path,
                    "art/models/Safety Checker",
                )
            )

            self.logger.info(f"Safety checker path: {safety_checker_path}")

            # Check if files exist
            if not os.path.exists(safety_checker_path):
                self.logger.error(
                    f"Safety checker path does not exist: {safety_checker_path}"
                )
                self._emit_status(ModelStatus.FAILED)
                return

            # Check for required files
            required_files = [
                "config.json",
                "pytorch_model.bin",
                "preprocessor_config.json",
            ]
            missing_files = [
                f
                for f in required_files
                if not os.path.exists(os.path.join(safety_checker_path, f))
            ]

            if missing_files:
                self.logger.error(
                    f"Missing safety checker files: {missing_files}"
                )
                self.logger.info(
                    "Triggering download via ART_MODEL_DOWNLOAD_REQUIRED signal"
                )

                self.emit_signal(
                    SignalCode.ART_MODEL_DOWNLOAD_REQUIRED,
                    {
                        "repo_id": "CompVis/stable-diffusion-safety-checker",
                        "model_path": safety_checker_path,
                        "model_type": "art",
                        "version": "Safety Checker",
                        "pipeline_action": "safety_checker",
                        "missing_files": missing_files,
                    },
                )

                # Register for download completion
                self.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                    self._on_download_complete,
                )
                self.register(
                    SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                    self._on_download_failed,
                )
                return

            # Load the models
            self.logger.info("Loading StableDiffusionSafetyChecker")
            self._safety_checker = (
                StableDiffusionSafetyChecker.from_pretrained(
                    safety_checker_path,
                    torch_dtype=self._data_type,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
            )

            if self._safety_checker:
                self._safety_checker.to(self._device)
                self.logger.info("Safety checker loaded successfully")

            # Load feature extractor (uses same preprocessor_config.json)
            self.logger.info("Loading CLIPFeatureExtractor")
            self._feature_extractor = CLIPFeatureExtractor.from_pretrained(
                safety_checker_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )

            if self._feature_extractor:
                self.logger.info("Feature extractor loaded successfully")

            self._emit_status(ModelStatus.LOADED)
            self.logger.info("Safety checker worker loaded successfully")

        except Exception as e:
            self.logger.error(
                f"Failed to load safety checker: {e}", exc_info=True
            )
            self._safety_checker = None
            self._feature_extractor = None
            self._emit_status(ModelStatus.FAILED)

    def handle_unload(self, data: Optional[Dict] = None):
        """Unload the safety checker models.

        Args:
            data: Optional data dictionary (unused)
        """
        self.logger.info("Unloading safety checker models")

        if self._safety_checker is not None:
            try:
                del self._safety_checker
            except Exception:
                pass
            self._safety_checker = None

        if self._feature_extractor is not None:
            try:
                del self._feature_extractor
            except Exception:
                pass
            self._feature_extractor = None

        # Force garbage collection
        import gc

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self._emit_status(ModelStatus.UNLOADED)
        self.logger.info("Safety checker worker unloaded")

    def handle_filter_request(self, data: Dict):
        """Filter images for NSFW content.

        Args:
            data: Dictionary containing:
                - images: List of PIL Images to check
                - request_id: Unique identifier for this request (optional)
        """
        if not self._safety_checker or not self._feature_extractor:
            self.logger.warning(
                "Safety checker not loaded, returning images unchanged"
            )
            self._emit_filter_complete(
                data.get("images", []),
                [False] * len(data.get("images", [])),
                data.get("request_id"),
            )
            return

        images = data.get("images", [])
        if not images:
            self.logger.warning("No images provided for filtering")
            self._emit_filter_complete([], [], data.get("request_id"))
            return

        self.logger.info(f"Filtering {len(images)} images for NSFW content")

        try:
            from airunner.components.art.utils.nsfw_checker import (
                check_and_mark_nsfw_images,
            )

            marked_images, nsfw_flags = check_and_mark_nsfw_images(
                images,
                self._feature_extractor,
                self._safety_checker,
                self._device,
            )

            if any(nsfw_flags):
                self.logger.info(
                    f"NSFW content detected in {sum(nsfw_flags)} of {len(images)} images"
                )
            else:
                self.logger.debug("No NSFW content detected")

            self._emit_filter_complete(
                marked_images, nsfw_flags, data.get("request_id")
            )

        except Exception as e:
            self.logger.error(
                f"Error during NSFW filtering: {e}", exc_info=True
            )
            # Return images unchanged on error
            self._emit_filter_complete(
                images, [False] * len(images), data.get("request_id")
            )

    def _emit_status(self, status: ModelStatus):
        """Emit model status change signal.

        Args:
            status: New model status
        """
        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL,
            {
                "model": ModelType.SAFETY_CHECKER,
                "status": status,
                "path": "",
            },
        )

    def _emit_filter_complete(self, images, nsfw_flags, request_id=None):
        """Emit filter complete signal with results.

        Args:
            images: List of processed PIL Images
            nsfw_flags: List of booleans indicating NSFW detection
            request_id: Optional request identifier
        """
        self.emit_signal(
            SignalCode.SAFETY_CHECKER_FILTER_COMPLETE,
            {
                "images": images,
                "nsfw_detected": nsfw_flags,
                "request_id": request_id,
            },
        )

    def _on_download_complete(self, data: Dict):
        """Handle download completion and retry load.

        Args:
            data: Download completion data
        """
        from airunner.components.settings.data.path_settings import (
            PathSettings,
        )

        path_settings = PathSettings.objects.first()

        expected_path = os.path.expanduser(
            os.path.join(
                path_settings.base_path,
                "art/models/Safety Checker",
            )
        )
        downloaded_path = data.get("model_path", "")

        if downloaded_path and os.path.abspath(
            downloaded_path
        ) == os.path.abspath(expected_path):
            self.logger.info("Safety checker download complete, retrying load")
            self._unregister_download_handlers()
            self.handle_load()

    def _on_download_failed(self, data: Dict):
        """Handle download failure.

        Args:
            data: Download failure data
        """
        error = data.get("error", "Unknown error")
        self.logger.error(f"Safety checker download failed: {error}")
        self._unregister_download_handlers()
        self._emit_status(ModelStatus.FAILED)

    def _unregister_download_handlers(self):
        """Unregister download completion/failure handlers."""
        try:
            self.mediator.unregister(
                SignalCode.HUGGINGFACE_DOWNLOAD_COMPLETE,
                self._on_download_complete,
            )
        except Exception:
            pass

        try:
            self.mediator.unregister(
                SignalCode.HUGGINGFACE_DOWNLOAD_FAILED,
                self._on_download_failed,
            )
        except Exception:
            pass
