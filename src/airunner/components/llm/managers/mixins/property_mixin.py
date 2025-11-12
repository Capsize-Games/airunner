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

from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner.components.model_management.hardware_profiler import (
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
        """Get all available tools from tool manager.

        Returns:
            List of available tools
        """
        if self._tool_manager:
            return self._tool_manager.get_all_tools()
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
        if not self.llm_generator_settings.model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )
        return os.path.basename(
            os.path.normpath(self.llm_generator_settings.model_path)
        )

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

        Returns:
            Absolute path to the model directory

        Raises:
            ValueError: If no model path is configured in settings or if
                       embedding model path is incorrectly used as main LLM
        """
        if not self.llm_generator_settings.model_path:
            raise ValueError(
                "No model path configured. Please select a model in LLM settings."
            )

        model_path = os.path.expanduser(self.llm_generator_settings.model_path)

        # Validate that the embedding model path is not used as main LLM
        if "intfloat/e5-large" in model_path or "/embedding/" in model_path:
            raise ValueError(
                f"Invalid model path: '{model_path}' appears to be an embedding model. "
                "Please configure a proper chat LLM model in LLM settings."
            )

        return model_path
