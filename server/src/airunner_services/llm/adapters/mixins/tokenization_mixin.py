"""Tokenization operations for HuggingFace chat models."""

import logging
import os

# Mistral native function calling support
try:
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    MistralTokenizer = None

_logger = logging.getLogger(__name__)


class TokenizationMixin:
    """Handles Mistral tokenizer initialization for chat models.

    This mixin provides functionality for:
    - Detecting Mistral native function calling support
    - Initializing Mistral tokenizer with tekken.json
    - Validating special tokens for function calling
    """

    def _init_mistral_tokenizer(self) -> None:
        """Initialize Mistral native tokenizer if available."""
        if not self._check_mistral_availability():
            return

        if not self.model_path:
            _logger.warning("No model path provided for Mistral tokenizer")
            return

        tekken_path = os.path.join(self.model_path, "tekken.json")
        if not os.path.exists(tekken_path):
            _logger.warning("tekken.json not found at %s", tekken_path)
            return

        if not self._validate_special_tokens():
            return

        self._load_mistral_tokenizer(tekken_path)

    def _check_mistral_availability(self) -> bool:
        """Check if Mistral library is available."""
        if not MISTRAL_AVAILABLE:
            _logger.debug("Mistral common library not available")
            return False
        return True

    def _validate_special_tokens(self) -> bool:
        """Validate that tokenizer has Mistral function calling tokens."""
        if not hasattr(self.tokenizer, "all_special_tokens"):
            return True

        special_tokens = self.tokenizer.all_special_tokens
        has_tool_tokens = any(
            "tool" in str(token).lower() for token in special_tokens
        )

        if not has_tool_tokens and len(special_tokens) < 10:
            self._log_unsupported_tokenizer(special_tokens)
            self.use_mistral_native = False
            return False

        return True

    def _log_unsupported_tokenizer(self, special_tokens: list) -> None:
        """Log warning when tokenizer doesn't support function calling."""
        _logger.warning(
            "Mistral native function calling NOT supported: %s has only %d "
            "special tokens; needs Mistral V3-Tekken tokenizer. "
            "Falling back to prompt-based tool calling.",
            type(self.tokenizer).__name__,
            len(special_tokens),
        )

    def _load_mistral_tokenizer(self, tekken_path: str) -> None:
        """Load Mistral tokenizer from tekken.json file."""
        try:
            self._mistral_tokenizer = MistralTokenizer.from_file(tekken_path)
            self.use_mistral_native = True
            _logger.info(
                "Mistral native function calling ENABLED for model at %s",
                self.model_path,
            )
        except Exception as e:
            _logger.warning("Failed to load Mistral tokenizer: %s", e)
            self.use_mistral_native = False
