"""Base interfaces for runtime clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from airunner.ipc.messages import (
        RequestEnvelope,
        ResponseEnvelope,
        StreamDelta,
    )
    from airunner.runtimes.contracts import RuntimeDescriptor, RuntimeHealth


class RuntimeClient(ABC):
    """Interface implemented by daemon-facing runtime clients."""

    descriptor: RuntimeDescriptor

    @abstractmethod
    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        """Execute a non-streaming request."""

    def stream(self, request: RequestEnvelope) -> Iterable[StreamDelta]:
        """Stream request output when the runtime supports it."""
        raise NotImplementedError("Streaming is not implemented")

    @abstractmethod
    def healthcheck(self) -> RuntimeHealth:
        """Return runtime health information."""

    def cancel(self, request_id: str) -> ResponseEnvelope:
        """Cancel a previously submitted request when supported."""
        raise NotImplementedError(
            f"Cancellation is not implemented for {request_id}"
        )

    def close(self) -> None:
        """Release runtime-owned resources during shutdown."""
