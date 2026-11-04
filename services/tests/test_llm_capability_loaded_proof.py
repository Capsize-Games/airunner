"""READY-plus-metadata loaded proof for local capability.

READY health alone proves the runtime answers, not which model
it serves: with no served-model metadata nothing is loaded. A
``model_path`` naming a known GGUF file is equally strong
metadata. Hermetic: canned health only, no model or network.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from airunner_services.llm.local_capability import (
    build_local_capability,
    proven_loaded_model_id,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
    RuntimeRoute,
)


class _FakeRuntimeClient(RuntimeClient):
    """Local runtime with canned READY health; no inference."""

    def __init__(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=DEFAULT_PROVIDER,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
            supports_streaming=True,
        )
        self._metadata = metadata or {}

    def invoke(self, request: Any) -> Any:
        del request
        raise AssertionError("capability must not invoke inference")

    def stream(self, request: Any) -> Iterable[Any]:
        del request
        raise AssertionError("capability must not stream inference")

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY,
            metadata=self._metadata,
        )


def _registry_with(client: RuntimeClient) -> RuntimeRegistry:
    registry = RuntimeRegistry()
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=DEFAULT_PROVIDER), client
    )
    return registry


def test_ready_without_metadata_does_not_claim_configured() -> None:
    """READY alone proves the runtime, not the served model."""
    payload = build_local_capability(
        registry=_registry_with(_FakeRuntimeClient()),
        configured_model_id="gpt-oss-20b",
    )
    assert payload["runtime"]["status"] == "ready"
    entry = next(m for m in payload["models"] if m["id"] == "gpt-oss-20b")
    assert entry["configured"] is True
    assert entry["loaded"] is False
    assert not any(m["loaded"] for m in payload["models"])


def test_ready_model_path_metadata_proves_served_model() -> None:
    """A served GGUF path in metadata resolves to its model id."""
    serving = _FakeRuntimeClient(
        metadata={"model_path": "/models/Qwen/Qwen3.5-9B-Q8_0.gguf"}
    )
    payload = build_local_capability(
        registry=_registry_with(serving),
        configured_model_id="gpt-oss-20b",
    )
    loaded = [m["id"] for m in payload["models"] if m["loaded"]]
    assert loaded == ["qwen3.5-9b"]


def test_ready_unresolvable_metadata_does_not_claim_loaded() -> None:
    """Metadata naming no known model proves no load."""
    serving = _FakeRuntimeClient(metadata={"model_id": "unknown-x"})
    payload = build_local_capability(
        registry=_registry_with(serving),
        configured_model_id="gpt-oss-20b",
    )
    assert payload["runtime"]["status"] == "ready"
    assert not any(m["loaded"] for m in payload["models"])


def test_proven_loaded_id_ignores_configured_argument() -> None:
    """The shared helper never uses configuration as proof."""
    registry = _registry_with(_FakeRuntimeClient())
    assert proven_loaded_model_id(registry, "gpt-oss-20b") == ""
    serving = _FakeRuntimeClient(metadata={"model_id": "gpt-oss-20b"})
    registry = _registry_with(serving)
    assert proven_loaded_model_id(registry, "qwen3.5-9b") == "gpt-oss-20b"
