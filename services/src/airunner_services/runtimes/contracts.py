"""Runtime modality contracts and descriptors."""

from __future__ import annotations

import json
import math
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from airunner_common.contract_enums import MessageRole  # re-exported (#2221)
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_LLM_FUNCTION_TOOLS = 16
MAX_LLM_FUNCTION_TOOL_BYTES = 64 * 1024
MAX_LLM_TOOL_CALLS = 16
MAX_LLM_TOOL_CALL_BYTES = 64 * 1024
MAX_LLM_TOOL_ARGUMENT_BYTES = 16 * 1024
MAX_LLM_TOOL_NAME_CHARS = 128
MAX_LLM_TOOL_CALL_ID_CHARS = 256


def _bounded_json_size(value: Any, limit: int, label: str) -> None:
    try:
        size = len(
            json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain JSON values") from exc
    if size > limit:
        raise ValueError(f"{label} exceeds the configured size limit")


def _valid_function_name(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= MAX_LLM_TOOL_NAME_CHARS
        and not any(char in value for char in ("\x00", "\n", "\r"))
    )


def validate_function_tools(value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bound standard function definitions; schemas are forwarded, never executed."""
    if len(value) > MAX_LLM_FUNCTION_TOOLS:
        raise ValueError("too many function tools")
    for tool in value:
        function = tool.get("function") if isinstance(tool, dict) else None
        if (
            not isinstance(tool, dict)
            or tool.get("type") != "function"
            or not isinstance(function, dict)
        ):
            raise ValueError("function tools must use the standard function schema")
        if not _valid_function_name(function.get("name")):
            raise ValueError("function name is invalid")
        description = function.get("description")
        if description is not None and (not isinstance(description, str) or len(description) > 4096):
            raise ValueError("function description is invalid")
        parameters = function.get("parameters")
        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("function parameters must be a JSON schema object")
        strict = function.get("strict")
        if strict is not None and not isinstance(strict, bool):
            raise ValueError("function strict must be a boolean")
    _bounded_json_size(value, MAX_LLM_FUNCTION_TOOL_BYTES, "function tools")
    return value


def validate_tool_choice(
    value: Optional[Union[str, Dict[str, Any]]],
) -> Optional[Union[str, Dict[str, Any]]]:
    """Bound string and standard named-function tool choices."""
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip() or len(value) > MAX_LLM_TOOL_NAME_CHARS:
            raise ValueError("tool choice is invalid")
        return value
    if not isinstance(value, dict):
        raise ValueError("tool choice must be a string or function choice object")
    function = value.get("function")
    if (
        value.get("type") != "function"
        or not isinstance(function, dict)
        or not _valid_function_name(function.get("name"))
    ):
        raise ValueError("function tool choice is invalid")
    _bounded_json_size(value, 1024, "tool choice")
    return value


def validate_message_tool_calls(value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bound standard assistant function-call messages before backend forwarding."""
    if len(value) > MAX_LLM_TOOL_CALLS:
        raise ValueError("too many tool calls in one message")
    for call in value:
        function = call.get("function") if isinstance(call, dict) else None
        if not isinstance(call, dict) or call.get("type") != "function" or not isinstance(function, dict):
            raise ValueError("tool calls must use the standard function-call shape")
        call_id = call.get("id")
        if not isinstance(call_id, str) or not call_id.strip() or len(call_id) > MAX_LLM_TOOL_CALL_ID_CHARS:
            raise ValueError("tool call id is invalid")
        if not _valid_function_name(function.get("name")):
            raise ValueError("tool call function name is invalid")
        arguments = function.get("arguments")
        if not isinstance(arguments, str) or len(arguments.encode("utf-8")) > MAX_LLM_TOOL_ARGUMENT_BYTES:
            raise ValueError("tool call arguments are invalid")
    _bounded_json_size(value, MAX_LLM_TOOL_CALL_BYTES, "message tool calls")
    return value


class RuntimeKind(str, Enum):
    """Supported runtime modalities."""

    LLM = "llm"
    STT = "stt"
    TTS = "tts"
    ART = "art"


class RuntimeMode(str, Enum):
    """Execution mode used by a runtime."""

    LOCAL_FALLBACK = "local_fallback"
    WORKER_PROCESS = "worker_process"
    SIDECAR = "sidecar"


class TransportKind(str, Enum):
    """Transport used to reach a runtime."""

    IN_PROCESS = "in_process"
    UNIX_SOCKET = "unix_socket"
    HTTP = "http"


class RuntimeAction(str, Enum):
    """Actions supported by the daemon and runtime boundary."""

    HEALTH = "health"
    LOAD_MODEL = "load_model"
    UNLOAD_MODEL = "unload_model"
    INVOKE = "invoke"
    CANCEL = "cancel"
    STATUS = "status"


class ChatMessage(BaseModel):
    """Neutral chat message representation."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: Optional[str]
    name: Optional[str] = Field(default=None, max_length=MAX_LLM_TOOL_NAME_CHARS)
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, max_length=MAX_LLM_TOOL_CALLS
    )
    tool_call_id: Optional[str] = Field(
        default=None, min_length=1, max_length=MAX_LLM_TOOL_CALL_ID_CHARS
    )

    @field_validator("tool_calls")
    @classmethod
    def _validate_tool_calls(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return validate_message_tool_calls(value)

    @model_validator(mode="after")
    def _validate_tool_message_shape(self) -> "ChatMessage":
        if self.tool_calls and self.role is not MessageRole.ASSISTANT:
            raise ValueError("only assistant messages may contain tool calls")
        if self.role is MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")
        if self.tool_call_id is not None and self.role is not MessageRole.TOOL:
            raise ValueError("tool_call_id is only valid on tool messages")
        if self.content is None and not (
            self.role is MessageRole.ASSISTANT and self.tool_calls
        ):
            raise ValueError("null content is only valid for assistant tool calls")
        return self


class LLMInvocationRequest(BaseModel):
    """Request payload for LLM invocation."""

    model_config = ConfigDict(extra="forbid")

    model: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    stream: bool = False
    enable_thinking: Optional[bool] = None
    tools: List[Dict[str, Any]] = Field(
        default_factory=list, max_length=MAX_LLM_FUNCTION_TOOLS
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tools")
    @classmethod
    def _validate_tools(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return validate_function_tools(value)

    @field_validator("tool_choice")
    @classmethod
    def _validate_tool_choice(
        cls, value: Optional[Union[str, Dict[str, Any]]]
    ) -> Optional[Union[str, Dict[str, Any]]]:
        return validate_tool_choice(value)


class STTInvocationRequest(BaseModel):
    """Request payload for speech-to-text execution."""

    model_config = ConfigDict(extra="forbid")

    model: Optional[str] = None
    audio_b64: str
    mime_type: str = "audio/wav"
    language: Optional[str] = None
    sample_rate: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


TTS_TEXT_MAX_LENGTH = 5000
TTS_SPEED_MIN = 0.25
TTS_SPEED_MAX = 4.0
TTS_NAME_MAX_LENGTH = 256


class TTSInvocationRequest(BaseModel):
    """Request payload for text-to-speech execution."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=TTS_TEXT_MAX_LENGTH)
    model: Optional[str] = Field(default=None, max_length=TTS_NAME_MAX_LENGTH)
    voice: Optional[str] = Field(default=None, max_length=TTS_NAME_MAX_LENGTH)
    speed: float = 1.0
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("speed")
    @classmethod
    def _speed_must_be_finite_and_bounded(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("speed must be finite")
        if not TTS_SPEED_MIN <= value <= TTS_SPEED_MAX:
            raise ValueError(
                f"speed must be between {TTS_SPEED_MIN} and {TTS_SPEED_MAX}"
            )
        return value

    @field_validator("model", "voice")
    @classmethod
    def _names_must_be_plain(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("model/voice names must not be blank")
        if any(char in text for char in ("\x00", "\n", "\r")):
            raise ValueError("model/voice names contain invalid characters")
        return text


class ArtInvocationRequest(BaseModel):
    """Request payload for art generation execution."""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    negative_prompt: str = ""
    model: Optional[str] = None
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.5
    seed: Optional[int] = None
    num_images: int = 1
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMInvocationResponse(BaseModel):
    """Response payload for LLM invocation."""

    model_config = ConfigDict(extra="forbid")

    content: str
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)


class STTInvocationResponse(BaseModel):
    """Response payload for speech-to-text execution."""

    model_config = ConfigDict(extra="forbid")

    text: str
    language: Optional[str] = None


class TTSInvocationResponse(BaseModel):
    """Response payload for text-to-speech execution."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool = True
    audio_b64: Optional[str] = None


class ArtInvocationResponse(BaseModel):
    """Response payload for art generation execution."""

    model_config = ConfigDict(extra="forbid")

    images: List[str] = Field(default_factory=list)
    image_count: int = 0
    node_id: Optional[str] = None


class RuntimeDescriptor(BaseModel):
    """Descriptor used by the runtime registry and health checks."""

    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeKind
    provider: str
    mode: RuntimeMode
    transport: TransportKind
    endpoint: Optional[str] = None
    supports_streaming: bool = False
    allows_model_control: bool = True


class RuntimeHealthStatus(str, Enum):
    """Health status reported by a runtime client."""

    UNKNOWN = "unknown"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


class RuntimeHealth(BaseModel):
    """Health payload shared by daemon and runtime clients."""

    model_config = ConfigDict(extra="forbid")

    descriptor: RuntimeDescriptor
    status: RuntimeHealthStatus = RuntimeHealthStatus.UNKNOWN
    details: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
