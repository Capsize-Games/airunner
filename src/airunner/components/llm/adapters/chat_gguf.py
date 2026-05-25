"""LangChain adapter for GGUF models via llama-cpp-python.

This adapter wraps llama-cpp-python for GGUF model inference with
model-specific tool-calling strategies.

GGUF models are significantly smaller and faster than BitsAndBytes quantized
safetensors:
- Q4_K_M: ~4.1GB for 7B model (vs ~5.5GB for BnB 4-bit)
- Faster inference via optimized llama.cpp backend
- Native GPU acceleration via cuBLAS

Qwen-family models can use llama.cpp native tool calling, while GPT-OSS runs
through a text-based tool path.
"""

import json
import importlib.metadata as importlib_metadata
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Union,
)

from airunner.utils.application.log_hygiene import summarize_mapping_keys

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.components.llm.utils.gpt_oss_parser import (
    CALL_TOKEN,
    CHANNEL_TOKEN,
    CONSTRAIN_TOKEN,
    END_TOKEN,
    GPTOSSStreamParser,
    MESSAGE_TOKEN,
    RETURN_TOKEN,
    START_TOKEN,
    has_gpt_oss_markup,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)
from airunner.utils.application import get_logger
from packaging.version import InvalidVersion, Version

try:
    from gguf import GGUFReader
except ImportError:
    GGUFReader = None

try:
    import torch
except ImportError:
    torch = None


class UnsupportedGGUFArchitectureError(Exception):
    """Raised when a GGUF model uses an architecture not supported by llama-cpp-python.
    
    This allows the factory to catch this specific error and fall back to
    transformers-based loading.
    """
    
    def __init__(
        self,
        architecture: str,
        model_path: str,
        runtime_version: Optional[str] = None,
    ):
        self.architecture = architecture
        self.model_path = model_path
        self.runtime_version = runtime_version
        version_message = ""
        if runtime_version:
            version_message = (
                f" Installed llama-cpp-python version: {runtime_version}."
            )
        super().__init__(
            f"GGUF model architecture '{architecture}' is not supported by llama-cpp-python. "
            f"Model: {model_path}.{version_message} Use a GGUF model "
            "supported by the installed llama-cpp-python runtime."
        )


_KNOWN_UNSUPPORTED_ARCHITECTURES = {
    "mistral3": Version("0.3.16"),
    "qwen35": Version("0.3.16"),
}


def _current_llama_cpp_version() -> Optional[Version]:
    """Return the installed llama-cpp-python version when available."""
    try:
        return Version(importlib_metadata.version("llama-cpp-python"))
    except (importlib_metadata.PackageNotFoundError, InvalidVersion):
        return None


def _read_gguf_string_field(model_path: str, field_name: str) -> Optional[str]:
    """Return one GGUF metadata string field when it can be parsed."""
    if GGUFReader is None or not os.path.exists(model_path):
        return None

    try:
        reader = GGUFReader(model_path)
        field = reader.fields.get(field_name)
        if field is None or not getattr(field, "parts", None):
            return None

        value = bytes(field.parts[-1]).decode("utf-8", errors="ignore")
        value = value.strip()
        return value or None
    except Exception:
        return None


def _guess_architecture_from_path(model_path: str) -> Optional[str]:
    """Return a likely architecture from a known GGUF filename."""
    filename = os.path.basename(str(model_path)).lower()
    if "qwen3.5" in filename or "qwen35" in filename:
        return "qwen35"
    if "ministral" in filename or "mistral3" in filename:
        return "mistral3"
    if "qwen3" in filename:
        return "qwen3"
    if "gpt-oss" in filename:
        return "gptoss"
    return None


def _metadata_int(metadata: Dict[str, Any], field_name: str) -> Optional[int]:
    """Return one llama.cpp metadata value parsed as an integer."""
    value = metadata.get(field_name)
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _estimate_known_kv_cache_gb(
    model_path: str,
    n_ctx: int,
    *,
    type_k_bytes: int = 1,
    type_v_bytes: int = 1,
) -> Optional[float]:
    """Estimate KV-cache size for known shipped GGUF models."""
    filename = os.path.basename(str(model_path)).lower()
    known_shapes = {
        "qwen3-8b": (36, 8, 128, 128),
    }

    for marker, shape in known_shapes.items():
        if marker not in filename:
            continue

        block_count, head_count_kv, key_length, value_length = shape
        kv_bytes = (
            int(n_ctx)
            * block_count
            * head_count_kv
            * (
                key_length * int(type_k_bytes)
                + value_length * int(type_v_bytes)
            )
        )
        return kv_bytes / float(1024 ** 3)

    return None


def read_gguf_architecture(model_path: str) -> Optional[str]:
    """Return the GGUF general.architecture metadata value."""
    return _read_gguf_string_field(model_path, "general.architecture")


