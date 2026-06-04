"""Model property and configuration methods for LLM models.

This mixin provides:
- Model metadata properties (name, version, path)
- Model type detection (Mistral, LLaMA)
- Configuration properties (use_cache)
- Hardware queries (VRAM)
- Tool access
- LLM wrapper for RAG
"""

import os
from typing import List

from airunner_services.llm.config.provider_config import LLMProviderConfig
from airunner_services.model_management.hardware_profiler import (
    HardwareProfiler,
)


class PropertyMixin:
    """Mixin for LLM model properties and configuration."""

    @property
    def supports_function_calling(self) -> bool:
        """Check if the current model supports function calling.

        Returns:
            True if model supports function calling
        """
        try:
            saved_model_id = getattr(self.llm_generator_settings, "model_id", None)
            if saved_model_id:
                model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
                if model_info:
                    return model_info.get("function_calling", False)

            model_path = self.model_path
            if not model_path:
                return False

            for (
                model_key,
                model_info,
            ) in LLMProviderConfig.LOCAL_MODELS.items():
                if model_key in model_path or model_info["name"] in model_path:
                    return model_info.get("function_calling", False)

            return False
        except Exception as e:
            self.logger.warning(
                f"Could not determine function calling support: {e}"
            )
            return False

    @property
    def tools(self) -> List:
        """Get immediately-available tools from tool manager.
        
        Returns only tools with defer_loading=False to reduce context size.
        Deferred tools (defer_loading=True) can be discovered via the
        search_tools meta-tool, which is always included in immediate tools.

        Returns:
            List of immediate tools (not deferred)
        """
        if self._tool_manager:
            return self._tool_manager.get_immediate_tools()
        return []

    @property
    def is_mistral(self) -> bool:
        """Check if the current model is a Mistral model.

        Returns:
            True if the model is a Mistral model
        """
        if not self._current_model_path:
            return False
        path = self._current_model_path.lower()
        return "mistral" in path

    @property
    def is_llama_instruct(self) -> bool:
        """Check if the current model is a LLaMA instruct model.

        Returns:
            True if the model is a LLaMA instruct model
        """
        if not self._current_model_path:
            return False
        path = self._current_model_path.lower()
        return "instruct" in path and "llama" in path

    def _get_available_vram_gb(self) -> float:
        """Get available VRAM in gigabytes.

        Returns:
            Available VRAM in GB
        """
        if not hasattr(self, "_hw_profiler") or self._hw_profiler is None:
            self._hw_profiler = HardwareProfiler()
        return self._hw_profiler._get_available_vram_gb()

    @property
    def use_cache(self) -> bool:
        """Determine whether to use model caching based on settings.

        Returns:
            True if cache should be used
        """
        if self.llm_generator_settings.override_parameters:
            return self.llm_generator_settings.use_cache
        return self.chatbot.use_cache

    @property
    def model_version(self) -> str:
        """Get the model version to use based on settings.

        Returns:
            The model version identifier
        """
        model_version = self.chatbot.model_version
        if self.llm_generator_settings.override_parameters:
            model_version = self.llm_generator_settings.model_version
        return model_version

    @property
    def model_name(self) -> str:
        """Extract model name from model path.

        Returns:
            Model name (basename of path)

        Raises:
            ValueError: If no model path configured
        """
        requested_model = getattr(getattr(self, "llm_request", None), "model", None)
        if requested_model:
            resolved_model_id = LLMProviderConfig.resolve_model_id(
                "local",
                str(requested_model),
            )
            if resolved_model_id:
                model_info = LLMProviderConfig.get_model_info("local", resolved_model_id)
                if model_info:
                    return model_info.get("name", resolved_model_id)

        saved_model_id = getattr(self.llm_generator_settings, "model_id", None)
        if saved_model_id and saved_model_id != "custom":
            model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
            if model_info:
                return model_info.get("name", saved_model_id)

        # Use the resolved model_path so runtime overrides (LLMRequest.model)
        # and container path normalization are handled consistently.
        model_path = self.model_path
        if not model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )
        return os.path.basename(os.path.normpath(model_path))

    @property
    def llm(self):
        """Get the LLM for RAG system.

        This property is required by RAGMixin to initialize the RAG system.
        Returns None if the chat model hasn't been loaded yet.

        Returns:
            LangChain chat model or None
        """
        return self._chat_model

    @property
    def model_path(self) -> str:
        """Get the filesystem path to the model files from settings.

        Supports runtime model loading via LLMRequest.model field.
        If LLMRequest.model is set, constructs path from base_path/text/models/llm/causallm/{model}.
        Otherwise uses llm_generator_settings.model_path, constructing full path if needed.

        Returns:
            Absolute path to the model directory

        Raises:
            ValueError: If no model path is configured in settings or if
                       embedding model path is incorrectly used as main LLM
        """
        model_path = None
        if self.llm_request is not None and self.llm_request.model:
            # Request-level override:
            # - If the request provides a bare model name (e.g. "Qwen3.5-9B"),
            #   interpret it as a directory under base_path/text/models/llm/causallm.
            # - If the request provides an absolute/relative filesystem path
            #   (contains a path separator or points to a *.gguf), use it as-is
            #   and let the container path normalization below rewrite host paths
            #   like /home/<user>/.local/share/airunner/... to the container base.
            requested = str(self.llm_request.model)
            resolved_model_id = LLMProviderConfig.resolve_model_id(
                "local",
                requested,
            )
            if resolved_model_id:
                model_path = LLMProviderConfig.get_expected_local_artifact_path(
                    self.path_settings.base_path,
                    "local",
                    model_id=resolved_model_id,
                )
            elif (
                "/" in requested
                or "\\" in requested
                or requested.lower().endswith(".gguf")
            ):
                model_path = requested
            else:
                model_path = os.path.join(
                    self.path_settings.base_path,
                    "text/models/llm/causallm",
                    requested,
                )
        else:
            model_path = self.llm_generator_settings.model_path

        # Handle empty/None model_path by falling back to default
        # Empty string check is important for existing DB records
        if not model_path or (isinstance(model_path, str) and model_path.strip() == ""):
            from airunner_services.settings import AIRUNNER_DEFAULT_LLM_HF_PATH
            model_path = AIRUNNER_DEFAULT_LLM_HF_PATH
            self.logger.info("No model path configured, using default LLM model")
            
        if not model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )

        model_path = os.path.expanduser(model_path)

        # If a model path was persisted from a host user home (e.g. /home/<user>)
        # but we're running in a container with a different base path, rewrite
        # it to the configured AIRunner data dir.
        try:
            marker = os.path.join(os.sep, ".local", "share", "airunner") + os.sep
            if marker in model_path:
                suffix = model_path.split(marker, 1)[-1]
                if suffix and getattr(self.path_settings, "base_path", None):
                    model_path = os.path.join(self.path_settings.base_path, suffix)
        except Exception:
            pass

        resolved_model_id = LLMProviderConfig.resolve_model_id(
            "local",
            model_path,
        )
        if resolved_model_id and not os.path.isabs(model_path):
            model_path = LLMProviderConfig.get_expected_local_artifact_path(
                self.path_settings.base_path,
                "local",
                model_id=resolved_model_id,
            )
        
        # If model_path doesn't contain a path separator, it's just a model name
        # Construct the full path
        if "/" not in model_path and "\\" not in model_path:
            if resolved_model_id:
                model_path = LLMProviderConfig.get_expected_local_artifact_path(
                    self.path_settings.base_path,
                    "local",
                    model_id=resolved_model_id,
                )
            else:
                model_path = os.path.join(
                    self.path_settings.base_path,
                    "text/models/llm/causallm",
                    model_path,
                )

        saved_model_id = getattr(self.llm_generator_settings, "model_id", None)
        if saved_model_id and saved_model_id != "custom":
            expected_artifact_path = LLMProviderConfig.get_expected_local_artifact_path(
                self.path_settings.base_path,
                "local",
                model_id=saved_model_id,
            )
            recovered_path = expected_artifact_path
            if (
                expected_artifact_path.lower().endswith(".gguf")
                and os.path.exists(expected_artifact_path)
                and not (model_path.lower().endswith(".gguf") and os.path.exists(model_path))
                and os.path.normpath(model_path) != os.path.normpath(recovered_path)
            ):
                self.logger.info(
                    "Recovered stale local model path '%s' to expected GGUF artifact '%s'",
                    model_path,
                    recovered_path,
                )
                self.llm_generator_settings.model_path = recovered_path
                model_path = recovered_path

        # Validate that the embedding model path is not used as main LLM
        if "intfloat/e5-large" in model_path or "/embedding/" in model_path:
            raise ValueError(
                f"Invalid model path: '{model_path}' appears to be an embedding model. "
                "Please configure a proper chat LLM model in LLM settings."
            )

        # Validate that SD/art model paths are not used as main LLM
        if "/art/models/" in model_path or "/txt2img" in model_path or "/inpaint" in model_path:
            self.logger.error(
                f"Invalid model path detected: '{model_path}' appears to be an SD/art model. "
                "Attempting to recover from model_id..."
            )
            
            # Try to recover using saved model_id
            saved_model_id = getattr(self.llm_generator_settings, "model_id", None)
            if saved_model_id and saved_model_id != "custom":
                model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
                if model_info:
                    recovered_path = LLMProviderConfig.get_expected_local_artifact_path(
                        self.path_settings.base_path,
                        "local",
                        model_id=saved_model_id,
                    )
                    self.logger.info(f"Recovered model path from model_id '{saved_model_id}': {recovered_path}")
                    # Save the corrected path
                    self.llm_generator_settings.model_path = recovered_path
                    return recovered_path
            
            # No recovery possible - clear and raise
            self.llm_generator_settings.model_path = ""
            raise ValueError(
                "LLM model path was corrupted (contained SD/art model path). "
                "Please select an LLM model from the dropdown."
            )

        # Validate that TTS model paths are not used as main LLM
        if "/tts/" in model_path or "/openvoice" in model_path:
            self.logger.error(
                f"Invalid model path detected: '{model_path}' appears to be a TTS model. "
                "Attempting to recover from model_id..."
            )
            
            # Try to recover using saved model_id
            saved_model_id = getattr(self.llm_generator_settings, "model_id", None)
            if saved_model_id and saved_model_id != "custom":
                model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
                if model_info:
                    recovered_path = LLMProviderConfig.get_expected_local_artifact_path(
                        self.path_settings.base_path,
                        "local",
                        model_id=saved_model_id,
                    )
                    self.logger.info(f"Recovered model path from model_id '{saved_model_id}': {recovered_path}")
                    # Save the corrected path
                    self.llm_generator_settings.model_path = recovered_path
                    return recovered_path
            
            # No recovery possible - clear and raise
            self.llm_generator_settings.model_path = ""
            raise ValueError(
                "LLM model path was corrupted (contained TTS path). "
                "Please select an LLM model from the dropdown."
            )

        return model_path
