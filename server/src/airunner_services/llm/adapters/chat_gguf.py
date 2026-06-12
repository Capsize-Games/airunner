"""LangChain adapter for GGUF models via llama-cpp-python."""

from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.llm.adapters.chat_gguf_execution_mixin import (
    ChatGGUFExecutionMixin,
)
from airunner_services.llm.adapters.chat_gguf_chat_format_detection import (
    _detect_chat_format,
)
from airunner_services.llm.adapters.chat_gguf_prompt_mixin import (
    ChatGGUFPromptMixin,
)
from airunner_services.llm.adapters.chat_gguf_runtime_mixin import (
    ChatGGUFRuntimeMixin,
)
from airunner_services.llm.adapters.chat_gguf_tool_parsing_mixin import (
    ChatGGUFToolParsingMixin,
)
from airunner_services.utils.application import get_logger


class ChatGGUF(
    ChatGGUFRuntimeMixin,
    ChatGGUFPromptMixin,
    ChatGGUFToolParsingMixin,
    ChatGGUFExecutionMixin,
    BaseChatModel,
):
    """LangChain ChatModel adapter for GGUF models via llama-cpp-python."""

    model_path: str
    gguf_runtime_profile: Optional[str] = None
    n_ctx: int = 32768
    n_gpu_layers: int = -1
    n_batch: int = 256
    max_tokens: int = 32768
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    repeat_penalty: float = 1.15
    flash_attn: bool = True
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    tool_calling_mode: str = "native"
    enable_thinking: bool = True
    reasoning_effort: str = "medium"
    chat_format: Optional[str] = None
    use_yarn: bool = False
    yarn_orig_ctx: int = 32768
    _interrupted: bool = False
    _llama: Optional[Any] = None
    _detected_format: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    @property
    def logger(self):
        """Get logger instance."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(
                self.__class__.__name__,
                AIRUNNER_LOG_LEVEL,
            )
        return self._logger

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM type."""
        return "gguf-llama-cpp"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for logging."""
        return {
            "model_path": self.model_path,
            "gguf_runtime_profile": self.gguf_runtime_profile,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "chat_format": self._detected_format,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _runtime_signature(self, tuning: Dict[str, Any]) -> str:
        """Return one concise runtime signature for logs."""
        signature = {
            "profile": self.gguf_runtime_profile or "default",
            "chat_format": self._detected_format or "auto",
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "n_batch": tuning.get("n_batch", self.n_batch),
            "flash_attn": self.flash_attn,
            "offload_kqv": tuning.get("offload_kqv"),
            "op_offload": tuning.get("op_offload"),
        }
        return ", ".join(
            f"{key}={value}"
            for key, value in signature.items()
            if value is not None
        )

    def model_post_init(self, __context: Any) -> None:
        """Initialize the llama-cpp-python model after Pydantic init."""
        super().model_post_init(__context)
        if self.chat_format is not None:
            self._detected_format = self.chat_format
        else:
            self._detected_format = _detect_chat_format(self.model_path)
        self._load_model()

    def _uses_gpt_oss_parser(self) -> bool:
        """Return True when GPT-OSS Harmony content needs normalization."""
        model_path = str(self.model_path).lower()
        return self._detected_format == "gpt-oss" or "gpt-oss" in model_path

    def _use_raw_gpt_oss_completion(self) -> bool:
        """Return True when GPT-OSS should use raw Harmony prompting."""
        return (
            self._uses_gpt_oss_parser()
            and self.tool_choice != "none"
            and hasattr(self._llama, "create_completion")
        )

    def _normalized_reasoning_effort(self) -> str:
        """Return a valid GPT-OSS reasoning-effort value."""
        effort = str(self.reasoning_effort or "medium").strip().lower()
        if effort in {"low", "medium", "high"}:
            return effort
        return "medium"

    def _reload_with_tools(self) -> None:
        """No-op: tool bindings do not require runtime reloading."""

    def clear_bound_tools(self) -> None:
        """Clear previously bound tools from the live model instance."""
        self.tools = None
        self.tool_choice = None

    def _use_native_tool_calling(self) -> bool:
        """Return True when llama.cpp native tools should be used."""
        return (
            bool(self.tools)
            and self.tool_choice != "none"
            and self.tool_calling_mode != "react"
        )

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag for stopping generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should stop."""
        return self._interrupted
