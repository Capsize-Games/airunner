"""Tokenizer loading mixin for LLM model manager.

This mixin handles tokenizer initialization for various model types,
including fallback strategies for tokenizer compatibility.
"""

import os
import traceback
from typing import TYPE_CHECKING

from transformers import AutoTokenizer, AutoConfig

from airunner_services.settings import AIRUNNER_LOCAL_FILES_ONLY

if TYPE_CHECKING:
    from airunner_services.model_management.llm_model_manager import (
        LLMModelManager,
    )


class TokenizerLoaderMixin:
    """Mixin for loading and configuring tokenizers.

    Handles tokenizer initialization with fallback strategies for
    different model types.
    """

    def _load_standard_tokenizer(self: "LLMModelManager") -> None:
        """Load standard HuggingFace tokenizer with fallbacks.

        Attempts to load tokenizer without trust_remote_code first,
        falls back to trusted mode if that fails.
        """
        is_mistral = (
            "mistral" in self.model_path.lower()
            if self.model_path
            else False
        )
        extra_kwargs = {"fix_mistral_regex": True} if is_mistral else {}

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=False,
                **extra_kwargs,
            )
        except (KeyError, Exception) as e:
            self.logger.warning(
                f"Failed to load tokenizer with trust_remote_code=False: "
                f"{type(e).__name__}"
            )
            self._load_tokenizer_with_trust_remote_code(extra_kwargs)

    def _load_tokenizer_with_trust_remote_code(
        self: "LLMModelManager",
        extra_kwargs: dict = None,
    ) -> None:
        """Load tokenizer with trust_remote_code=True and fallbacks.

        Used when standard loading fails. Falls back to slow tokenizer
        if KeyError occurs (tokenizer class not in mapping).
        
        Args:
            extra_kwargs: Additional kwargs to pass to from_pretrained.
        """
        if extra_kwargs is None:
            extra_kwargs = {}
        self.logger.info("Retrying with trust_remote_code=True")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
                **extra_kwargs,
            )
        except KeyError as ke:
            self.logger.warning(
                f"Tokenizer class not in TOKENIZER_MAPPING: "
                f"{type(ke).__name__}"
            )
            self._load_slow_tokenizer(extra_kwargs)

    def _load_slow_tokenizer(
        self: "LLMModelManager",
        extra_kwargs: dict = None,
    ) -> None:
        """Load slow tokenizer as final fallback.

        Slow tokenizers are Python-based rather than Rust-based,
        guaranteed to work but slower than fast tokenizers.
        
        Args:
            extra_kwargs: Additional kwargs to pass to from_pretrained.
        """
        if extra_kwargs is None:
            extra_kwargs = {}
        self.logger.info("Trying with use_fast=False to use slow tokenizer")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
            use_fast=False,
            **extra_kwargs,
        )

    def _load_tokenizer(self: "LLMModelManager") -> None:
        """Load the tokenizer for the selected model.

        Sets use_default_system_prompt=False for loaded tokenizers.
        """
        if self._tokenizer is not None:
            return

        try:
            self._load_model_config()
            self._load_standard_tokenizer()

            self._configure_loaded_tokenizer()

        except Exception as e:
            self._handle_tokenizer_error(e)

    def _load_model_config(self: "LLMModelManager") -> AutoConfig:
        """Load model configuration for tokenizer setup.

        Returns:
            AutoConfig object with model configuration.
        """
        config = AutoConfig.from_pretrained(
            self.model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )
        # Align tokenizer limits with YaRN/target context if available
        if hasattr(self, "_apply_context_settings"):
            try:
                self._apply_context_settings(config)
            except Exception as e:
                self.logger.warning(
                    f"Failed to apply context settings to tokenizer config: {e}"
                )

        return config

    def _configure_loaded_tokenizer(self: "LLMModelManager") -> None:
        """Configure tokenizer after successful loading.

        Disables default system prompt if tokenizer was loaded.
        """
        if self._tokenizer:
            self._tokenizer.use_default_system_prompt = False

            target_ctx = getattr(self, "_target_context_length", None)
            if target_ctx and hasattr(self._tokenizer, "model_max_length"):
                self._tokenizer.model_max_length = target_ctx

    def _handle_tokenizer_error(
        self: "LLMModelManager", error: Exception
    ) -> None:
        """Handle tokenizer loading errors.

        Args:
            error: The exception that occurred during loading.
        """
        self.logger.error(
            f"Error loading tokenizer: {type(error).__name__}: {str(error)}"
        )
        self.logger.error(f"Tokenizer traceback:\n{traceback.format_exc()}")
        self._tokenizer = None
        self.logger.error("Tokenizer failed to load")
