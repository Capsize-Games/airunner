"""Model availability checks and download triggers for local LLMs."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from airunner_services.llm.adapters import is_gguf_model
from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.contract_enums import ModelType, ModelStatus, SignalCode

if TYPE_CHECKING:
    from airunner_services.model_management.llm_model_manager import (
        LLMModelManager,
    )


class ModelAvailabilityMixin:
    """Check model artifacts and trigger downloads when needed."""

    def _check_model_exists(self: "LLMModelManager") -> bool:
        """Check whether the current local model has usable artifacts."""
        if not self.llm_settings.use_local_llm:
            return True

        model_path = self.model_path
        if not os.path.exists(model_path):
            self.logger.info("Configured model path does not exist")
            self._missing_files = None
            self._missing_gguf = False
            return False

        expected_gguf_path = self._get_expected_gguf_path()
        if expected_gguf_path and os.path.exists(expected_gguf_path):
            self.logger.info(
                "Expected GGUF model found "
                "(preferring GGUF; skipping safetensors validation)"
            )
            self._missing_files = None
            self._missing_gguf = False
            return True

        if expected_gguf_path is None and is_gguf_model(model_path):
            self.logger.info(
                "GGUF model found "
                "(preferring GGUF; skipping safetensors validation)"
            )
            self._missing_files = None
            self._missing_gguf = False
            return True

        gguf_selected = self._is_gguf_quantization_selected()
        if gguf_selected:
            if expected_gguf_path and os.path.exists(expected_gguf_path):
                self.logger.info("GGUF model found")
                self._missing_files = None
                self._missing_gguf = False
                return True
            if expected_gguf_path is None and is_gguf_model(model_path):
                self.logger.info("GGUF model found")
                self._missing_files = None
                self._missing_gguf = False
                return True

            self.logger.info(
                "GGUF quantization selected but no GGUF file found",
            )
            self._missing_files = None
            self._missing_gguf = True
            return False

        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            self.logger.warning(
                "No repo_id found for %s - using basic file validation",
                self.model_name,
            )
            self._missing_files = None
            self._missing_gguf = False
            return self._verify_model_files(model_path)

        from airunner_services.database.bootstrap.llm_file_bootstrap_data import (
            LLM_FILE_BOOTSTRAP_DATA,
        )

        if repo_id not in LLM_FILE_BOOTSTRAP_DATA:
            self.logger.warning(
                "Model %s not in LLM_FILE_BOOTSTRAP_DATA - using basic file "
                "validation",
                repo_id,
            )
            self._missing_files = None
            self._missing_gguf = False
            return self._verify_model_files(model_path)

        required_files = LLM_FILE_BOOTSTRAP_DATA[repo_id]["files"]
        missing_files = []
        for required_file, expected_size in required_files.items():
            file_path = os.path.join(model_path, required_file)
            if not os.path.exists(file_path):
                missing_files.append(required_file)
                continue
            if expected_size <= 0:
                continue
            actual_size = os.path.getsize(file_path)
            if actual_size < expected_size:
                self.logger.warning(
                    "File %s is incomplete: %s bytes vs expected %s bytes",
                    required_file,
                    actual_size,
                    expected_size,
                )
                missing_files.append(required_file)

        if missing_files:
            self._missing_files = missing_files
            self._missing_gguf = False
            self.logger.info(
                "Model incomplete - missing or incomplete %s files: %s...",
                len(missing_files),
                missing_files[:5],
            )
            return False

        self._missing_files = None
        self._missing_gguf = False
        return True

    def _trigger_model_download(self: "LLMModelManager") -> bool:
        """Trigger model download or GGUF conversion when artifacts are absent."""
        expected_gguf_path = self._get_expected_gguf_path()
        if expected_gguf_path and os.path.exists(expected_gguf_path):
            self.logger.info(
                "Expected GGUF model present at %s; skipping download trigger",
                expected_gguf_path,
            )
            return False

        if expected_gguf_path is None and is_gguf_model(self.model_path):
            self.logger.info(
                "GGUF model present at %s; skipping download trigger",
                self.model_path,
            )
            return False

        self.logger.info(
            "Model not found at %s, triggering download",
            self.model_path,
        )
        if getattr(self, "_missing_gguf", False):
            return self._trigger_gguf_download()

        repo_id = self._get_repo_id_for_model()
        if not repo_id:
            return False

        self._emit_download_signal(repo_id)
        return False

    def _trigger_gguf_download(self: "LLMModelManager") -> bool:
        """Download a vendor GGUF or trigger safetensors conversion."""
        model_id = self._get_model_id_for_model()
        if not model_id:
            self.logger.error(
                "Could not find model_id for model: %s",
                self.model_name,
            )
            return False

        gguf_info = LLMProviderConfig.get_gguf_info("local", model_id)
        if gguf_info:
            self.logger.info(
                "Triggering GGUF download: %s / %s",
                gguf_info["repo_id"],
                gguf_info["filename"],
            )
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                {
                    "model_path": self.model_path,
                    "model_name": self.model_name,
                    "repo_id": gguf_info["repo_id"],
                    "gguf_filename": gguf_info["filename"],
                    "model_type": "gguf",
                    "quantization_bits": 0,
                },
            )
            return False

        return self._try_convert_safetensors_to_gguf()

    def _try_convert_safetensors_to_gguf(self: "LLMModelManager") -> bool:
        """Convert local safetensors to GGUF when no GGUF download exists."""
        from airunner_services.utils.model_optimizer import get_model_optimizer

        model_path = self.model_path
        safetensor_files = []
        if os.path.exists(model_path):
            safetensor_files = [
                file_name
                for file_name in os.listdir(model_path)
                if file_name.endswith(".safetensors")
            ]

        if safetensor_files:
            self.logger.info(
                "No GGUF available for download. Converting safetensors to "
                "GGUF..."
            )
            optimizer = get_model_optimizer()
            if not optimizer.has_llama_cpp_convert():
                self.logger.error(
                    "GGUF conversion requires llama.cpp tools. Install with: "
                    "pip install llama-cpp-python or clone llama.cpp from "
                    "https://github.com/ggerganov/llama.cpp"
                )
                self.emit_signal(
                    SignalCode.APPLICATION_SETTINGS_ERROR,
                    {
                        "error": "GGUF Conversion Not Available",
                        "message": (
                            "No pre-quantized GGUF model is available for "
                            "this model, and automatic conversion requires "
                            "llama.cpp tools.\n\nOptions:\n"
                            "1. Install llama-cpp-python: pip install "
                            "llama-cpp-python\n"
                            "2. Clone llama.cpp and build convert tools\n"
                            "3. Choose a different model with GGUF support\n"
                            "4. Disable GGUF quantization in settings"
                        ),
                    },
                )
                return False

            self.emit_signal(
                SignalCode.LLM_CONVERT_TO_GGUF_SIGNAL,
                {
                    "model_path": model_path,
                    "model_name": self.model_name,
                    "quantization": "Q4_K_M",
                },
            )
            return False

        self.logger.info(
            "No GGUF available and no safetensors found. Downloading "
            "safetensors first..."
        )
        repo_id = self._get_repo_id_for_model()
        if repo_id:
            self.emit_signal(
                SignalCode.LLM_MODEL_DOWNLOAD_REQUIRED,
                {
                    "model_path": model_path,
                    "model_name": self.model_name,
                    "repo_id": repo_id,
                    "model_type": "safetensors",
                    "convert_to_gguf": True,
                },
            )
        return False

    def _check_components_loaded_for_local(self: "LLMModelManager") -> bool:
        """Check if local-mode components are ready for generation."""
        if self._is_gguf_quantization_selected():
            return (
                self._chat_model is not None
                and self._workflow_manager is not None
            )

        has_model = self._model is not None
        has_tokenizer = self._tokenizer is not None
        if hasattr(self, "_local_execution_component_state"):
            has_model, has_tokenizer = (
                self._local_execution_component_state()
            )
        if self._is_mistral3_model():
            has_tokenizer = True

        return (
            has_model
            and has_tokenizer
            and self._chat_model is not None
            and self._workflow_manager is not None
        )

    def _handle_missing_model(self: "LLMModelManager") -> None:
        """Handle a missing model by triggering download once."""
        if self.model_status[ModelType.LLM] != ModelStatus.FAILED:
            self._trigger_model_download()
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)