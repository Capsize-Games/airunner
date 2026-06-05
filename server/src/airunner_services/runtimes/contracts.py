"""Runtime modality contracts and descriptors."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    WEBSOCKET = "websocket"


class RuntimeAction(str, Enum):
    """Actions supported by the daemon and runtime boundary."""

    HEALTH = "health"
    LOAD_MODEL = "load_model"
    UNLOAD_MODEL = "unload_model"
    INVOKE = "invoke"
    CANCEL = "cancel"
    STATUS = "status"


class MessageRole(str, Enum):
    """LLM message roles shared by API and runtime requests."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """Neutral chat message representation."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str
    name: Optional[str] = None


class LLMInvocationRequest(BaseModel):
    """Request payload for LLM invocation."""

    model_config = ConfigDict(extra="forbid")

    model: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    stream: bool = False
    tool_choice: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


class TTSInvocationRequest(BaseModel):
    """Request payload for text-to-speech execution."""

    model_config = ConfigDict(extra="forbid")

    text: str
    model: Optional[str] = None
    voice: Optional[str] = None
    speed: float = 1.0
    stream: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
