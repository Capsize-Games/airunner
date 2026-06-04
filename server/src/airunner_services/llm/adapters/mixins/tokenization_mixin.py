"""Tokenization operations for HuggingFace chat models."""

import os

# Mistral native function calling support
try:
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    MistralTokenizer = None


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
            print("No model path provided for Mistral tokenizer")
            return

        tekken_path = os.path.join(self.model_path, "tekken.json")
        if not os.path.exists(tekken_path):
            print(f"tekken.json not found at {tekken_path}")
            return

        if not self._validate_special_tokens():
            return

        self._load_mistral_tokenizer(tekken_path)

    def _check_mistral_availability(self) -> bool:
        """Check if Mistral library is available.

        Returns:
            True if Mistral common library is available
        """
        if not MISTRAL_AVAILABLE:
            print("Mistral common library not available")
            return False
        return True

    def _validate_special_tokens(self) -> bool:
        """Validate that tokenizer has Mistral function calling tokens.

        Returns:
            True if tokenizer supports function calling
        """
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
        """Log warning when tokenizer doesn't support function calling.

        Args:
            special_tokens: List of special tokens in tokenizer
        """
        print("⚠ Mistral native function calling NOT supported by this model:")
        print(
            f"   → Uses {type(self.tokenizer).__name__} with only {len(special_tokens)} special tokens"
        )
        print(
            "   → Needs Mistral V3-Tekken tokenizer with function calling tokens"
        )
        print(
            "   → Quantized models often lose native function calling capability"
        )
        print("   → Falling back to prompt-based tool calling")

    def _load_mistral_tokenizer(self, tekken_path: str) -> None:
        """Load Mistral tokenizer from tekken.json file.

        Args:
            tekken_path: Path to tekken.json file
        """
        try:
            self._mistral_tokenizer = MistralTokenizer.from_file(tekken_path)
            self.use_mistral_native = True
            print(
                f"✓ Mistral native function calling ENABLED for model at {self.model_path}"
            )
        except Exception as e:
            print(f"Failed to load Mistral tokenizer: {e}")
            self.use_mistral_native = False
