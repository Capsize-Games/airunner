"""Validation mixin for LLM model manager.

This mixin handles model path validation, existence checking, and component
loading verification for the LLM model manager.
"""

import os
from typing import TYPE_CHECKING, List

from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.enums import SignalCode, ModelType, ModelStatus

if TYPE_CHECKING:
    from airunner.components.llm.managers.llm_model_manager import (
        LLMModelManager,
    )


class ValidationMixin:
    """Mixin for validating model paths and checking component loading status.

    Handles verification that models exist on disk, paths are valid,
    and all required components are loaded for API or local mode.
    """

    def _check_model_exists(self: "LLMModelManager") -> bool:
        """Check if model exists with all necessary files.

        Validates that the model directory contains config.json and
        at least one .safetensors file.

        Returns:
            True if model exists with required files, False otherwise.
        """
        if not self.llm_settings.use_local_llm:
            return True

        model_path = self.model_path
        if not os.path.exists(model_path):
            self.logger.info(f"Model path does not exist: {model_path}")
            return False

        return self._verify_model_files(model_path)

    def _verify_model_files(self: "LLMModelManager", model_path: str) -> bool:
        """Verify essential model files exist in directory.

        Args:
            model_path: Path to model directory to check.

        Returns:
            True if all essential files present, False otherwise.
        """
        essential_files = ["config.json"]

        try:
            files_in_dir = os.listdir(model_path)
            safetensors_found = any(
                f.endswith(".safetensors") for f in files_in_dir
            )

            has_essential = self._check_essential_files(
                model_path, essential_files
            )

            if not has_essential:
                self._log_missing_files(model_path, essential_files)

            if not safetensors_found:
                self.logger.info(
                    f"No .safetensors files found in {model_path}"
                )

            result = has_essential and safetensors_found
            self.logger.info(
                f"Model exists check: {result} "
                f"(essential={has_essential}, safetensors={safetensors_found})"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error checking model files: {e}")
            return False

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

    def _trigger_model_download(self: "LLMModelManager") -> bool:
        """Trigger model download via signal.

        Emits signal to download manager to fetch model from HuggingFace.

        Returns:
            False to indicate model is not yet available.
        """
        self.logger.info(
            f"Model not found at {self.model_path}, triggering download"
        )

        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            return False

        self._emit_download_signal(repo_id)
        return False

    def _get_repo_id_for_model(self: "LLMModelManager") -> str:
        """Get HuggingFace repo ID for current model.

        Returns:
            Repository ID string, or empty string if not found.
        """
        for model_id, model_info in LLMProviderConfig.LOCAL_MODELS.items():
            if model_info["name"] == self.model_name:
                return model_info["repo_id"]

        self.logger.error(
            f"Could not find repo_id for model: {self.model_name}"
        )
        return ""

    def _emit_download_signal(self: "LLMModelManager", repo_id: str) -> None:
        """Emit signal to trigger model download.

        Args:
            repo_id: HuggingFace repository identifier.
        """
        self.emit_signal(
            SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
            {
                "model_path": self.model_path,
                "model_name": self.model_name,
                "repo_id": repo_id,
            },
        )

    def _validate_model_path(self: "LLMModelManager") -> bool:
        """Verify model path is set and optionally registered.

        Checks that model path is configured. Warns if model is not
        in the resource manager registry but allows loading anyway.

        Returns:
            True if path is valid, False if not set.
        """
        if not self.model_path:
            self.logger.error("Model path is not set")
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

    def _handle_missing_model(self: "LLMModelManager") -> None:
        """Handle missing model by triggering download and updating status.

        Only triggers download once to avoid spam. Updates model status
        to FAILED to prevent repeated download attempts.
        """
        if self.model_status[ModelType.LLM] != ModelStatus.FAILED:
            self._trigger_model_download()
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def _check_components_loaded_for_api(self: "LLMModelManager") -> bool:
        """Check if required components are loaded for API mode.

        API mode requires chat model and workflow manager.

        Returns:
            True if all required components are loaded.
        """
        return (
            self._chat_model is not None and self._workflow_manager is not None
        )

    def _check_components_loaded_for_local(self: "LLMModelManager") -> bool:
        """Check if required components are loaded for local mode.

        Local mode requires model, tokenizer, chat model, and workflow manager.

        Returns:
            True if all required components are loaded.
        """
        return (
            self._model is not None
            and self._tokenizer is not None
            and self._chat_model is not None
            and self._workflow_manager is not None
        )
