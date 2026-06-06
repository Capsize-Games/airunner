"""Base interfaces for runtime clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable

from airunner_services.runtimes.contracts import RuntimeDescriptor
from airunner_services.runtimes.contracts import RuntimeHealth


class RuntimeClient(ABC):
    """Interface implemented by daemon-facing runtime clients."""

    descriptor: RuntimeDescriptor

    @abstractmethod
    def invoke(self, request: Any) -> Any:
        """Execute a non-streaming request."""

    def stream(self, request: Any) -> Iterable[Any]:
        """Stream request output when the runtime supports it."""
        raise NotImplementedError("Streaming is not implemented")

    @abstractmethod
    def healthcheck(self) -> RuntimeHealth:
        """Return runtime health information."""

    def cancel(self, request_id: str) -> Any:
        """Cancel a previously submitted request when supported."""
        raise NotImplementedError(
            f"Cancellation is not implemented for {request_id}"
        )

    def close(self) -> None:
        """Release runtime-owned resources during shutdown."""


__all__ = ["RuntimeClient"]
