"""Tests for runtime registry lookup behavior."""

from airunner.ipc.messages import (
    EnvelopeStatus,
    RequestEnvelope,
    ResponseEnvelope,
)
from airunner.runtimes.base import RuntimeClient
from airunner.runtimes.contracts import (
    RuntimeDescriptor,
    RuntimeHealth,
    RuntimeHealthStatus,
    RuntimeKind,
    RuntimeMode,
    TransportKind,
)
from airunner.runtimes.registry import RuntimeRegistry, RuntimeRoute


class DummyClient(RuntimeClient):
    """Simple runtime client used by registry tests."""

    def __init__(self, provider: str):
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=provider,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        )

    def invoke(self, request: RequestEnvelope) -> ResponseEnvelope:
        return ResponseEnvelope(
            request_id=request.request_id,
            status=EnvelopeStatus.SUCCEEDED,
        )

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY,
        )


class TestRuntimeRegistry:
    """Tests for runtime registry resolution rules."""

    def test_resolves_exact_route(self):
        registry = RuntimeRegistry()
        client = DummyClient(provider="local")

        registry.register(
            RuntimeRoute(RuntimeKind.LLM, provider="local"),
            client,
        )

        resolved = registry.resolve(RuntimeKind.LLM, provider="local")

        assert resolved is client

    def test_resolves_default_provider_fallback(self):
        registry = RuntimeRegistry()
        fallback = DummyClient(provider="default")

        registry.register(RuntimeRoute(RuntimeKind.STT), fallback)

        resolved = registry.resolve(RuntimeKind.STT, provider="native")

        assert resolved is fallback

    def test_raises_for_unknown_route(self):
        registry = RuntimeRegistry()

        try:
            registry.resolve(RuntimeKind.TTS, provider="local")
        except KeyError as exc:
            assert "tts/local/default" in str(exc)
        else:
            raise AssertionError("Expected KeyError for missing route")