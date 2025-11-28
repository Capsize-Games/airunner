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

        Uses llm_file_bootstrap_data.py as the source of truth for required files.
        Only files listed in that configuration are considered essential.

        Returns:
            True if model exists with required files, False otherwise.
        """
        if not self.llm_settings.use_local_llm:
            return True

        model_path = self.model_path
        if not os.path.exists(model_path):
            self.logger.info(f"Model path does not exist: {model_path}")
            self._missing_files = None  # Full download needed
            return False

        # Get repo_id for this model
        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            # If no repo_id, fall back to basic validation
            self.logger.warning(
                f"No repo_id found for {self.model_name} - using basic file validation"
            )
            self._missing_files = None
            return self._verify_model_files(model_path)

        # Use llm_file_bootstrap_data as source of truth
        from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
            LLM_FILE_BOOTSTRAP_DATA,
        )

        if repo_id not in LLM_FILE_BOOTSTRAP_DATA:
            self.logger.warning(
                f"Model {repo_id} not in LLM_FILE_BOOTSTRAP_DATA - using basic file validation"
            )
            self._missing_files = None
            return self._verify_model_files(model_path)

        # Check which required files are missing or incomplete
        # files is a dict of {filename: expected_size}
        required_files = LLM_FILE_BOOTSTRAP_DATA[repo_id]["files"]
        missing_files = []

        for required_file, expected_size in required_files.items():
            file_path = os.path.join(model_path, required_file)
            if not os.path.exists(file_path):
                missing_files.append(required_file)
            elif expected_size > 0:
                # Check if file is complete by comparing size
                actual_size = os.path.getsize(file_path)
                if actual_size < expected_size:
                    self.logger.warning(
                        f"File {required_file} is incomplete: {actual_size} bytes vs expected {expected_size} bytes"
                    )
                    missing_files.append(required_file)

        if missing_files:
            self._missing_files = missing_files
            self.logger.info(
                f"Model incomplete - missing or incomplete {len(missing_files)} files: {missing_files[:5]}..."
            )
            return False

        self._missing_files = None
        return True

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
