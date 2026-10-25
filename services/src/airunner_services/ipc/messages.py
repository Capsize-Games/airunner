"""Transport-neutral request and response envelopes."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

#: Upper bound on the serialized payload/metadata of one envelope.
#: Audio-bearing STT payloads are base64 text, so this must stay above
#: the largest accepted clip (see MAX_STT_AUDIO_BYTES); anything larger
#: is rejected at the transport boundary instead of being decoded.
MAX_ENVELOPE_PAYLOAD_BYTES = 32 * 1024 * 1024


class EnvelopeStatus(str, Enum):
    """Status values shared across transport boundaries."""

    ACCEPTED = "accepted"
    STREAM = "stream"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorEnvelope(BaseModel):
    """Error payload returned by a runtime boundary."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class RequestEnvelope(BaseModel):
    """Envelope used for daemon and runtime requests."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    runtime: RuntimeKind
    action: RuntimeAction
    provider: Optional[str] = None
    stream: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _payload_must_fit_transport_budget(self) -> "RequestEnvelope":
        size = _rough_json_size(self.payload) + _rough_json_size(self.metadata)
        if size > MAX_ENVELOPE_PAYLOAD_BYTES:
            raise ValueError(
                f"envelope payload exceeds {MAX_ENVELOPE_PAYLOAD_BYTES} bytes"
            )
        return self


class ResponseEnvelope(BaseModel):
    """Envelope returned by runtime clients and sidecars."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: EnvelopeStatus
    payload: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[ErrorEnvelope] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _rough_json_size(value: Any) -> int:
    """Estimate the serialized size of one envelope mapping."""
    if isinstance(value, str):
        return len(value.encode("utf-8", "replace"))
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, dict):
        return sum(
            _rough_json_size(key) + _rough_json_size(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return sum(_rough_json_size(item) for item in value)
    if value is None or isinstance(value, bool):
        return 4
    return len(str(value).encode("utf-8", "replace"))


class StreamDelta(BaseModel):
    """Streaming delta emitted by a runtime request."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    sequence: int = 0
    delta: Dict[str, Any] = Field(default_factory=dict)
    final: bool = False
    status: EnvelopeStatus = EnvelopeStatus.STREAM
    metadata: Dict[str, Any] = Field(default_factory=dict)