"""Validation mixin for LLM model manager.

This mixin handles model path validation, existence checking, and component
loading verification for the LLM model manager.
"""

import os
from typing import TYPE_CHECKING, List

from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.llm.managers.mixins.model_availability_mixin import (
    ModelAvailabilityMixin,
)
from airunner_services.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner_services.contract_enums import SignalCode

if TYPE_CHECKING:
    from airunner_services.model_management.llm_model_manager import (
        LLMModelManager,
    )


class ValidationMixin:
    """Mixin for validating model paths and checking component loading status.

    Handles verification that models exist on disk, paths are valid,
    and all required components are loaded for API or local mode.
    """

    def _check_model_exists(self: "LLMModelManager") -> bool:
        """Delegate model artifact checks to the availability mixin."""
        return ModelAvailabilityMixin._check_model_exists(self)

    def _trigger_model_download(self: "LLMModelManager") -> bool:
        """Delegate download triggering to the availability mixin."""
        return ModelAvailabilityMixin._trigger_model_download(self)

    def _trigger_gguf_download(self: "LLMModelManager") -> bool:
        """Delegate GGUF download triggering to the availability mixin."""
        return ModelAvailabilityMixin._trigger_gguf_download(self)

    def _try_convert_safetensors_to_gguf(
        self: "LLMModelManager",
    ) -> bool:
        """Delegate GGUF conversion checks to the availability mixin."""
        return ModelAvailabilityMixin._try_convert_safetensors_to_gguf(self)

    def _handle_missing_model(self: "LLMModelManager") -> None:
        """Delegate missing-model handling to the availability mixin."""
        ModelAvailabilityMixin._handle_missing_model(self)

    def _check_components_loaded_for_local(self: "LLMModelManager") -> bool:
        """Delegate local component readiness checks to the availability mixin."""
        return ModelAvailabilityMixin._check_components_loaded_for_local(self)

    def _is_gguf_quantization_selected(self: "LLMModelManager") -> bool:
        """Return True when the current model should use GGUF downloads.

        AIRunner now prefers vendor-provided GGUF artifacts for any local LLM
        that has one configured. Legacy 2/4/8-bit settings are treated as a
        stale preference for those models; we only fall back to transformers
        downloads when no GGUF artifact is available.
        """
        if not self._model_supports_gguf():
            return False
        return True

    def _model_supports_gguf(self: "LLMModelManager") -> bool:
        """Check if the current model supports GGUF format.
        
        This checks the provider config to see if GGUF repo/filename is configured.
        Models without GGUF config will use transformers instead.
        
        Returns:
            True if the model has GGUF support configured.
        """
        model_id = self._get_model_id_for_model()
        if not model_id:
            # No model_id - can't determine GGUF support, assume no
            return False
            
        gguf_info = LLMProviderConfig.get_gguf_info("local", model_id)
        return gguf_info is not None

    def _verify_model_files(self: "LLMModelManager", model_path: str) -> bool:
        """Verify essential model files exist in directory.

        Args:
            model_path: Path to model directory to check.

        Returns:
            True if all essential files present, False otherwise.
        """
        try:
            return self._check_model_files_exist(model_path)
        except Exception as e:
            self.logger.error(f"Error checking model files: {e}")
            return False

    def _check_model_files_exist(
        self: "LLMModelManager", model_path: str
    ) -> bool:
        """Check if required model files exist in directory.

        Args:
            model_path: Path to model directory.

        Returns:
            True if config and safetensors files exist.
        """
        files_in_dir = os.listdir(model_path)
        safetensors_found = any(
            f.endswith(".safetensors") for f in files_in_dir
        )

        essential_files = ["config.json"]
        has_essential = self._check_essential_files(
            model_path, essential_files
        )

        self._log_file_check_results(
            model_path, essential_files, has_essential, safetensors_found
        )

        return has_essential and safetensors_found

    def _log_file_check_results(
        self: "LLMModelManager",
        model_path: str,
        essential_files: List[str],
        has_essential: bool,
        safetensors_found: bool,
    ) -> None:
        """Log results of file existence check.

        Args:
            model_path: Path to model directory.
            essential_files: List of required filenames.
            has_essential: Whether essential files were found.
            safetensors_found: Whether safetensors files were found.
        """
        if not has_essential:
            self._log_missing_files(model_path, essential_files)

        if not safetensors_found:
            self.logger.info(f"No .safetensors files found in {model_path}")

        self.logger.info(
            f"Model exists check: {has_essential and safetensors_found} "
            f"(essential={has_essential}, safetensors={safetensors_found})"
        )

    def _check_essential_files(
        self: "LLMModelManager",
        model_path: str,
        essential_files: List[str],
    ) -> bool:
        """Check if all essential files exist.

        Args:
            model_path: Path to model directory.
            essential_files: List of required filenames.

        Returns:
            True if all essential files exist.
        """
        return all(
            os.path.exists(os.path.join(model_path, f))
            for f in essential_files
        )

    def _log_missing_files(
        self: "LLMModelManager",
        model_path: str,
        essential_files: List[str],
    ) -> None:
        """Log which essential files are missing.

        Args:
            model_path: Path to model directory.
            essential_files: List of required filenames.
        """
        missing = [
            f
            for f in essential_files
            if not os.path.exists(os.path.join(model_path, f))
        ]
        self.logger.info(f"Missing essential files: {missing}")

    def _get_model_id_for_model(self: "LLMModelManager") -> str:
        """Get model ID for current model.

        Returns:
            Model ID string, or empty string if not found.
        """
        llm_generator_settings = getattr(self, "llm_generator_settings", None)
        saved_model_id = getattr(llm_generator_settings, "model_id", None)
        if saved_model_id:
            model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
            if model_info:
                return saved_model_id

        model_id = LLMProviderConfig.resolve_model_id(
            "local",
            self.model_name,
        )
        if model_id:
            return model_id

        model_id = LLMProviderConfig.get_model_id_for_name(
            "local",
            self.model_name,
        )
        if model_id:
            return model_id

        self.logger.error(
            f"Could not find model_id for model: {self.model_name}"
        )
        return ""

    def _get_expected_gguf_path(self: "LLMModelManager") -> str | None:
        """Return the exact GGUF artifact path expected for the current model."""
        model_id = self._get_model_id_for_model()
        path_settings = getattr(self, "path_settings", None)
        base_path = getattr(path_settings, "base_path", None)
        if not model_id or not base_path:
            return None

        artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
            base_path,
            "local",
            model_id=model_id,
        )
        if artifact_path.lower().endswith(".gguf"):
            return artifact_path
        return None

    def _get_repo_id_for_model(self: "LLMModelManager") -> str:
        """Get HuggingFace repo ID for current model.

        Returns:
            Repository ID string, or empty string if not found.
        """
        model_id = self._get_model_id_for_model()
        if model_id:
            model_info = LLMProviderConfig.get_model_info("local", model_id)
            return model_info.get("repo_id", "")

        self.logger.error(
            f"Could not find repo_id for model: {self.model_name}"
        )
        return ""

    def _emit_download_signal(self: "LLMModelManager", repo_id: str) -> None:
        """Emit signal to trigger model download.

        Args:
            repo_id: HuggingFace repository identifier.
        """
        signal_data = {
            "model_path": self.model_path,
            "model_name": self.model_name,
            "repo_id": repo_id,
        }

        # Include missing_files if we have them (for partial downloads)
        if hasattr(self, "_missing_files") and self._missing_files:
            signal_data["missing_files"] = self._missing_files

        self.emit_signal(
            SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
            signal_data,
        )

    def _validate_model_path(self: "LLMModelManager") -> bool:
        """Verify model path is set and optionally registered.

        Checks that model path is configured. Warns if model is not
        in the resource manager registry but allows loading anyway.
        Emits an error signal if the model path is not set.

        Returns:
            True if path is valid, False if not set.
        """
        try:
            if not self.model_path:
                self.logger.error("Model path is not set")
                self.emit_signal(
                    SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                    {
                        "message": "No LLM model selected. Please go to Settings > LLM and select a model."
                    },
                )
                return False
        except ValueError as e:
            # Catch the ValueError raised by the property when path is not configured
            # or when embedding model is incorrectly used as main LLM
            self.logger.error(f"Model path validation failed: {e}")

            # Check if this is an embedding model error - auto-fix it
            error_msg = str(e)
            if "embedding model" in error_msg.lower():
                self.logger.warning(
                    "Detected embedding model set as main LLM - clearing corrupted model_path"
                )
                # Clear the corrupted path so user can select a proper model
                self.llm_generator_settings.model_path = ""
                self.session.commit()

                message = (
                    "Invalid model configuration detected and cleared: "
                    "The embedding model was incorrectly set as the main LLM. "
                    "Please go to Settings > LLM and select a proper chat model "
                    "(e.g., Qwen, Mistral, or Llama)."
                )
            else:
                message = "No LLM model selected. Please go to Settings > LLM and select a model."

            self.emit_signal(
                SignalCode.APPLICATION_STATUS_ERROR_SIGNAL,
                {"message": message},
            )
            return False

        self._check_model_registry()
        return True

    def _check_model_registry(self: "LLMModelManager") -> None:
        """Check if model is registered with resource manager.

        Logs warning if model is not in registry but does not prevent loading.
        """
        resource_manager = ModelResourceManager()
        model_metadata = resource_manager.registry.get_model(self.model_path)

        if not model_metadata:
            self.logger.warning(
                f"Model {self.model_path} not in registry - "
                "loading without validation"
            )

    def _check_and_download_model(self: "LLMModelManager") -> bool:
        """Check if model exists and trigger download if needed.

        Returns:
            True if model exists or is API-based, False if download triggered.
        """
        if not self.llm_settings.use_local_llm:
            return True

        if not self._check_model_exists():
            self._handle_missing_model()
            return False

        return True

    def _check_components_loaded_for_api(self: "LLMModelManager") -> bool:
        """Check if required components are loaded for API mode.

        API mode requires chat model and workflow manager.

        Returns:
            True if all required components are loaded.
        """
        return (
            self._chat_model is not None and self._workflow_manager is not None
        )
