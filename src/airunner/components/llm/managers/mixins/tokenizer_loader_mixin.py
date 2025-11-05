"""Tokenizer loading mixin for LLM model manager.

This mixin handles tokenizer initialization for various model types,
including special handling for Mistral3 models and fallback strategies.
"""

import os
import traceback
from typing import TYPE_CHECKING

from transformers import AutoTokenizer, AutoConfig

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY

if TYPE_CHECKING:
    from airunner.components.llm.managers.llm_model_manager import (
        LLMModelManager,
    )


class TokenizerLoaderMixin:
    """Mixin for loading and configuring tokenizers.

    Handles tokenizer initialization with fallback strategies for
    different model types, including special Mistral3 support.
    """

    def _is_mistral3_config(
        self: "LLMModelManager", config: AutoConfig
    ) -> bool:
        """Check if config indicates Mistral3 model.

        Args:
            config: AutoConfig object from the model.

        Returns:
            True if model is Mistral3, False otherwise.
        """
        is_mistral3_type = (
            hasattr(config, "model_type") and config.model_type == "mistral3"
        )
        is_mistral3_arch = hasattr(config, "architectures") and any(
            "Mistral3" in arch for arch in (config.architectures or [])
        )
        return is_mistral3_type or is_mistral3_arch

    def _handle_mistral3_tokenizer(self: "LLMModelManager") -> bool:
        """Handle Mistral3 Tekken tokenizer setup.

        Mistral3 uses mistral_common for tokenization instead of
        HuggingFace tokenizers. Validates tekken.json exists.

        Returns:
            True if Mistral3 tokenizer handled successfully.

        Raises:
            FileNotFoundError: If tekken.json is missing.
        """
        self.logger.info(
            "Detected Mistral3 model - tokenizer will be handled by "
            "chat adapter using mistral_common"
        )

        tekken_path = os.path.join(self.model_path, "tekken.json")
        if not os.path.exists(tekken_path):
            raise FileNotFoundError(
                f"tekken.json not found at {tekken_path}. "
                f"Ensure the model is fully downloaded."
            )

        self.logger.info(
            f"✓ Found tekken.json at {tekken_path} - "
            "will use mistral_common for tokenization"
        )
        return True

    def _load_standard_tokenizer(self: "LLMModelManager") -> None:
        """Load standard HuggingFace tokenizer with fallbacks.

        Attempts to load tokenizer without trust_remote_code first,
        falls back to trusted mode if that fails.
        """
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=False,
            )
        except (KeyError, Exception) as e:
            self.logger.warning(
                f"Failed to load tokenizer with trust_remote_code=False: "
                f"{type(e).__name__}"
            )
            self._load_tokenizer_with_trust_remote_code()

    def _load_tokenizer_with_trust_remote_code(
        self: "LLMModelManager",
    ) -> None:
        """Load tokenizer with trust_remote_code=True and fallbacks.

        Used when standard loading fails. Falls back to slow tokenizer
        if KeyError occurs (tokenizer class not in mapping).
        """
        self.logger.info("Retrying with trust_remote_code=True")
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
            )
        except KeyError as ke:
            self.logger.warning(
                f"Tokenizer class not in TOKENIZER_MAPPING: "
                f"{type(ke).__name__}"
            )
            self._load_slow_tokenizer()

    def _load_slow_tokenizer(self: "LLMModelManager") -> None:
        """Load slow tokenizer as final fallback.

        Slow tokenizers are Python-based rather than Rust-based,
        guaranteed to work but slower than fast tokenizers.
        """
        self.logger.info("Trying with use_fast=False to use slow tokenizer")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
            use_fast=False,
        )

    def _load_tokenizer(self: "LLMModelManager") -> None:
        """Load the tokenizer for the selected model.

        Handles different tokenizer types:
        - Mistral3: Uses mistral_common (tekken.json)
        - Standard: HuggingFace AutoTokenizer with fallbacks

        Sets use_default_system_prompt=False for loaded tokenizers.
        """
        if self._tokenizer is not None:
            return

        try:
            config = self._load_model_config()

            if self._is_mistral3_config(config):
                if self._handle_mistral3_tokenizer():
                    return
            else:
                self._load_standard_tokenizer()

            self._configure_loaded_tokenizer()

        except Exception as e:
            self._handle_tokenizer_error(e)

    def _load_model_config(self: "LLMModelManager") -> AutoConfig:
        """Load model configuration for tokenizer setup.

        Returns:
            AutoConfig object with model configuration.
        """
        return AutoConfig.from_pretrained(
            self.model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )

    def _configure_loaded_tokenizer(self: "LLMModelManager") -> None:
        """Configure tokenizer after successful loading.

        Disables default system prompt if tokenizer was loaded.
        """
        if self._tokenizer:
            self._tokenizer.use_default_system_prompt = False

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
