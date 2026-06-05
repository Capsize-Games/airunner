"""Transport-neutral request and response envelopes."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind


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


class ResponseEnvelope(BaseModel):
    """Envelope returned by runtime clients and sidecars."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: EnvelopeStatus
    payload: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[ErrorEnvelope] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamDelta(BaseModel):
    """Streaming delta emitted by a runtime request."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    sequence: int = 0
    delta: Dict[str, Any] = Field(default_factory=dict)
    final: bool = False
    status: EnvelopeStatus = EnvelopeStatus.STREAM
    metadata: Dict[str, Any] = Field(default_factory=dict)
