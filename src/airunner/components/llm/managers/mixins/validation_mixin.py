"""Validation mixin for LLM model manager.

This mixin handles model path validation, existence checking, and component
loading verification for the LLM model manager.
"""

import os
from typing import TYPE_CHECKING, List

from airunner.components.llm.adapters import is_gguf_model
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.utils.settings.get_qsettings import get_qsettings

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
        
        For GGUF models (when GGUF quantization is selected), checks for GGUF files
        instead of safetensors. This allows using GGUF models even when safetensor
        files have been deleted.

        Returns:
            True if model exists with required files, False otherwise.
        """
        if not self.llm_settings.use_local_llm:
            return True

        model_path = self.model_path
        if not os.path.exists(model_path):
            self.logger.info(f"Model path does not exist: {model_path}")
            self._missing_files = None  # Full download needed
            self._missing_gguf = False
            return False

        # Check if GGUF quantization is selected (quantization_bits == 0 is GGUF)
        gguf_selected = self._is_gguf_quantization_selected()
        
        if gguf_selected:
            # GGUF mode: check for GGUF file instead of safetensors
            if is_gguf_model(model_path):
                self.logger.info(f"GGUF model found at {model_path}")
                self._missing_files = None
                self._missing_gguf = False
                return True
            else:
                # GGUF selected but no GGUF file - trigger GGUF download
                self.logger.info(
                    f"GGUF quantization selected but no GGUF file found at {model_path}"
                )
                self._missing_files = None
                self._missing_gguf = True
                return False

        # Normal mode: check safetensors using bootstrap data
        # Get repo_id for this model
        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            # If no repo_id, fall back to basic validation
            self.logger.warning(
                f"No repo_id found for {self.model_name} - using basic file validation"
            )
            self._missing_files = None
            self._missing_gguf = False
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
            self._missing_gguf = False
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
            self._missing_gguf = False
            self.logger.info(
                f"Model incomplete - missing or incomplete {len(missing_files)} files: {missing_files[:5]}..."
            )
            return False

        self._missing_files = None
        self._missing_gguf = False
        return True
    
    def _is_gguf_quantization_selected(self: "LLMModelManager") -> bool:
        """Check if GGUF quantization is selected AND supported for this model.
        
        GGUF uses quantization_bits == 0 as a sentinel value.
        However, some models (like Ministral 3) don't support GGUF yet due to
        architecture limitations in llama-cpp-python.
        
        Returns:
            True if GGUF quantization is selected AND the model supports GGUF.
        """
        # First check if the model supports GGUF
        if not self._model_supports_gguf():
            return False
            
        try:
            qs = get_qsettings()
            saved = qs.value("llm_settings/quantization_bits", None)
            if saved is not None:
                return int(saved) == 0
        except Exception as e:
            self.logger.warning(f"Error reading quantization setting: {e}")
        # Default to GGUF if model supports it
        return True

    def _model_supports_gguf(self: "LLMModelManager") -> bool:
        """Check if the current model supports GGUF format.
        
        This checks the provider config to see if GGUF repo/filename is configured.
        Models without GGUF config (like Ministral 3) will use transformers instead.
        
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

    def _trigger_model_download(self: "LLMModelManager") -> bool:
        """Trigger model download via signal.

        Emits signal to download manager to fetch model from HuggingFace.
        For GGUF models (when _missing_gguf is True), triggers GGUF-specific download.

        Returns:
            False to indicate model is not yet available.
        """
        self.logger.info(
            f"Model not found at {self.model_path}, triggering download"
        )

        # Check if we need to download GGUF
        if hasattr(self, "_missing_gguf") and self._missing_gguf:
            return self._trigger_gguf_download()

        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            return False

        self._emit_download_signal(repo_id)
        return False
    
    def _trigger_gguf_download(self: "LLMModelManager") -> bool:
        """Trigger GGUF model download or conversion.
        
        First checks if a pre-quantized GGUF is available for download.
        If not, checks if safetensors exist and can be converted to GGUF.
        
        Returns:
            False to indicate model is not yet available.
        """
        # Get model_id for this model
        model_id = self._get_model_id_for_model()
        if not model_id:
            self.logger.error(
                f"Could not find model_id for model: {self.model_name}"
            )
            return False
        
        # Get GGUF info - check if pre-quantized GGUF is available
        gguf_info = LLMProviderConfig.get_gguf_info("local", model_id)
        
        if gguf_info:
            # Pre-quantized GGUF available - download it
            self.logger.info(
                f"Triggering GGUF download: {gguf_info['repo_id']} / {gguf_info['filename']}"
            )
            
            signal_data = {
                "model_path": self.model_path,
                "model_name": self.model_name,
                "repo_id": gguf_info["repo_id"],
                "gguf_filename": gguf_info["filename"],
                "model_type": "gguf",
                "quantization_bits": 0,
            }
            
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                signal_data,
            )
            return False
        
        # No pre-quantized GGUF available - check if we can convert from safetensors
        return self._try_convert_safetensors_to_gguf()
    
    def _try_convert_safetensors_to_gguf(self: "LLMModelManager") -> bool:
        """Attempt to convert existing safetensors to GGUF format.
        
        If safetensors exist at model_path, triggers conversion to GGUF.
        If safetensors don't exist, triggers safetensors download first.
        
        Returns:
            False to indicate model is not yet available.
        """
        from airunner.utils.model_optimizer import get_model_optimizer
        
        model_path = self.model_path
        
        # Check if safetensors exist
        safetensor_files = list(
            f for f in os.listdir(model_path) 
            if f.endswith('.safetensors')
        ) if os.path.exists(model_path) else []
        
        if safetensor_files:
            # Safetensors exist - convert to GGUF
            self.logger.info(
                f"No GGUF available for download. Converting safetensors to GGUF..."
            )
            
            optimizer = get_model_optimizer()
            
            # Check if conversion tools are available
            if not optimizer.has_llama_cpp_convert():
                self.logger.error(
                    "GGUF conversion requires llama.cpp tools. "
                    "Install with: pip install llama-cpp-python "
                    "or clone llama.cpp from https://github.com/ggerganov/llama.cpp"
                )
                # Emit signal to notify user
                self.emit_signal(
                    SignalCode.APPLICATION_SETTINGS_ERROR,
                    {
                        "error": "GGUF Conversion Not Available",
                        "message": (
                            "No pre-quantized GGUF model is available for this model, "
                            "and automatic conversion requires llama.cpp tools.\n\n"
                            "Options:\n"
                            "1. Install llama-cpp-python: pip install llama-cpp-python\n"
                            "2. Clone llama.cpp and build convert tools\n"
                            "3. Choose a different model with GGUF support\n"
                            "4. Disable GGUF quantization in settings"
                        ),
                    },
                )
                return False
            
            # Emit signal to trigger conversion (async in worker)
            self.emit_signal(
                SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL,
                {
                    "model_path": model_path,
                    "model_name": self.model_name,
                    "quantization": "Q4_K_M",
                },
            )
            return False
        
        # No safetensors - need to download them first
        self.logger.info(
            f"No GGUF available and no safetensors found. Downloading safetensors first..."
        )
        repo_id = self._get_repo_id_for_model()
        if repo_id:
            # Download safetensors, then convert
            signal_data = {
                "model_path": model_path,
                "model_name": self.model_name,
                "repo_id": repo_id,
                "model_type": "safetensors",
                "convert_to_gguf": True,  # Flag to trigger conversion after download
            }
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                signal_data,
            )
        return False
    
    def _get_model_id_for_model(self: "LLMModelManager") -> str:
        """Get model ID for current model.

        Returns:
            Model ID string, or empty string if not found.
        """
        for model_id, model_info in LLMProviderConfig.LOCAL_MODELS.items():
            if model_info["name"] == self.model_name:
                return model_id

        self.logger.error(
            f"Could not find model_id for model: {self.model_name}"
        )
        return ""

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
        For GGUF models, only chat model and workflow manager are required
        since GGUF handles model/tokenizer internally.

        Returns:
            True if all required components are loaded.
        """
        # Check if GGUF mode - only need chat_model and workflow_manager
        if self._is_gguf_quantization_selected():
            return (
                self._chat_model is not None
                and self._workflow_manager is not None
            )
        
        # Standard HuggingFace mode - need all components
        return (
            self._model is not None
            and self._tokenizer is not None
            and self._chat_model is not None
            and self._workflow_manager is not None
        )
