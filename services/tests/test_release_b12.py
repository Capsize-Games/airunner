"""Regression tests for release issue B12 (#2141).

Proves every companion pipeline routes through shared local
inference by default:

- The routing matrix covers every W01 pipeline; all LLM pipelines
  resolve to the one registered local client (no duplicate models).
- Explicit OpenRouter needs opt-in consent and is denied offline;
  offline local calls make zero external requests.
- Missing/denied local inference raises an actionable retryable
  error and never silently becomes a cloud call.
- Cancellation maps to the runtime cancel path and stops the
  stream with a terminal event; exhausted admission raises before
  touching the runtime.

Uses real data contracts with a fake registry/runtime boundary —
no model, network, GPU, database, or GUI access.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

from airunner_services.ipc.messages import EnvelopeStatus, StreamDelta
from airunner_services.llm.companion.contracts import (
    ERROR_CANCELLED,
    ERROR_INFERENCE_UNAVAILABLE,
    CallChainId,
    CancellationRequest,
    CompanionError,
)
from airunner_services.llm.companion.inference import (
    CompanionInferenceClient,
    CompanionInferenceRequest,
)
from airunner_services.llm.companion.local_inference import (
    RegistryInferenceClient,
    job_text_fn,
)
from airunner_services.llm.companion.local_routing import (
    REMOTE_PROVIDER_OPENROUTER,
    CompanionPipeline,
    PIPELINE_ROUTES,
    allow_all_admission,
    deny_all_admission,
    resolve_pipeline_client,
)
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ChatMessage,
    LLMInvocationResponse,
    MessageRole,
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
    """Count every call; never touches a model or the network."""

    def __init__(self, provider: str, deltas: Optional[list] = None) -> None:
        self.descriptor = RuntimeDescriptor(
            runtime=RuntimeKind.LLM,
            provider=provider,
            mode=RuntimeMode.LOCAL_FALLBACK,
            transport=TransportKind.IN_PROCESS,
        )
        self.invoked: List[Any] = []
        self.streamed: List[Any] = []
        self.cancelled: List[str] = []
        self._deltas = list(deltas or [])

    def invoke(self, request: Any) -> Any:
        self.invoked.append(request)
        return LLMInvocationResponse(content="local reply")

    def stream(self, request: Any) -> Iterable[Any]:
        self.streamed.append(request)
        return list(self._deltas)

    def healthcheck(self) -> RuntimeHealth:
        return RuntimeHealth(
            descriptor=self.descriptor,
            status=RuntimeHealthStatus.READY,
        )

    def cancel(self, request_id: str) -> Any:
        self.cancelled.append(request_id)
        return None


def _registry_with_local(deltas: Optional[list] = None) -> Any:
    """Return (registry, local) with only the local route registered."""
    registry = RuntimeRegistry()
    local = _FakeRuntimeClient(DEFAULT_PROVIDER, deltas)
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=DEFAULT_PROVIDER), local
    )
    return SimpleNamespace(registry=registry, local=local)


def _messages() -> List[ChatMessage]:
    """Return one minimal composed prompt."""
    return [ChatMessage(role=MessageRole.USER, content="hello")]


def _collect(client: RegistryInferenceClient, call: str) -> list:
    """Stream one turn to completion and return its events."""

    async def _run() -> list:
        request = CompanionInferenceRequest(
            call_chain_id=CallChainId(call), messages=_messages()
        )
        return [event async for event in client.stream(request)]

    return asyncio.run(_run())


def _delta(text: str, sequence: int, final: bool = False) -> StreamDelta:
    """Return one local-fallback-shaped stream delta."""
    return StreamDelta(
        request_id="r1",
        sequence=sequence,
        delta={"content": text},
        final=final,
    )


def test_routing_matrix_covers_every_pipeline() -> None:
    """Every W01 pipeline has a local-first route; embeddings stay out
    of the LLM registry by design (B04 identity-bound local index)."""
    assert set(PIPELINE_ROUTES) == set(CompanionPipeline)
    env = _registry_with_local()
    for pipeline in CompanionPipeline:
        if pipeline == CompanionPipeline.EMBEDDING:
            try:
                resolve_pipeline_client(env.registry, pipeline)
            except CompanionError as exc:
                assert exc.error.code == ERROR_INFERENCE_UNAVAILABLE
                assert "EmbeddingClient" in exc.error.detail
            else:
                raise AssertionError("embedding must not resolve via LLM")
        else:
            assert resolve_pipeline_client(env.registry, pipeline) is env.local


def test_default_resolution_shares_one_local_client() -> None:
    """Two pipelines share the registered instance; a registered
    remote is never touched without explicit consent."""
    env = _registry_with_local()
    remote = _FakeRuntimeClient(REMOTE_PROVIDER_OPENROUTER)
    env.registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=REMOTE_PROVIDER_OPENROUTER),
        remote,
    )
    first = resolve_pipeline_client(env.registry, CompanionPipeline.DIALOGUE)
    second = resolve_pipeline_client(
        env.registry, CompanionPipeline.FACT_EXTRACTION
    )
    assert first is second is env.local
    assert remote.invoked == [] and remote.streamed == []


def test_explicit_remote_consent_routes_to_openrouter() -> None:
    """Opt-in consent selects the remote provider when online."""
    env = _registry_with_local()
    remote = _FakeRuntimeClient(REMOTE_PROVIDER_OPENROUTER)
    env.registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=REMOTE_PROVIDER_OPENROUTER),
        remote,
    )
    resolved = resolve_pipeline_client(
        env.registry,
        CompanionPipeline.DIALOGUE,
        allow_remote=True,
        remote_consent=True,
        is_offline=lambda: False,
    )
    assert resolved is remote


def test_offline_denies_remote_but_keeps_local() -> None:
    """Offline consent raises with zero remote calls; local works."""
    env = _registry_with_local()
    remote = _FakeRuntimeClient(REMOTE_PROVIDER_OPENROUTER)
    env.registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=REMOTE_PROVIDER_OPENROUTER),
        remote,
    )
    try:
        resolve_pipeline_client(
            env.registry,
            CompanionPipeline.DIALOGUE,
            allow_remote=True,
            remote_consent=True,
            is_offline=lambda: True,
        )
    except CompanionError as exc:
        assert exc.error.code == ERROR_INFERENCE_UNAVAILABLE
        assert "offline" in exc.error.detail
    else:
        raise AssertionError("offline must deny remote inference")
    assert remote.invoked == [] and remote.streamed == []
    assert (
        resolve_pipeline_client(
            env.registry, CompanionPipeline.DIALOGUE, is_offline=lambda: True
        )
        is env.local
    )


def test_missing_local_runtime_never_becomes_cloud() -> None:
    """No local route raises retryable; the cloud client stays idle."""
    registry = RuntimeRegistry()
    remote = _FakeRuntimeClient(REMOTE_PROVIDER_OPENROUTER)
    registry.register(
        RuntimeRoute(RuntimeKind.LLM, provider=REMOTE_PROVIDER_OPENROUTER),
        remote,
    )
    try:
        resolve_pipeline_client(registry, CompanionPipeline.MOOD_UPDATE)
    except CompanionError as exc:
        assert exc.error.code == ERROR_INFERENCE_UNAVAILABLE
        assert exc.error.retryable is True
        assert "mood_update" in exc.error.detail
    else:
        raise AssertionError("missing local runtime must raise")
    assert remote.invoked == [] and remote.streamed == []


def test_client_satisfies_the_inference_protocol() -> None:
    """The registry client is a B01 CompanionInferenceClient."""
    env = _registry_with_local()
    assert isinstance(
        RegistryInferenceClient(env.registry), CompanionInferenceClient
    )


def test_stream_adapts_runtime_deltas() -> None:
    """Content, tool calls, and final all survive adaptation."""
    deltas = [
        _delta("Hel", 0),
        StreamDelta(
            request_id="r1",
            sequence=1,
            delta={"content": "lo", "tool_calls": [{"name": "t"}]},
            final=True,
        ),
    ]
    env = _registry_with_local(deltas)
    events = _collect(RegistryInferenceClient(env.registry), "chain-1")
    assert [e.delta_text for e in events] == ["Hel", "lo"]
    assert events[1].tool_calls == [{"name": "t"}]
    assert events[-1].final is True
    assert len(env.local.streamed) == 1
    assert env.local.streamed[0].stream is True


def test_failed_delta_becomes_a_terminal_error_event() -> None:
    """A FAILED runtime delta ends the turn actionably, not silently."""
    env = _registry_with_local(
        [
            StreamDelta(
                request_id="r1",
                sequence=0,
                final=True,
                status=EnvelopeStatus.FAILED,
            )
        ]
    )
    events = _collect(RegistryInferenceClient(env.registry), "chain-2")
    assert len(events) == 1
    assert events[0].final is True
    assert events[0].status == EnvelopeStatus.FAILED
    assert events[0].error is not None
    assert events[0].error.code == ERROR_INFERENCE_UNAVAILABLE
    assert events[0].error.retryable is True


def test_cancel_maps_to_runtime_cancel_and_stops_stream() -> None:
    """Cancel reaches the runtime keyed by call chain; a cancelled
    stream yields one terminal CANCELLED event and reads no deltas."""
    env = _registry_with_local([_delta("x", 0), _delta("y", 1, True)])
    client = RegistryInferenceClient(env.registry)
    asyncio.run(
        client.cancel(CancellationRequest(call_chain_id=CallChainId("c9")))
    )
    assert env.local.cancelled == ["c9"]
    events = _collect(client, "c9")
    assert len(events) == 1
    assert events[0].final is True
    assert events[0].status == EnvelopeStatus.CANCELLED
    assert events[0].error is not None
    assert events[0].error.code == ERROR_CANCELLED


def test_exhausted_admission_raises_before_touching_runtime() -> None:
    """No admission means a retryable error and zero runtime calls —
    never a second model load."""
    env = _registry_with_local([_delta("x", 0, True)])
    client = RegistryInferenceClient(
        env.registry,
        pipeline=CompanionPipeline.EPISODIC_SUMMARY,
        admission=deny_all_admission("vram exhausted; art owns the gpu"),
    )
    for call in (
        lambda: client.invoke_text(_messages()),
        lambda: _collect(client, "chain-3"),
    ):
        try:
            call()
        except CompanionError as exc:
            assert exc.error.code == ERROR_INFERENCE_UNAVAILABLE
            assert exc.error.retryable is True
            assert "vram exhausted" in exc.error.detail
        else:
            raise AssertionError("exhausted admission must raise")
    assert env.local.invoked == [] and env.local.streamed == []


def test_job_text_fn_routes_background_pipelines_through_local() -> None:
    """Extraction, summaries, blend, mood, and curiosity all invoke
    the shared local client with the job id as the call chain."""
    env = _registry_with_local()
    pipelines = [
        CompanionPipeline.FACT_EXTRACTION,
        CompanionPipeline.EPISODIC_SUMMARY,
        CompanionPipeline.ROLLING_COMPRESSION,
        CompanionPipeline.MEMORY_BLEND,
        CompanionPipeline.MOOD_UPDATE,
        CompanionPipeline.CURIOSITY,
    ]
    for index, pipeline in enumerate(pipelines):
        client = RegistryInferenceClient(
            env.registry, pipeline=pipeline, admission=allow_all_admission
        )
        text = job_text_fn(client)(
            SimpleNamespace(job_id=f"job-{index}"), _messages()
        )
        assert text == "local reply"
    assert len(env.local.invoked) == len(pipelines)
    assert env.local.invoked[0].metadata["call_chain_id"] == "job-0"


def test_unregistered_remote_consent_names_the_provider() -> None:
    """Consent without a registered remote is an explicit config
    error, not a silent local substitution or a crash."""
    env = _registry_with_local()
    try:
        resolve_pipeline_client(
            env.registry,
            CompanionPipeline.DIALOGUE,
            allow_remote=True,
            remote_consent=True,
            is_offline=lambda: False,
        )
    except CompanionError as exc:
        assert exc.error.code == ERROR_INFERENCE_UNAVAILABLE
        assert REMOTE_PROVIDER_OPENROUTER in exc.error.detail
    else:
        raise AssertionError("unregistered remote must raise")
