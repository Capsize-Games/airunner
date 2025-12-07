"""Custom LangChain adapter for locally-loaded HuggingFace models."""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from airunner.components.llm.adapters.mixins import (
    TokenizationMixin,
    MessageFormattingMixin,
    ToolCallingMixin,
    GenerationMixin,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ChatHuggingFaceLocal(
    TokenizationMixin,
    MessageFormattingMixin,
    ToolCallingMixin,
    GenerationMixin,
    BaseChatModel,
):
    """LangChain ChatModel adapter for locally-loaded HuggingFace models.

    This adapter wraps a pre-loaded HuggingFace model and tokenizer,
    allowing them to work with LangChain's agent system.

    Uses mixins for separation of concerns:
    - TokenizationMixin: Mistral tokenizer initialization
    - MessageFormattingMixin: Message to prompt/token conversion
    - ToolCallingMixin: Tool parsing and formatting
    - GenerationMixin: Text generation (streaming and non-streaming)

    Attributes:
        model: The loaded HuggingFace model
        tokenizer: The loaded HuggingFace tokenizer
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        top_k: Top-k sampling parameter
        repetition_penalty: Penalty for repeating tokens
        do_sample: Whether to use sampling
        tools: Bound tools for function calling
        tool_calling_mode: Tool calling strategy (native, json, react)
    """

    model: Any
    tokenizer: Any
    processor: Optional[Any] = None  # Vision processor for multimodal models
    model_path: Optional[str] = None
    use_mistral_native: bool = False
    use_json_mode: bool = False
    is_vision_model: bool = False  # True for Ministral-3, Pixtral, etc.
    tool_calling_mode: str = "react"
    max_new_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 20  # Qwen3 recommended value for better quality/speed
    repetition_penalty: float = 1.15
    do_sample: bool = True
    tools: Optional[List[Any]] = None
    enable_thinking: bool = True  # Qwen3 thinking mode
    _interrupted: bool = False
    _mistral_tokenizer: Optional[Any] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        """Called after Pydantic model initialization.

        Args:
            __context: Pydantic context (unused)
        """
        self._detect_tool_calling_mode()
        self._detect_vision_model()

        if self.use_mistral_native and self.tool_calling_mode == "native":
            self._init_mistral_tokenizer()

    def _detect_vision_model(self) -> None:
        """Detect if this is a vision model and load processor if needed."""
        if not self.model_path:
            return
            
        model_path_lower = self.model_path.lower()
        
        # Check for known vision model patterns
        is_ministral3 = "ministral" in model_path_lower or "mistral-3" in model_path_lower
        is_pixtral = "pixtral" in model_path_lower
        
        if is_ministral3 or is_pixtral:
            self.is_vision_model = True
            self._load_vision_processor()

    def _load_vision_processor(self) -> None:
        """Load vision processor for multimodal models like Ministral-3."""
        try:
            from transformers import AutoProcessor
            self.processor = AutoProcessor.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            print(f"✓ Loaded vision processor for {self.model_path}")
        except Exception as e:
            print(f"⚠ Failed to load vision processor: {e}")
            self.processor = None

    def _detect_tool_calling_mode(self) -> None:
        """Auto-detect which tool calling mode to use based on model.

        Priority:
        1. Native (Mistral with tekken.json) - best reliability
           EXCEPT: Ministral-3 (vision model) - tekken produces corrupted output
        2. Structured JSON (Qwen, Llama-3.1, Phi-3) - good reliability
        3. ReAct (fallback for all models) - okay reliability
        """
        if not self.model_path:
            self.tool_calling_mode = "react"
            return

        model_path_lower = self.model_path.lower()
        tekken_path = os.path.join(self.model_path, "tekken.json")

        # Check for Ministral-3 (vision model) - do NOT use native mode
        # The mistral_common tekken tokenizer produces corrupted output with
        # Mistral3ForConditionalGeneration architecture
        is_ministral3 = "ministral" in model_path_lower or "mistral-3" in model_path_lower
        
        if os.path.exists(tekken_path) and "mistral" in model_path_lower and not is_ministral3:
            self.tool_calling_mode = "native"
            self.use_mistral_native = True
            return

        # Check if model supports JSON mode via provider config
        from airunner.components.llm.config.provider_config import (
            LLMProviderConfig,
        )

        # Try to match model_path to known model configs
        for model_key, model_config in LLMProviderConfig.LOCAL_MODELS.items():
            repo_id = model_config.get("repo_id", "")
            if not repo_id:
                continue

            # Extract model name from repo_id (e.g., "Qwen2.5-7B-Instruct" from "Qwen/Qwen2.5-7B-Instruct")
            model_name = repo_id.split("/")[-1].lower()

            # Match if model name appears in path (handles both "Qwen/Qwen2.5-7B-Instruct" and ".../Qwen2.5-7B-Instruct-4bit")
            if model_name in model_path_lower:
                configured_mode = model_config.get("tool_calling_mode")
                if configured_mode in ("json", "native"):
                    self.tool_calling_mode = configured_mode
                    if configured_mode == "json":
                        self.use_json_mode = True
                    print(
                        f"ℹ Using {configured_mode} tool calling mode for {repo_id}"
                    )
                    return

        self.tool_calling_mode = "react"
        print(
            f"ℹ Using ReAct fallback tool calling (model: {self.model_path})"
        )

    @property
    def logger(self):
        """Lazy logger initialization.

        Returns:
            Logger instance for this class
        """
        if not hasattr(self, "_logger"):
            self._logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        return self._logger

    def set_interrupted(self, value: bool) -> None:
        """Set interrupt flag to stop generation.

        Args:
            value: True to interrupt, False to clear interrupt
        """
        self._interrupted = value
        if value:
            self.logger.info(f"ChatModel interrupt flag set to {value}")

    def should_stop_generation(self) -> bool:
        """Check if generation should be interrupted.

        Returns:
            True if generation should stop
        """
        if self._interrupted:
            self.logger.info(
                "should_stop_generation returning True - interrupting!"
            )
        return self._interrupted

    @property
    def _llm_type(self) -> str:
        """Return type of language model.

        Returns:
            Model type identifier
        """
        return "huggingface_local"

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to this chat model.

        For Mistral models with native function calling support, we use
        the Mistral tokenizer and native tool format. For other models,
        we inject tool schemas into the system prompt and parse responses.

        Args:
            tools: List of tools to bind (LangChain tools or callables)
            **kwargs: Additional arguments (unused)

        Returns:
            New instance with tools bound
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        return self.__class__(
            model=self.model,
            tokenizer=self.tokenizer,
            processor=self.processor,
            model_path=self.model_path,
            use_mistral_native=self.use_mistral_native,
            is_vision_model=self.is_vision_model,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            repetition_penalty=self.repetition_penalty,
            do_sample=self.do_sample,
            tools=formatted_tools,
            _mistral_tokenizer=self._mistral_tokenizer,
        )
