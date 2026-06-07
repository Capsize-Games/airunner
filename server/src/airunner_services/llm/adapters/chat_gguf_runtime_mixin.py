"""Runtime-loading mixin for the GGUF chat adapter."""

from typing import Any, Dict, Optional

from airunner_services.llm.adapters.chat_gguf_model_loading import (
    load_model,
)
from airunner_services.llm.adapters.chat_gguf_model_runtime_config import (
    apply_runtime_env_overrides,
    context_retry_sequence,
    format_llama_tuning,
    llama_kwargs_for_context,
    load_llama_with_context_fallback,
    next_retry_context,
    resolve_llama_tuning,
    should_retry_context,
)


class ChatGGUFRuntimeMixin:
    """Provide runtime-loading wrappers for ChatGGUF."""

    def _resolve_llama_tuning(self) -> Dict[str, Any]:
        """Resolve optional llama.cpp tuning overrides from the environment."""
        return resolve_llama_tuning(self)

    @staticmethod
    def _format_llama_tuning(tuning: Dict[str, Any]) -> str:
        """Format tuning fields for concise logging."""
        return format_llama_tuning(tuning)

    def _load_model(self) -> None:
        """Load the GGUF model via llama-cpp-python."""
        load_model(self)

    def _apply_runtime_env_overrides(self) -> None:
        """Apply optional llama.cpp runtime overrides from the environment."""
        apply_runtime_env_overrides(self)

    def _load_llama_with_context_fallback(
        self,
        llama_cls: Any,
        base_kwargs: Dict[str, Any],
    ) -> None:
        """Load llama.cpp and retry smaller contexts on allocation failure."""
        load_llama_with_context_fallback(self, llama_cls, base_kwargs)

    def _llama_kwargs_for_context(
        self,
        base_kwargs: Dict[str, Any],
        n_ctx: int,
    ) -> Dict[str, Any]:
        """Return llama.cpp kwargs for one specific context size."""
        return llama_kwargs_for_context(self, base_kwargs, n_ctx)

    def _context_retry_sequence(self) -> tuple[int, ...]:
        """Return candidate context sizes for llama.cpp retry attempts."""
        return context_retry_sequence(self)

    @staticmethod
    def _next_retry_context(current_n_ctx: int) -> Optional[int]:
        """Return the next smaller context retry target when one exists."""
        return next_retry_context(current_n_ctx)

    @staticmethod
    def _should_retry_context(exc: Exception, n_ctx: int) -> bool:
        """Return True when one smaller llama context should be attempted."""
        return should_retry_context(exc, n_ctx)
