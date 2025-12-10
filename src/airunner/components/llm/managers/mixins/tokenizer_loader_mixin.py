"""Tokenizer loading mixin for LLM model manager.

This mixin handles tokenizer initialization for various model types,
including special handling for Mistral3 models and fallback strategies.
"""

import os
import traceback
from typing import TYPE_CHECKING

from transformers import AutoTokenizer, AutoConfig

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.components.llm.utils.ministral3_config_patcher import (
    patch_ministral3_config,
    is_ministral3_model,
)

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

        Uses path-based detection since config model_type is patched
        from 'ministral3' to 'mistral' for transformers compatibility.

        Args:
            config: AutoConfig object from the model.

        Returns:
            True if model is Mistral3, False otherwise.
        """
        # Primary check: use path-based detection (works with patched config)
        if is_ministral3_model(self.model_path):
            return True
        
        # Fallback: check architecture list (preserved after patching)
        is_mistral3_arch = hasattr(config, "architectures") and any(
            "Mistral3" in arch for arch in (config.architectures or [])
        )
        return is_mistral3_arch

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
        # Detect if this is a Mistral model that needs regex fix
        is_mistral = "mistral" in self.model_path.lower() if self.model_path else False
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

    def _load_slow_tokenizer(self: "LLMModelManager", extra_kwargs: dict = None) -> None:
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

        Handles different tokenizer types:
        - Mistral3: Uses mistral_common (tekken.json) for encoding, but
                    ALSO loads HuggingFace tokenizer for streaming decode
        - Standard: HuggingFace AutoTokenizer with fallbacks

        Sets use_default_system_prompt=False for loaded tokenizers.
        """
        if self._tokenizer is not None:
            return

        try:
            config = self._load_model_config()

            if self._is_mistral3_config(config):
                # Validate tekken.json exists for mistral_common encoding
                self._handle_mistral3_tokenizer()
                # ALSO load HuggingFace tokenizer for TextIteratorStreamer decoding
                self._load_standard_tokenizer()
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
        # Patch Ministral3 config if needed before loading
        if is_ministral3_model(self.model_path):
            patch_ministral3_config(self.model_path)
        
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