def estimate_gguf_kv_cache_gb(
    model_path: str,
    n_ctx: int,
    *,
    type_k_bytes: int = 1,
    type_v_bytes: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    """Estimate the GGUF KV-cache footprint for one configured context."""
    metadata_values = metadata or {}
    architecture = str(
        metadata_values.get("general.architecture", "")
    ).strip()
    if not architecture:
        estimated = _estimate_known_kv_cache_gb(
            model_path,
            n_ctx,
            type_k_bytes=type_k_bytes,
            type_v_bytes=type_v_bytes,
        )
        if estimated is not None:
            return estimated
        return None

    if not architecture:
        return None

    prefix = f"{architecture}.attention"
    block_count = _metadata_int(metadata_values, f"{architecture}.block_count")
    head_count_kv = _metadata_int(
        metadata_values,
        f"{prefix}.head_count_kv",
    )
    key_length = _metadata_int(metadata_values, f"{prefix}.key_length")
    value_length = _metadata_int(metadata_values, f"{prefix}.value_length")

    if not all(
        value is not None
        for value in (block_count, head_count_kv, key_length, value_length)
    ):
        return None

    kv_bytes = (
        int(n_ctx)
        * int(block_count)
        * int(head_count_kv)
        * (
            int(key_length) * int(type_k_bytes)
            + int(value_length) * int(type_v_bytes)
        )
    )
    return kv_bytes / float(1024 ** 3)


def detect_known_unsupported_architecture(model_path: str) -> Optional[str]:
    """Return a known-unsupported GGUF architecture for this runtime."""
    architecture = _guess_architecture_from_path(model_path)
    if not architecture:
        architecture = read_gguf_architecture(model_path)
    if not architecture:
        return None

    max_supported_version = _KNOWN_UNSUPPORTED_ARCHITECTURES.get(architecture)
    runtime_version = _current_llama_cpp_version()
    if runtime_version is None or max_supported_version is None:
        return None

    if runtime_version <= max_supported_version:
        return architecture

    return None


@lru_cache(maxsize=16)
def _llama_chat_format_supported(name: str) -> bool:
    """Return True when the installed llama_cpp runtime supports a chat format."""
    if not name:
        return False

    try:
        from llama_cpp import llama_chat_format

        llama_chat_format.get_chat_completion_handler(name)
    except Exception:
        return False

    return True


def _detect_chat_format(model_path: str) -> Optional[str]:
    """Detect the appropriate chat format based on model filename.
    
    Args:
        model_path: Path to the GGUF model file
        
    Returns:
        Chat format string for llama-cpp-python, or None to let
        llama.cpp use the GGUF's embedded chat template.
    """
    path_lower = model_path.lower()

    if "gpt-oss" in path_lower:
        return "gpt-oss" if _llama_chat_format_supported("gpt-oss") else None
    
    # Qwen models use chatml
    if "qwen" in path_lower:
        return "chatml"
    
    # Llama 3.x 
    if any(x in path_lower for x in ["llama-3", "llama3", "meta-llama-3"]):
        return "llama-3"
    
    # Mistral
    if any(x in path_lower for x in ["mistral", "ministral", "magistral"]):
        return "mistral-instruct"
    
    return None


def _get_int_env(name: str) -> Optional[int]:
    """Parse an integer environment variable if present."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def _get_bool_env(name: str) -> Optional[bool]:
    """Parse a boolean environment variable if present."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return None


class ChatGGUF(BaseChatModel):
    """LangChain ChatModel adapter for GGUF models via llama-cpp-python.

    This adapter uses llama-cpp-python's NATIVE function calling support
    via create_chat_completion() with tools parameter. This is the proper
    way to do tool calling with Qwen3 and other modern models.
    
    Key features:
    - Uses native chat completion API (not manual prompt building)
    - Proper Hermes-style function calling (not ReAct)
    - Automatic chat format detection from model name
    - Full streaming support
    - Thinking mode support for Qwen3

    Attributes:
        model_path: Path to the GGUF model file
        n_ctx: Context window size (32768 native for Qwen3, up to 131072 with YaRN)
        n_gpu_layers: Number of layers to offload to GPU (-1 for all)
        max_tokens: Maximum tokens to generate (32768 for Qwen3)
        temperature: Sampling temperature
        tools: Bound tools for function calling (OpenAI format)
        enable_thinking: Whether to enable thinking mode (Qwen3-style)
        chat_format: Override auto-detected chat format
        use_yarn: Enable YaRN for extended context (requires more VRAM)
    """

    model_path: str
    n_ctx: int = 32768  # Qwen3 native context (use YaRN for 131K)
    n_gpu_layers: int = -1
    n_batch: int = 512
    max_tokens: int = 32768  # Qwen3 recommended output length
    temperature: float = 0.6  # Qwen3 thinking mode recommended
    top_p: float = 0.95  # Qwen3 thinking mode recommended  
    top_k: int = 20  # Qwen3 recommended
    min_p: float = 0.0  # Qwen3 recommended (disabled)
    repeat_penalty: float = 1.15
    flash_attn: bool = True
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    tool_calling_mode: str = "native"
    enable_thinking: bool = True
    reasoning_effort: str = "medium"
    chat_format: Optional[str] = None  # Auto-detected if None
    use_yarn: bool = False  # Disabled by default - requires more VRAM
    yarn_orig_ctx: int = 32768  # Qwen3 native context length
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
                AIRUNNER_LOG_LEVEL
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
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "chat_format": self._detected_format,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

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
            and self.tool_calling_mode == "react"
            and bool(self.tools)
            and hasattr(self._llama, "create_completion")
        )

    def _normalized_reasoning_effort(self) -> str:
        """Return a valid GPT-OSS reasoning-effort value."""
        effort = str(self.reasoning_effort or "medium").strip().lower()
        if effort in {"low", "medium", "high"}:
            return effort
        return "medium"

    @staticmethod
    def _is_numeric_override(value: Any) -> bool:
        """Return whether one runtime override is numeric, not boolean."""
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @contextmanager
    def _temporary_runtime_overrides(
        self,
        kwargs: Optional[Dict[str, Any]],
    ) -> Iterator[None]:
        """Apply one-shot generation overrides for this model call."""
        runtime_kwargs = dict(kwargs or {})
        original_values: Dict[str, Any] = {}
        overrides: Dict[str, Any] = {}

        max_tokens = runtime_kwargs.get("max_new_tokens")
        if not isinstance(max_tokens, int):
            max_tokens = runtime_kwargs.get("max_tokens")
        if isinstance(max_tokens, int):
            overrides["max_tokens"] = max_tokens

        for attr_name in ("temperature", "top_p", "min_p"):
            value = runtime_kwargs.get(attr_name)
            if self._is_numeric_override(value):
                overrides[attr_name] = value

        top_k = runtime_kwargs.get("top_k")
        if isinstance(top_k, int):
            overrides["top_k"] = top_k

        repeat_penalty = runtime_kwargs.get("repetition_penalty")
        if repeat_penalty is None:
            repeat_penalty = runtime_kwargs.get("repeat_penalty")
        if self._is_numeric_override(repeat_penalty):
            overrides["repeat_penalty"] = repeat_penalty

        reasoning_effort = runtime_kwargs.get("reasoning_effort")
        if isinstance(reasoning_effort, str) and reasoning_effort.strip():
            overrides["reasoning_effort"] = reasoning_effort.strip()

        enable_thinking = runtime_kwargs.get("enable_thinking")
        if isinstance(enable_thinking, bool):
            overrides["enable_thinking"] = enable_thinking

        try:
            for attr_name, value in overrides.items():
                original_values[attr_name] = getattr(self, attr_name)
                setattr(self, attr_name, value)
            yield
        finally:
            for attr_name, value in original_values.items():
                setattr(self, attr_name, value)

    def _resolve_llama_tuning(self) -> Dict[str, Any]:
        """Resolve optional llama.cpp tuning overrides from the environment."""
        tuning: Dict[str, Any] = {
            "n_batch": self.n_batch,
            "offload_kqv": True,
        }

        n_batch_override = _get_int_env("AIRUNNER_GGUF_N_BATCH")
        if n_batch_override is not None:
            tuning["n_batch"] = n_batch_override

        n_ubatch_override = _get_int_env("AIRUNNER_GGUF_N_UBATCH")
        if n_ubatch_override is not None:
            tuning["n_ubatch"] = n_ubatch_override

        n_threads_override = _get_int_env("AIRUNNER_GGUF_N_THREADS")
        if n_threads_override is not None:
            tuning["n_threads"] = n_threads_override

        n_threads_batch_override = _get_int_env("AIRUNNER_GGUF_N_THREADS_BATCH")
        if n_threads_batch_override is not None:
            tuning["n_threads_batch"] = n_threads_batch_override

        offload_kqv_override = _get_bool_env("AIRUNNER_GGUF_OFFLOAD_KQV")
        if offload_kqv_override is not None:
            tuning["offload_kqv"] = offload_kqv_override

        op_offload_override = _get_bool_env("AIRUNNER_GGUF_OP_OFFLOAD")
        if op_offload_override is not None:
            tuning["op_offload"] = op_offload_override

        return tuning

    @staticmethod
    def _format_llama_tuning(tuning: Dict[str, Any]) -> str:
        """Format tuning fields for concise logging."""
        keys = [
            "n_batch",
            "n_ubatch",
            "n_threads",
            "n_threads_batch",
            "offload_kqv",
            "op_offload",
        ]
        return ", ".join(
            f"{key}={tuning[key]}" for key in keys if key in tuning
        )

    def _load_model(self) -> None:
        """Load the GGUF model via llama-cpp-python.
        
        Raises:
            ImportError: If llama-cpp-python is not installed
            UnsupportedGGUFArchitectureError: If the model architecture is not supported
            RuntimeError: For other loading errors
        """
        if self._llama is not None:
            return

        unsupported_architecture = detect_known_unsupported_architecture(
            self.model_path
        )
        if unsupported_architecture is not None:
            runtime_version = _current_llama_cpp_version()
            raise UnsupportedGGUFArchitectureError(
                unsupported_architecture,
                self.model_path,
                runtime_version=str(runtime_version)
                if runtime_version is not None
                else None,
            )

        try:
            from llama_cpp import Llama, llama_supports_gpu_offload
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for GGUF support. "
                "Install with: pip install llama-cpp-python"
            )

        gpu_offload_supported = False
        try:
            gpu_offload_supported = bool(llama_supports_gpu_offload())
        except Exception:
            gpu_offload_supported = False

        cuda_available = bool(
            torch is not None
            and hasattr(torch, "cuda")
            and torch.cuda.is_available()
        )

        if self.n_gpu_layers != 0 and cuda_available and not gpu_offload_supported:
            self.logger.warning(
                "CUDA is available, but this llama-cpp-python build does not support GPU offload. "
                "GGUF inference will run on CPU until llama-cpp-python is rebuilt with GGML_CUDA=on."
            )

        self.logger.info("Loading GGUF model from %s", self.model_path)
        self.logger.info(
            f"  chat_format={self._detected_format or 'auto'}, "
            f"n_ctx={self.n_ctx}, "
            f"n_gpu_layers={self.n_gpu_layers}"
        )
        try:
            model_size_gb = os.path.getsize(self.model_path) / float(1024 ** 3)
            self.logger.info(f"  GGUF file size={model_size_gb:.2f} GiB")
        except OSError:
            pass
        if self.n_gpu_layers != 0:
            self.logger.info(
                f"  llama.cpp GPU offload support={gpu_offload_supported}"
            )

        llama_tuning = self._resolve_llama_tuning()

        # Build kwargs with optional YaRN support for extended context
        llama_kwargs = {
            "model_path": self.model_path,
            "n_ctx": self.n_ctx,
            "n_gpu_layers": self.n_gpu_layers,
            "flash_attn": self.flash_attn,
            "type_k": 8,  # KV cache quantization to save VRAM
            "type_v": 8,
            "verbose": False,
            **llama_tuning,
        }
        if self._detected_format is not None:
            llama_kwargs["chat_format"] = self._detected_format

        self.logger.info(
            f"  llama.cpp tuning: {self._format_llama_tuning(llama_tuning)}"
        )

        # Add YaRN parameters for extended context (131K)
        # YaRN (Yet another RoPE extensioN) allows extending context
        # beyond native limit
        if self.use_yarn and self.n_ctx > self.yarn_orig_ctx:
            self.logger.info(
                f"Enabling YaRN for extended context: {self.yarn_orig_ctx} -> {self.n_ctx}"
            )
            # rope_scaling_type: 2 = YARN in llama.cpp
            llama_kwargs["rope_scaling_type"] = 2
            llama_kwargs["yarn_orig_ctx"] = self.yarn_orig_ctx
            # Calculate scaling factor: target_ctx / original_ctx
            factor = self.n_ctx / self.yarn_orig_ctx
            llama_kwargs["yarn_ext_factor"] = factor
            llama_kwargs["yarn_attn_factor"] = 1.0
            llama_kwargs["yarn_beta_fast"] = 32.0
            llama_kwargs["yarn_beta_slow"] = 1.0

        try:
            self._llama = Llama(**llama_kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            # Check for unsupported architecture error from llama.cpp
            if "unknown model architecture" in error_msg:
                # Extract architecture name from error message if possible
                # Error format: "unknown model architecture: 'mistral3'"
                import re

                arch_match = re.search(
                    r"unknown model architecture[:\s]*['\"]?(\w+)['\"]?",
                    error_msg,
                )
                architecture = (
                    arch_match.group(1) if arch_match else "unknown"
                )
                raise UnsupportedGGUFArchitectureError(
                    architecture,
                    self.model_path,
                )
            elif "failed to load model" in error_msg:
                # Generic llama.cpp load failure - could also be
                # architecture issue
                raise RuntimeError(
                    f"Failed to load GGUF model from {self.model_path}: {e}. "
                    "This may be due to an unsupported model architecture or corrupted file."
                )
            else:
                raise

        estimated_kv_cache_gb = estimate_gguf_kv_cache_gb(
            self.model_path,
            self.n_ctx,
            type_k_bytes=1,
            type_v_bytes=1,
            metadata=getattr(self._llama, "metadata", None),
        )
        if estimated_kv_cache_gb is not None:
            self.logger.info(
                "  estimated q8 KV cache at n_ctx=%s: %.2f GiB",
                self.n_ctx,
                estimated_kv_cache_gb,
            )

        self.logger.info("✓ GGUF model loaded successfully")

    def _reload_with_tools(self) -> None:
        """No-op: tool bindings do not require runtime reloading."""
        pass

    def clear_bound_tools(self) -> None:
        """Clear previously bound tools from the live model instance."""
        self.tools = None
        self.tool_choice = None

    def _use_native_tool_calling(self) -> bool:
        """Return True when llama.cpp native tools should be used."""
        return (
            bool(self.tools)
            and self.tool_choice != "none"
            and self.tool_calling_mode == "native"
        )

    def _native_tool_choice(
        self,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Normalize internal tool-choice values for llama.cpp."""
        if self.tool_choice == "any" and self._use_native_tool_calling():
            return "required"
        return self.tool_choice

    def _forced_tool_name(self) -> Optional[str]:
        """Return one explicitly forced tool name, if present."""
        if isinstance(self.tool_choice, str):
            normalized = self.tool_choice.strip()
            if normalized and normalized not in {
                "auto",
                "none",
                "any",
                "required",
            }:
                return normalized
            return None
        if not isinstance(self.tool_choice, dict):
            return None
        function = self.tool_choice.get("function") or {}
        if not isinstance(function, dict):
            return None
        name = function.get("name")
        return str(name).strip() or None if name else None

    def _non_native_tool_choice_instruction(self) -> str:
        """Return prompt guidance for required non-native tool turns."""
        forced_tool = self._forced_tool_name()
        if not forced_tool and self.tool_choice not in {"any", "required"}:
            return ""

        if self.tool_calling_mode == "react":
            if forced_tool:
                return (
                    "\n\nYou MUST call the tool '"
                    f"{forced_tool}' now. Respond ONLY with that tool call "
                    "in the documented Action / Action Input format. Do "
                    "NOT write conversational text before or after it."
                )
            return (
                "\n\nYou MUST call at least one tool now. Respond ONLY "
                "with tool-call output in the documented Action / Action "
                "Input format. Do NOT write conversational text before or "
                "after the tool call."
            )

        if forced_tool:
            return (
                "\n\nYou MUST call the tool '"
                f"{forced_tool}' now. Respond ONLY with one <tool_call>"
                "...</tool_call> block for that tool. Do NOT write "
                "conversational text before or after it."
            )
        return (
            "\n\nYou MUST call at least one tool now. Respond ONLY with "
            "one or more <tool_call>...</tool_call> blocks. Do NOT write "
            "conversational text before or after the tool call output."
        )

    def set_interrupted(self, value: bool) -> None:
        """Set the interrupted flag for stopping generation."""
        self._interrupted = value

    def should_stop_generation(self) -> bool:
        """Check if generation should stop."""
        return self._interrupted

    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert LangChain messages to llama-cpp-python format.
        
        Args:
            messages: LangChain message objects
            
        Returns:
            List of message dicts for create_chat_completion
        """
        converted = []
        tool_instructions_added = False
        use_native_tool_calling = self._use_native_tool_calling()
        
        for msg in messages:
            if isinstance(msg, SystemMessage):
                content = msg.content
                # Legacy XML tool instructions are only needed when native
                # llama.cpp tool calling is unavailable.
                if self.tools and not use_native_tool_calling and not tool_instructions_added:
                    content = self._inject_tool_instructions(content)
                    tool_instructions_added = True
                converted.append({
                    "role": "system",
                    "content": content,
                })
            elif isinstance(msg, HumanMessage):
                converted.append({
                    "role": "user",
                    "content": msg.content,
                })
            elif isinstance(msg, AIMessage):
                msg_dict: Dict[str, Any] = {"role": "assistant"}
                tool_calls = self._convert_langchain_tool_calls(
                    getattr(msg, "tool_calls", []) or []
                )
                content = msg.content
                if content is None:
                    content = ""
                elif not isinstance(content, str):
                    content = str(content)
                if (
                    self._uses_gpt_oss_parser()
                    and tool_calls
                    and not content
                ):
                    content = str(
                        msg.additional_kwargs.get("thinking_content") or ""
                    )
                msg_dict["content"] = content
                if tool_calls:
                    msg_dict["tool_calls"] = tool_calls
                converted.append(msg_dict)
            elif isinstance(msg, ToolMessage):
                if self._uses_gpt_oss_parser() or use_native_tool_calling:
                    converted.append(
                        {
                            "role": "tool",
                            "content": str(msg.content),
                            "tool_call_id": msg.tool_call_id,
                        }
                    )
                else:
                    converted.append(
                        {
                            "role": "user",
                            "content": (
                                "Tool result for "
                                f"{getattr(msg, 'name', 'tool')}:\n"
                                f"{msg.content}"
                            ),
                        }
                    )
        
        # If no system message but we have tools, add one
        if self.tools and not use_native_tool_calling and not tool_instructions_added:
            tool_system = self._inject_tool_instructions("")
            converted.insert(0, {"role": "system", "content": tool_system})

        self._apply_gpt_oss_reasoning_effort(converted)
        self._apply_thinking_directive(converted)
        
        return converted

    def _apply_gpt_oss_reasoning_effort(
        self, converted: List[Dict[str, Any]]
    ) -> None:
        """Inject the documented GPT-OSS reasoning-effort directive."""
        if not self._uses_gpt_oss_parser():
            return

        directive = f"reasoning effort {self._normalized_reasoning_effort()}"

        for message in converted:
            if message.get("role") != "system":
                continue
            content = message.get("content")
            if not isinstance(content, str):
                return
            lowered = content.lower()
            if "reasoning effort low" in lowered:
                return
            if "reasoning effort medium" in lowered:
                return
            if "reasoning effort high" in lowered:
                return
            message["content"] = (
                f"{content.rstrip()}\n\n{directive}"
                if content.strip()
                else directive
            )
            return

        converted.insert(0, {"role": "system", "content": directive})

    def _inject_tool_instructions(self, system_content: str) -> str:
        """Inject tool instructions into the system prompt."""
        if not self.tools:
            return system_content

        # Respect tool_choice="none" - don't inject tool instructions
        if self.tool_choice == "none":
            return system_content

        if self._uses_gpt_oss_parser():
            return self._inject_gpt_oss_tool_instructions(system_content)

        if self.tool_calling_mode == "react":
            return (
                self._inject_react_tool_instructions(system_content)
                + self._non_native_tool_choice_instruction()
            )

        # Build Qwen-style XML tool definitions
        tool_defs = []
        for tool in self.tools:
            tool_defs.append(json.dumps(tool))

        tools_json = "\n".join(tool_defs)

        tool_instructions = f"""

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": "<function-name>", "arguments": <args-json-object>}}
</tool_call>"""

        return (
            system_content
            + tool_instructions
            + self._non_native_tool_choice_instruction()
        )

    def _inject_gpt_oss_tool_instructions(self, system_content: str) -> str:
        """Inject Harmony-style tool instructions for GPT-OSS."""
        tools_text = self._format_gpt_oss_namespace()
        instructions = (
            "\n\n# Valid channels: analysis, commentary, final. "
            "Channel must be included for every message.\n"
            "For coding and editor tasks, avoid analysis-only replies. "
            "Use commentary for brief progress updates and tool calls, "
            "and use final for the finished user-facing answer.\n"
            "Calls to these tools must go to the commentary channel: "
            "'functions'.\n\n"
            "# Tools\n\n"
            "## functions\n\n"
            f"{tools_text}\n\n"
            "When a tool is needed, call it on the commentary channel "
            "with JSON arguments. After tool results arrive, continue "
            "and answer the user on the final channel."
        )
        return system_content + instructions

    def _gpt_oss_harmony_system_message(self) -> str:
        """Return the top-level Harmony system message."""
        return (
            "You are ChatGPT, a large language model trained by OpenAI.\n"
            "Knowledge cutoff: 2024-06\n"
            f"Current date: {date.today().isoformat()}\n\n"
            f"Reasoning: {self._normalized_reasoning_effort()}\n\n"
            "# Valid channels: analysis, commentary, final. Channel "
            "must be included for every message.\n"
            "Calls to these tools must go to the commentary channel: "
            "'functions'."
        )

    def _render_harmony_message(
        self,
        role: str,
        content: str,
        *,
        channel: Optional[str] = None,
        recipient: Optional[str] = None,
        content_type: Optional[str] = None,
        terminator: str = END_TOKEN,
    ) -> str:
        """Render one Harmony protocol message."""
        rendered = [f"{START_TOKEN}{role}"]
        if recipient:
            rendered.append(f" to={recipient}")
        if channel:
            rendered.append(f"{CHANNEL_TOKEN}{channel}")
        if content_type:
            rendered.append(f"{CONSTRAIN_TOKEN}{content_type}")
        rendered.append(f"{MESSAGE_TOKEN}{content}{terminator}")
        return "".join(rendered)

    def _stringify_harmony_content(self, content: Any) -> str:
        """Convert one LangChain content payload into Harmony text."""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except TypeError:
            return str(content)

    def _render_gpt_oss_developer_message(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Render the developer instruction layer for raw Harmony prompts."""
        contents = [
            self._stringify_harmony_content(message.content)
            for message in messages
            if isinstance(message, SystemMessage)
        ]
        if not contents:
            return ""

        developer_content = "\n\n".join(
            content for content in contents if content.strip()
        )
        if self.tools and "namespace functions" not in developer_content:
            developer_content = self._inject_gpt_oss_tool_instructions(
                developer_content
            )
        if not developer_content.strip():
            return ""
        return self._render_harmony_message("developer", developer_content)

    def _render_gpt_oss_ai_message(
        self,
        message: AIMessage,
    ) -> List[str]:
        """Render one historical AI message into Harmony messages."""
        rendered: List[str] = []
        thinking = str(
            message.additional_kwargs.get("thinking_content") or ""
        ).strip()
        if thinking:
            rendered.append(
                self._render_harmony_message(
                    "assistant",
                    thinking,
                    channel="analysis",
                )
            )

        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            for tool_call in self._convert_langchain_tool_calls(tool_calls):
                rendered.append(
                    self._render_harmony_message(
                        "assistant",
                        tool_call["function"]["arguments"],
                        channel="commentary",
                        recipient=(
                            f"functions.{tool_call['function']['name']}"
                        ),
                        content_type="json",
                        terminator=CALL_TOKEN,
                    )
                )
            return rendered

        content = str(message.content or "").strip()
        if content:
            rendered.append(
                self._render_harmony_message(
                    "assistant",
                    content,
                    channel="final",
                )
            )
        return rendered

    def _render_gpt_oss_tool_message(self, message: ToolMessage) -> str:
        """Render one tool-result message into Harmony format."""
        content = str(message.content or "")
        content_type = None
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            content_type = "json"

        recipient = None
        tool_name = getattr(message, "name", None)
        if tool_name:
            recipient = f"functions.{tool_name}"

        return self._render_harmony_message(
            "tool",
            content,
            recipient=recipient,
            content_type=content_type,
        )

    def _forced_gpt_oss_tool_name(self) -> Optional[str]:
        """Return the forced tool name for raw Harmony prompting."""
        if not self._use_raw_gpt_oss_completion():
            return None

        tool_name = None
        if isinstance(self.tool_choice, str):
            normalized = self.tool_choice.strip()
            if normalized and normalized not in {"auto", "none"}:
                tool_name = normalized
        elif isinstance(self.tool_choice, dict):
            function = self.tool_choice.get("function") or {}
            tool_name = function.get("name")

        if not tool_name:
            return None

        available_tools = {
            (tool.get("function", tool) or {}).get("name")
            for tool in self.tools or []
        }
        if tool_name in available_tools:
            return tool_name
        return None

    def _render_gpt_oss_prefilled_tool_call(self, tool_name: str) -> str:
        """Render a partial Harmony tool call for one forced tool."""
        return self._render_harmony_message(
            "assistant",
            "",
            channel="commentary",
            recipient=f"functions.{tool_name}",
            content_type="json",
            terminator="",
        )

    def _render_gpt_oss_harmony_prompt(
        self,
        messages: List[BaseMessage],
    ) -> str:
        """Render LangChain messages as one raw Harmony prompt."""
        prompt_parts = [
            self._render_harmony_message(
                "system",
                self._gpt_oss_harmony_system_message(),
            )
        ]
        developer_message = self._render_gpt_oss_developer_message(messages)
        if developer_message:
            prompt_parts.append(developer_message)

        for message in messages:
            if isinstance(message, SystemMessage):
                continue
            if isinstance(message, HumanMessage):
                prompt_parts.append(
                    self._render_harmony_message(
                        "user",
                        self._stringify_harmony_content(message.content),
                    )
                )
                continue
            if isinstance(message, AIMessage):
                prompt_parts.extend(self._render_gpt_oss_ai_message(message))
                continue
            if isinstance(message, ToolMessage):
                prompt_parts.append(
                    self._render_gpt_oss_tool_message(message)
                )

        forced_tool_name = self._forced_gpt_oss_tool_name()
        if forced_tool_name:
            prompt_parts.append(
                self._render_gpt_oss_prefilled_tool_call(
                    forced_tool_name,
                )
            )
        else:
            prompt_parts.append(f"{START_TOKEN}assistant")
        return "".join(prompt_parts)

    def _build_gpt_oss_completion_kwargs(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]],
        *,
        stream: bool,
    ) -> Dict[str, Any]:
        """Build llama.cpp completion kwargs for raw Harmony prompting."""
        completion_kwargs: Dict[str, Any] = {
            "prompt": self._render_gpt_oss_harmony_prompt(messages),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "stream": stream,
        }
        if stop:
            completion_kwargs["stop"] = stop
        return completion_kwargs

    def _prefilled_gpt_oss_tool_json_needs_continuation(
        self,
        raw_text: str,
    ) -> bool:
        """Return True when a forced prefilled tool body looks truncated."""
        if not self._forced_gpt_oss_tool_name():
            return False

        json_text = self._extract_prefilled_gpt_oss_tool_json(raw_text)
        if not json_text:
            return False

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            error_text = str(exc).lower()
            if "unterminated string" in error_text:
                return True
            return exc.pos >= max(0, len(json_text) - 16)

        return not isinstance(parsed, dict)

    def _continue_prefilled_gpt_oss_tool_call(
        self,
        completion_kwargs: Dict[str, Any],
        raw_text: str,
    ) -> str:
        """Continue a truncated prefilled Harmony tool call body."""
        combined = raw_text or ""
        for attempt in range(2):
            if not self._prefilled_gpt_oss_tool_json_needs_continuation(
                combined
            ):
                break

            continuation_kwargs = dict(completion_kwargs)
            continuation_kwargs["prompt"] = (
                f"{completion_kwargs['prompt']}{combined}"
            )
            continuation_kwargs["max_tokens"] = min(self.max_tokens, 512)

            response = self._llama.create_completion(**continuation_kwargs)
            choice = response["choices"][0]
            continuation_text = choice.get("text", "") or ""
            if not continuation_text:
                break

            self.logger.info(
                "Continuing incomplete prefilled GPT-OSS tool JSON "
                "(attempt %s)",
                attempt + 1,
            )
            combined += continuation_text

        return combined

    def _build_gpt_oss_message_from_raw(
        self,
        raw_text: str,
    ) -> AIMessage:
        """Normalize one raw Harmony completion into an AIMessage."""
        parsed = parse_gpt_oss_response(raw_text)
        content = parsed.content
        tool_calls = self._parse_gpt_oss_commentary_tool_calls(raw_text)
        suppressed_prefilled_payload = False
        if not tool_calls:
            tool_calls = self._parse_prefilled_gpt_oss_tool_call(raw_text)
            if not tool_calls:
                suppressed_prefilled_payload = (
                    bool(self._forced_gpt_oss_tool_name())
                    and looks_like_tool_argument_payload(raw_text)
                )
        if tool_calls:
            content = ""
        else:
            tool_calls, content = self._extract_tool_calls(content or raw_text)
            if suppressed_prefilled_payload and not tool_calls:
                self.logger.warning(
                    "Suppressing malformed prefilled GPT-OSS tool payload"
                )
                content = ""

        additional_kwargs: Dict[str, Any] = {}
        if parsed.thinking_content:
            additional_kwargs["thinking_content"] = parsed.thinking_content
        if suppressed_prefilled_payload:
            additional_kwargs["suppressed_malformed_tool_payload"] = True

        return AIMessage(
            content=content,
            tool_calls=tool_calls,
            additional_kwargs=additional_kwargs,
        )

    def _format_gpt_oss_namespace(self) -> str:
        """Format bound tools as a Harmony functions namespace."""
        shared_defs: Dict[str, Dict[str, Any]] = {}
        lines = ["namespace functions {", ""]

        for tool in self.tools or []:
            function = tool.get("function", tool)
            parameters = function.get("parameters", {})
            shared_defs.update(parameters.get("$defs", {}))

        if shared_defs:
            lines.extend(self._format_gpt_oss_shared_definitions(shared_defs))
            lines.append("")

        for tool in self.tools or []:
            function = tool.get("function", tool)
            lines.extend(self._format_gpt_oss_tool(function))
            lines.append("")

        while lines and not lines[-1]:
            lines.pop()
        lines.append("} // namespace functions")
        return "\n".join(lines)

    def _format_gpt_oss_shared_definitions(
        self,
        shared_defs: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Format shared schema definitions for Harmony tool prompts."""
        lines: List[str] = []
        for name, schema in shared_defs.items():
            type_definition = self._format_gpt_oss_type(schema, 1)
            lines.append(f"type {name} = {type_definition};")
        return lines

    def _format_gpt_oss_tool(self, tool: Dict[str, Any]) -> List[str]:
        """Format one tool schema as a Harmony type definition."""
        description = tool.get("description", "")
        parameters = tool.get("parameters", {})
        properties = parameters.get("properties", {})
        required = set(parameters.get("required", []))
        name = tool.get("name", "unknown_tool")
        lines = [f"// {description}" if description else "// Tool"]

        if not properties:
            lines.append(f"type {name} = () => any;")
            return lines

        lines.append(f"type {name} = (_: {{")
        for param_name, schema in properties.items():
            param_description = schema.get("description", "")
            if param_description:
                lines.append(f"// {param_description}")
            param_type = self._format_gpt_oss_type(schema, 1)
            optional = "" if param_name in required else "?"
            lines.append(f"{param_name}{optional}: {param_type},")
        lines.append("}) => any;")
        return lines

    def _format_gpt_oss_type(
        self,
        schema: Dict[str, Any],
        indent_level: int = 0,
    ) -> str:
        """Convert a JSON schema fragment to a Harmony-style type."""
        if not isinstance(schema, dict):
            return "any"

        if "$ref" in schema:
            return str(schema["$ref"]).rsplit("/", 1)[-1]

        variants = schema.get("anyOf") or schema.get("oneOf")
        if variants:
            return " | ".join(
                self._format_gpt_oss_type(variant, indent_level)
                for variant in variants
            )

        if "enum" in schema:
            return " | ".join(
                json.dumps(value)
                for value in schema.get("enum", [])
            )

        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            return " | ".join(str(item) for item in schema_type)
        if schema_type == "array":
            item_type = self._format_gpt_oss_type(
                schema.get("items", {}),
                indent_level + 1,
            )
            return f"Array<{item_type}>"
        if schema_type == "object":
            return self._format_gpt_oss_object_type(
                schema,
                indent_level + 1,
            )
        if isinstance(schema_type, str):
            return schema_type
        return "any"

    def _format_gpt_oss_object_type(
        self,
        schema: Dict[str, Any],
        indent_level: int,
    ) -> str:
        """Format one JSON object schema as an inline type block."""
        properties = schema.get("properties", {})
        if not properties:
            return "object"

        required = set(schema.get("required", []))
        indent = "  " * indent_level
        closing_indent = "  " * max(indent_level - 1, 0)
        lines = ["{"]
        for name, child in properties.items():
            child_type = self._format_gpt_oss_type(child, indent_level + 1)
            optional = "" if name in required else "?"
            lines.append(f"{indent}{name}{optional}: {child_type},")
        lines.append(f"{closing_indent}}}")
        return "\n".join(lines)

    def _inject_react_tool_instructions(self, system_content: str) -> str:
        """Inject ReAct-style tool instructions for text tool calling."""
        tool_defs = []
        for tool in self.tools or []:
            func = tool.get("function", tool)
            tool_defs.append(self._format_react_tool(func))

        tools_text = "\n".join(tool_defs)
        react_instructions = (
            "\n\n# Tools\n\n"
            "You have access to the following tools:\n"
            f"{tools_text}\n\n"
            "To use a tool, respond EXACTLY in this format:\n"
            "Action: tool_name\n"
            'Action Input: {"arg": "value"}\n\n'
            "Do not wrap tool calls in markdown fences. After the tool "
            "result arrives, continue with your answer or the next tool "
            "call."
        )
        return system_content + react_instructions

    def _format_react_tool(self, tool: Dict[str, Any]) -> str:
        """Format one OpenAI tool schema as a compact ReAct tool line."""
        name = tool.get("name", "unknown_tool")
        description = tool.get("description", "")
        parameters = tool.get("parameters", {}).get("properties", {})
        required = set(tool.get("parameters", {}).get("required", []))

        args = []
        for param_name, param_info in parameters.items():
            arg_type = param_info.get("type", "any")
            marker = "*" if param_name in required else ""
            args.append(f"{param_name}{marker}: {arg_type}")

        signature = ", ".join(args)
        short_description = description.split(".")[0] if description else ""
        return f"- {name}({signature}) - {short_description}"

    def _convert_langchain_tool_calls(
        self,
        tool_calls: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Convert LangChain tool call records to OpenAI chat format."""
        converted: List[Dict[str, Any]] = []
        for tool_call in tool_calls or []:
            openai_call = self._convert_langchain_tool_call(tool_call)
            if openai_call is not None:
                converted.append(openai_call)
        return converted

    def _convert_langchain_tool_call(
        self,
        tool_call: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Convert one LangChain tool call to OpenAI chat format."""
        if not isinstance(tool_call, dict):
            return None

        function = tool_call.get("function") or {}
        name = tool_call.get("name") or function.get("name")
        if not name:
            return None

        arguments = tool_call.get("args", function.get("arguments", {}))
        if not isinstance(arguments, str):
            try:
                arguments = json.dumps(arguments or {}, sort_keys=True)
            except TypeError:
                arguments = "{}"

        return {
            "id": tool_call.get("id") or str(uuid.uuid4()),
            "type": "function",
            "function": {
                "name": name,
                "arguments": arguments,
            },
        }

    def _apply_thinking_directive(
        self, converted: List[Dict[str, Any]]
    ) -> None:
        """Prefix the final Qwen3 user turn with a no-think directive."""
        model_path = str(self.model_path).lower()
        if self.enable_thinking or "qwen3" not in model_path:
            return

        for message in reversed(converted):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if not isinstance(content, str):
                return

            stripped = content.lstrip()
            if stripped.startswith("/no_think") or stripped.startswith(
                "/think"
            ):
                return

            message["content"] = f"/no_think\n{content}"
            return

    def _extract_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Extract text-encoded tool calls and cleaned response text."""
        react_calls, react_text = self._parse_react_tool_calls(content)
        if react_calls:
            return react_calls, react_text

        xml_calls, xml_text = self._parse_xml_tool_calls(content)
        return xml_calls, xml_text

    def _parse_gpt_oss_commentary_tool_calls(
        self, content: str
    ) -> List[Dict[str, Any]]:
        """Parse GPT-OSS Harmony commentary tool calls from raw output."""
        tool_calls: List[Dict[str, Any]] = []
        pattern = re.compile(
            r"(?:<\|start\|>assistant(?P<role_header>[^<]*))?"
            r"<\|channel\|>(?P<channel_header>[^<]*)"
            r"(?:<\|constrain\|>(?P<constraint>[^<]*))?"
            r"<\|message\|>(?P<body>.*?)(?P<terminator><\|call\|>|"
            r"<\|end\|>|<\|return\|>|$)",
            re.DOTALL,
        )

        for match in pattern.finditer(content or ""):
            channel_header = (match.group("channel_header") or "").strip()
            channel_name = channel_header.split()[0] if channel_header else ""
            if channel_name != "commentary":
                continue
            terminator = match.group("terminator") or ""
            if terminator not in {"<|call|>", ""}:
                continue

            recipient = self._extract_gpt_oss_recipient(
                match.group("role_header"),
                channel_header,
            )
            if not recipient or not recipient.startswith("functions."):
                continue

            body = (match.group("body") or "").strip()
            if not body:
                continue

            try:
                arguments = json.loads(body)
            except json.JSONDecodeError as exc:
                self.logger.warning(
                    "Failed to parse GPT-OSS Harmony tool call JSON for %s: %s",
                    recipient,
                    exc,
                )
                continue

            tool_calls.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": recipient.removeprefix("functions."),
                    "args": arguments if isinstance(arguments, dict) else {},
                    "type": "tool_call",
                }
            )

        return tool_calls

    def _extract_prefilled_gpt_oss_tool_json(self, content: str) -> str:
        """Return JSON emitted after a prefilled Harmony tool envelope."""
        candidate = (content or "").strip()
        if not candidate:
            return ""

        marker_indexes = [
            candidate.find(token)
            for token in (CALL_TOKEN, END_TOKEN, RETURN_TOKEN)
            if token in candidate
        ]
        if marker_indexes:
            candidate = candidate[: min(marker_indexes)].strip()

        fenced = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            candidate,
            re.DOTALL,
        )
        if fenced:
            candidate = fenced.group(1).strip()

        if candidate.startswith("{"):
            return candidate
        return ""

    def _parse_prefilled_gpt_oss_tool_call(
        self,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Parse one forced Harmony tool call from a bare JSON body."""
        tool_name = self._forced_gpt_oss_tool_name()
        json_text = self._extract_prefilled_gpt_oss_tool_json(content)
        if not tool_name or not json_text:
            return []

        try:
            arguments = json.loads(json_text)
        except json.JSONDecodeError as exc:
            self.logger.warning(
                "Failed to parse prefilled GPT-OSS tool JSON for %s: %s",
                tool_name,
                exc,
            )
            return []

        if not isinstance(arguments, dict):
            return []

        return [
            {
                "id": str(uuid.uuid4()),
                "name": tool_name,
                "args": arguments,
                "type": "tool_call",
            }
        ]

    def _extract_gpt_oss_recipient(
        self,
        role_header: Optional[str],
        channel_header: str,
    ) -> Optional[str]:
        """Return the Harmony tool recipient from role or channel header."""
        for header in (role_header or "", channel_header or ""):
            match = re.search(r"\bto=([^\s<]+)", header)
            if match:
                return match.group(1).strip()
        return None

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Parse text-encoded tool calls from model response text."""
        tool_calls, _ = self._extract_tool_calls(content)
        return tool_calls

    def _parse_xml_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse XML-tagged tool calls from model response text."""
        tool_calls = []

        # Find all <tool_call>...</tool_call> blocks
        pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            try:
                # Parse the JSON inside the tool_call tags
                call_data = json.loads(match.strip())
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": call_data.get("name"),
                    "args": call_data.get("arguments", {}),
                    "type": "tool_call",
                })
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse tool call JSON: {e}")
                continue

        cleaned = re.sub(
            r'<tool_call>\s*.*?\s*</tool_call>',
            '',
            content,
            flags=re.DOTALL,
        ).strip()
        return tool_calls, cleaned

    def _parse_react_tool_calls(
        self, content: str
    ) -> tuple[List[Dict[str, Any]], str]:
        """Parse ReAct tool calls from model response text."""
        tool_calls = []
        cleaned_text = content
        react_pattern = (
            r"Action:\s*(\w+)(?:\([^)]*\))?\s*Action Input:\s*"
            r"(.*?)(?=\s*Action:|$)"
        )
        react_matches = re.findall(react_pattern, content, re.DOTALL)

        for tool_name, raw_input in react_matches:
            normalized = raw_input.strip().rstrip("</s> ")

            while (
                normalized.startswith("{{")
                and normalized.endswith("}}")
                and len(normalized) > 4
            ):
                normalized = normalized[1:-1]

            while normalized.startswith("{") and normalized.endswith("}}"):
                normalized = normalized[:-1]

            while normalized.startswith("{{") and normalized.endswith("}"):
                normalized = normalized[1:]

            if not (
                normalized.startswith("{") and normalized.endswith("}")
            ):
                brace_match = re.search(r"\{.*\}", normalized, re.DOTALL)
                if brace_match:
                    normalized = brace_match.group(0).strip()

            if not (
                normalized.startswith("{") and normalized.endswith("}")
            ):
                continue

            try:
                args = json.loads(normalized)
            except json.JSONDecodeError as e:
                snippet = normalized[:200].replace("\n", " ")
                self.logger.error(
                    "Failed to parse ReAct JSON for %s: %s | snippet=%s",
                    tool_name,
                    e,
                    snippet,
                )
                continue

            tool_calls.append(
                {
                    "name": tool_name,
                    "args": args,
                    "id": f"call_{len(tool_calls)}",
                    "type": "tool_call",
                }
            )

        if react_matches:
            cleaned_text = re.sub(
                react_pattern,
                "",
                content,
                flags=re.DOTALL,
            ).strip()
            cleaned_text = re.sub(
                r"\n?Observation:\s*\[.*?\]",
                "",
                cleaned_text,
                flags=re.DOTALL,
            ).strip()

        return tool_calls, cleaned_text

    def _parse_native_tool_calls(
        self, raw_tool_calls: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Parse OpenAI-style native tool calls from llama.cpp responses."""
        tool_calls: List[Dict[str, Any]] = []

        for raw_call in raw_tool_calls or []:
            function = raw_call.get("function", {}) if isinstance(raw_call, dict) else {}
            arguments = function.get("arguments", {})

            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments.strip() else {}
                except json.JSONDecodeError:
                    self.logger.warning(
                        "Failed to parse native tool arguments for %s",
                        function.get("name", "unknown"),
                    )
                    arguments = {}

            tool_calls.append(
                {
                    "id": raw_call.get("id") or str(uuid.uuid4()),
                    "name": function.get("name"),
                    "args": arguments if isinstance(arguments, dict) else {},
                    "type": "tool_call",
                }
            )

        return tool_calls

    def _merge_streamed_tool_delta_text(
        self,
        current: str,
        incoming: str,
    ) -> str:
        """Merge one streamed tool delta field.

        llama.cpp can stream either incremental fragments or repeated
        cumulative values for native tool calls. Prefer the longest prefix
        when chunks overlap, and only append when the incoming value is a
        genuine suffix fragment.
        """
        current = current or ""
        incoming = incoming or ""
        if not incoming:
            return current
        if not current:
            return incoming
        if incoming == current or current.startswith(incoming):
            return current
        if incoming.startswith(current):
            return incoming
        return f"{current}{incoming}"

    def _merge_native_tool_call_deltas(
        self,
        tool_call_buffers: Dict[int, Dict[str, Any]],
        raw_tool_calls: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Merge streaming native tool call deltas into a complete structure."""
        for raw_call in raw_tool_calls or []:
            index = raw_call.get("index", len(tool_call_buffers))
            buffer = tool_call_buffers.setdefault(
                index,
                {
                    "id": None,
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                },
            )

            if raw_call.get("id"):
                buffer["id"] = raw_call["id"]
            if raw_call.get("type"):
                buffer["type"] = raw_call["type"]

            function = raw_call.get("function") or {}
            if function.get("name"):
                buffer["function"]["name"] = (
                    self._merge_streamed_tool_delta_text(
                        buffer["function"]["name"],
                        function["name"],
                    )
                )
            if function.get("arguments"):
                buffer["function"]["arguments"] = (
                    self._merge_streamed_tool_delta_text(
                        buffer["function"]["arguments"],
                        function["arguments"],
                    )
                )

    def _finalize_native_tool_call_deltas(
        self, tool_call_buffers: Dict[int, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert buffered streaming tool call deltas into normalized tool calls."""
        if not tool_call_buffers:
            return []

        ordered_calls = [tool_call_buffers[index] for index in sorted(tool_call_buffers)]
        return self._parse_native_tool_calls(ordered_calls)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response using native chat completion API.

        For Qwen3 models, tools are injected into the system prompt and
        tool calls are parsed from <tool_call> XML tags in the response.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Returns:
            ChatResult with generated response
        """
        with self._temporary_runtime_overrides(kwargs):
            if self._use_raw_gpt_oss_completion():
                completion_kwargs = self._build_gpt_oss_completion_kwargs(
                    messages,
                    stop,
                    stream=False,
                )
                call_started = time.perf_counter()
                response = self._llama.create_completion(**completion_kwargs)
                self.logger.info(
                    "[ChatGGUF._generate] create_completion returned in %.3fs",
                    time.perf_counter() - call_started,
                )
                choice = response["choices"][0]
                raw_text = choice.get("text", "") or ""
                raw_text = self._continue_prefilled_gpt_oss_tool_call(
                    completion_kwargs,
                    raw_text,
                )
                message = self._build_gpt_oss_message_from_raw(raw_text)
                return ChatResult(
                    generations=[ChatGeneration(message=message)]
                )

            converted_messages = self._convert_messages(messages)

            chat_kwargs = {
                "messages": converted_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "min_p": self.min_p,
                "repeat_penalty": self.repeat_penalty,
                "stream": False,
            }

            if stop:
                chat_kwargs["stop"] = stop

            native_tool_choice = self._native_tool_choice()

            if self._use_native_tool_calling():
                chat_kwargs["tools"] = self.tools
                if native_tool_choice is not None:
                    chat_kwargs["tool_choice"] = native_tool_choice

            if self._use_native_tool_calling():
                self.logger.debug(
                    f"[TOOL CALL] Passing {len(self.tools or [])} native tools to llama.cpp"
                )
            elif self.tools:
                self.logger.debug(
                    f"[TOOL CALL] {len(self.tools)} tools injected in system prompt"
                )
            else:
                self.logger.debug("[TOOL CALL] No tools bound")

            call_started = time.perf_counter()
            self.logger.debug(
                "[TOOL CALL] Calling create_chat_completion with "
                f"chat_format={self._detected_format}"
            )
            response = self._llama.create_chat_completion(**chat_kwargs)
            self.logger.info(
                "[ChatGGUF._generate] create_chat_completion returned in "
                f"{time.perf_counter() - call_started:.3f}s"
            )
            self.logger.debug(
                "[TOOL CALL] Response received (%s)",
                summarize_mapping_keys(response, label="response"),
            )

            choice = response["choices"][0]
            message_data = choice.get("message", {})
            content = message_data.get("content", "") or ""

            thinking_content = None
            if self.enable_thinking and hasattr(message_data, "get"):
                thinking_content = message_data.get("reasoning_content")

            gpt_oss_tool_calls: List[Dict[str, Any]] = []
            if self._uses_gpt_oss_parser() or has_gpt_oss_markup(content):
                gpt_oss_tool_calls = (
                    self._parse_gpt_oss_commentary_tool_calls(content)
                )
                parsed = parse_gpt_oss_response(content)
                content = parsed.content
                if not thinking_content:
                    thinking_content = parsed.thinking_content

            raw_native_tool_calls = (
                message_data.get("tool_calls")
                if hasattr(message_data, "get")
                else None
            )
            tool_calls = self._parse_native_tool_calls(raw_native_tool_calls)
            if not tool_calls:
                tool_calls, content = self._extract_tool_calls(content)
            if not tool_calls and gpt_oss_tool_calls:
                tool_calls = gpt_oss_tool_calls

            if tool_calls:
                self.logger.debug(
                    "[TOOL CALL] Parsed %s tool calls from response",
                    len(tool_calls),
                )

            additional_kwargs = {}
            if thinking_content:
                additional_kwargs["thinking_content"] = thinking_content

            message = AIMessage(
                content=content,
                tool_calls=tool_calls,
                additional_kwargs=additional_kwargs,
            )

            return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream response using native chat completion API.

        For Qwen3 models, tools are in the system prompt and tool calls
        are parsed from <tool_call> XML tags at the end of streaming.

        Args:
            messages: List of input messages
            stop: Optional stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional generation parameters

        Yields:
            ChatGenerationChunk objects with streamed content
        """
        with self._temporary_runtime_overrides(kwargs):
            if self._use_raw_gpt_oss_completion():
                completion_kwargs = self._build_gpt_oss_completion_kwargs(
                    messages,
                    stop,
                    stream=True,
                )
                full_content: List[str] = []
                parser = GPTOSSStreamParser()
                for chunk in self._llama.create_completion(**completion_kwargs):
                    if self._interrupted:
                        break

                    raw_text = chunk.get("choices", [{}])[0].get(
                        "text",
                        "",
                    )
                    if not raw_text:
                        continue

                    full_content.append(raw_text)
                    parsed_delta = parser.feed(raw_text)
                    if parsed_delta.analysis_text:
                        yield ChatGenerationChunk(
                            message=AIMessageChunk(
                                content="",
                                additional_kwargs={
                                    "reasoning_content": (
                                        parsed_delta.analysis_text
                                    ),
                                },
                            )
                        )

                    if parsed_delta.final_text:
                        chunk_msg = ChatGenerationChunk(
                            message=AIMessageChunk(
                                content=parsed_delta.final_text
                            )
                        )
                        if run_manager:
                            run_manager.on_llm_new_token(
                                parsed_delta.final_text,
                                chunk=chunk_msg,
                            )
                        yield chunk_msg

                parsed_tail = parser.finish()
                if parsed_tail.analysis_text:
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="",
                            additional_kwargs={
                                "reasoning_content": (
                                    parsed_tail.analysis_text
                                ),
                            },
                        )
                    )
                if parsed_tail.final_text:
                    tail_chunk = ChatGenerationChunk(
                        message=AIMessageChunk(
                            content=parsed_tail.final_text
                        )
                    )
                    if run_manager:
                        run_manager.on_llm_new_token(
                            parsed_tail.final_text,
                            chunk=tail_chunk,
                        )
                    yield tail_chunk

                raw_text = "".join(full_content)
                tool_calls = self._parse_gpt_oss_commentary_tool_calls(
                    raw_text
                )
                if not tool_calls:
                    tool_calls, _ = self._extract_tool_calls(raw_text)
                if tool_calls:
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="",
                            tool_calls=tool_calls,
                        )
                    )
                return

            self.logger.info("[ChatGGUF._stream] Starting stream generation")
            converted_messages = self._convert_messages(messages)
            self.logger.info(
                f"[ChatGGUF._stream] Converted {len(converted_messages)} messages"
            )

            chat_kwargs = {
                "messages": converted_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "min_p": self.min_p,
                "repeat_penalty": self.repeat_penalty,
                "stream": True,
            }

            if stop:
                chat_kwargs["stop"] = stop

            native_tool_choice = self._native_tool_choice()

            if self._use_native_tool_calling():
                chat_kwargs["tools"] = self.tools
                if native_tool_choice is not None:
                    chat_kwargs["tool_choice"] = native_tool_choice

            self._interrupted = False
            full_content = []
            native_tool_call_buffers: Dict[int, Dict[str, Any]] = {}

            call_started = time.perf_counter()
            self.logger.info(
                f"[ChatGGUF._stream] Calling create_chat_completion with max_tokens={self.max_tokens}"
            )
            self.logger.info(
                f"[ChatGGUF._stream] Number of tools bound: {len(self.tools) if self.tools else 0}"
            )
            self.logger.info(
                f"[ChatGGUF._stream] tool_choice: {native_tool_choice}"
            )

            chunk_count = 0
            gpt_oss_parser = (
                GPTOSSStreamParser() if self._uses_gpt_oss_parser() else None
            )
            for chunk in self._llama.create_chat_completion(**chat_kwargs):
                chunk_count += 1
                if chunk_count == 1:
                    self.logger.info(
                        f"[ChatGGUF._stream] First chunk received after {time.perf_counter() - call_started:.3f}s"
                    )
                if self._interrupted:
                    break

                delta = chunk.get("choices", [{}])[0].get("delta", {})

                if "tool_calls" in delta and delta["tool_calls"]:
                    self._merge_native_tool_call_deltas(
                        native_tool_call_buffers,
                        delta["tool_calls"],
                    )

                reasoning_text = delta.get("reasoning_content")

                if "content" in delta and delta["content"]:
                    raw_text = delta["content"]
                    full_content.append(raw_text)
                    text = raw_text

                    if gpt_oss_parser is not None or has_gpt_oss_markup(
                        raw_text
                    ):
                        if gpt_oss_parser is None:
                            gpt_oss_parser = GPTOSSStreamParser()
                        parsed_delta = gpt_oss_parser.feed(raw_text)
                        if parsed_delta.analysis_text:
                            reasoning_text = (
                                f"{reasoning_text}{parsed_delta.analysis_text}"
                                if reasoning_text
                                else parsed_delta.analysis_text
                            )
                        text = parsed_delta.final_text

                    additional_kwargs: Dict[str, Any] = {}
                    if reasoning_text:
                        additional_kwargs["reasoning_content"] = (
                            reasoning_text
                        )

                    chunk_msg = ChatGenerationChunk(
                        message=AIMessageChunk(
                            content=text,
                            additional_kwargs=additional_kwargs,
                        )
                    )

                    if run_manager:
                        run_manager.on_llm_new_token(text, chunk=chunk_msg)

                    yield chunk_msg
                else:
                    additional_kwargs = {}
                    if reasoning_text:
                        additional_kwargs["reasoning_content"] = (
                            reasoning_text
                        )
                if not (
                    "content" in delta and delta["content"]
                ) and additional_kwargs:
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="",
                            additional_kwargs=additional_kwargs,
                        )
                    )

            if gpt_oss_parser is not None:
                parsed_tail = gpt_oss_parser.finish()
                if parsed_tail.analysis_text:
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="",
                            additional_kwargs={
                                "reasoning_content": (
                                    parsed_tail.analysis_text
                                ),
                            },
                        )
                    )
                if parsed_tail.final_text:
                    tail_chunk = ChatGenerationChunk(
                        message=AIMessageChunk(
                            content=parsed_tail.final_text
                        )
                    )
                    if run_manager:
                        run_manager.on_llm_new_token(
                            parsed_tail.final_text,
                            chunk=tail_chunk,
                        )
                    yield tail_chunk

            self.logger.info(
                f"[ChatGGUF._stream] Stream loop finished in {time.perf_counter() - call_started:.3f}s. "
                f"Total chunks: {chunk_count}, content length: {len(''.join(full_content))}"
            )
            full_text = "".join(full_content)
            gpt_oss_tool_calls = self._parse_gpt_oss_commentary_tool_calls(
                full_text
            )
            tool_calls = self._finalize_native_tool_call_deltas(
                native_tool_call_buffers
            )
            if not tool_calls:
                tool_calls, _ = self._extract_tool_calls(full_text)
            if not tool_calls and gpt_oss_tool_calls:
                tool_calls = gpt_oss_tool_calls

            if tool_calls:
                self.logger.debug(
                    f"[TOOL CALL] Parsed {len(tool_calls)} tool calls from streamed response"
                )
                yield ChatGenerationChunk(
                    message=AIMessageChunk(
                        content="",
                        tool_calls=tool_calls,
                    )
                )

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to this chat model.

        Args:
            tools: List of tools to bind (will be converted to OpenAI format)
            tool_choice: Tool selection strategy. Internal callers may use
                "any" to require some tool; llama.cpp receives "required".
            **kwargs: Additional arguments

        Returns:
            Copy of this model with tools bound
        """
        bound_model = self.model_copy(deep=False)

        # Convert tools to OpenAI format
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]

        bound_model.tools = formatted_tools
        bound_model.tool_choice = tool_choice

        # Reload model with function calling format if needed
        bound_model._reload_with_tools()

        return bound_model

    def get_tool_schemas_text(self) -> str:
        """Get formatted tool schemas for compatibility.
        
        Note: This is mainly for debugging/logging. The actual tool
        formatting is handled by llama-cpp-python's chat format.
        """
        if not self.tools:
            return ""

        lines = []
        for tool in self.tools:
            func = tool.get("function", tool)
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])

            param_strs = []
            for k, v in params.items():
                req = "*" if k in required else ""
                param_strs.append(f"{k}{req}: {v.get('type', 'any')}")

            lines.append(f"- {name}({', '.join(param_strs)}): {desc}")

        return "\n".join(lines)


def find_gguf_file(
    model_dir: str,
    preferred_filename: Optional[str] = None,
) -> Optional[str]:
    """Find a GGUF file in a model directory.

    Args:
        model_dir: Directory to search
        preferred_filename: Preferred GGUF filename when one is known

    Returns:
        Path to GGUF file if found, None otherwise
    """
    model_path = Path(model_dir)
    if not model_path.exists():
        return None

    # Look for GGUF files (prefer Q4_K_M)
    gguf_files = sorted(
        model_path.glob("*.gguf"),
        key=lambda path: path.name.lower(),
    )

    if not gguf_files:
        return None

    if preferred_filename:
        preferred_name = str(preferred_filename).strip()
        for gguf_file in gguf_files:
            if gguf_file.name == preferred_name:
                return str(gguf_file)
        preferred_name = preferred_name.lower()
        for gguf_file in gguf_files:
            if gguf_file.name.lower() == preferred_name:
                return str(gguf_file)

    # Prefer Q4_K_M quantization
    for f in gguf_files:
        if "Q4_K_M" in f.name or "q4_k_m" in f.name:
            return str(f)

    # Fall back to first GGUF file
    return str(gguf_files[0])


def is_gguf_model(model_path: str) -> bool:
    """Check if a model path contains a GGUF model.

    Args:
        model_path: Path to model directory or file

    Returns:
        True if GGUF model found
    """
    path = Path(model_path)

    # Direct GGUF file
    if path.suffix == ".gguf":
        return path.exists()

    # Directory containing GGUF
    if path.is_dir():
        return find_gguf_file(str(path)) is not None

    return False
