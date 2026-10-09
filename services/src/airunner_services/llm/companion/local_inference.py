"""Local inference client for companion turns and jobs (B12).

Implements the B01 ``CompanionInferenceClient`` protocol against the
existing ``RuntimeRegistry``: the companion reuses the already-loaded
Desktop LLM runtime instead of loading a model instance of its own.
This module never issues ``LOAD_MODEL``/``UNLOAD_MODEL`` — load and
unload priority across modalities stays with the daemon's shared
runtime owner; a companion call only *resolves* the client.

Every call passes the injected admission check first (the daemon
wires it to the shared resource coordinator). Exhausted resources
raise a retryable ``CompanionError`` so the caller requeues instead
of loading a duplicate model. Cancellation maps to the existing
``RuntimeClient.cancel`` path keyed by ``call_chain_id``.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.contracts import (
    ChatMessage,
    LLMInvocationRequest,
)
from airunner_services.runtimes.registry import RuntimeRegistry

from .contracts import (
    ERROR_INFERENCE_UNAVAILABLE,
    CancellationRequest,
    CompanionError,
    CompanionErrorCode,
    CompanionStreamEvent,
)
from .inference import CompanionInferenceRequest
from .local_routing import (
    AdmissionCheck,
    CompanionPipeline,
    allow_all_admission,
    check_admission,
    resolve_pipeline_client,
)
from .stream_events import adapt_delta, cancelled_event


class RegistryInferenceClient:
    """Route companion inference through the shared local runtime."""

    def __init__(
        self,
        registry: RuntimeRegistry,
        *,
        pipeline: CompanionPipeline = CompanionPipeline.DIALOGUE,
        admission: Optional[AdmissionCheck] = None,
        allow_remote: bool = False,
        remote_consent: bool = False,
        is_offline: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._registry = registry
        self._pipeline = pipeline
        self._admission = admission or allow_all_admission
        self._allow_remote = allow_remote
        self._remote_consent = remote_consent
        self._is_offline = is_offline
        self._cancelled: Set[str] = set()

    @property
    def pipeline(self) -> CompanionPipeline:
        """The pipeline this client resolves routes for."""
        return self._pipeline

    def invoke_text(
        self,
        messages: List[ChatMessage],
        *,
        call_chain_id: str = "companion-job",
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> str:
        """Run one non-streaming call; the job-Fn wiring primitive."""
        client = self._client()
        request = _invocation(
            messages, call_chain_id, max_tokens, temperature, False
        )
        return _response_text(_safe_invoke(self._pipeline, client, request))

    async def stream(
        self, request: CompanionInferenceRequest
    ) -> AsyncIterator[CompanionStreamEvent]:
        """Stream one turn, adapting runtime deltas to turn events."""
        client = self._client()
        invocation = _invocation(
            request.messages,
            str(request.call_chain_id),
            request.max_tokens,
            request.temperature,
            True,
        )
        deltas = _open_stream(self._pipeline, client, invocation)
        sequence = 0
        for delta in _read_deltas(self._pipeline, deltas):
            if str(request.call_chain_id) in self._cancelled:
                yield cancelled_event(request.call_chain_id, sequence)
                return
            yield adapt_delta(request.call_chain_id, delta)
            sequence += 1

    async def cancel(self, request: CancellationRequest) -> None:
        """Cancel one in-flight turn via the shared runtime client."""
        call_chain_id = str(request.call_chain_id)
        self._cancelled.add(call_chain_id)
        try:
            client = self._client()
        except CompanionError:
            return
        try:
            client.cancel(call_chain_id)
        except Exception:
            return

    def _client(self) -> RuntimeClient:
        """Admit, then resolve the shared client (never loads)."""
        check_admission(self._admission, self._pipeline)
        return resolve_pipeline_client(
            self._registry,
            self._pipeline,
            allow_remote=self._allow_remote,
            remote_consent=self._remote_consent,
            is_offline=self._is_offline,
        )


def job_text_fn(
    client: RegistryInferenceClient,
) -> Callable[[Any, List[ChatMessage]], str]:
    """Adapt one client to ``(JobContext, messages) -> text``.

    The daemon wraps this per pipeline and parses the text into each
    job's result model — parsing stays with each B07/B08/B09 ``*Fn``
    contract while every call routes through the shared runtime.
    """

    def _run(context: Any, messages: List[ChatMessage]) -> str:
        return client.invoke_text(messages, call_chain_id=str(context.job_id))

    return _run


def _invocation(
    messages: List[ChatMessage],
    call_chain_id: str,
    max_tokens: Optional[int],
    temperature: float,
    stream: bool,
) -> LLMInvocationRequest:
    """Build the runtime request for one companion call."""
    return LLMInvocationRequest(
        messages=list(messages),
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream,
        metadata={"call_chain_id": call_chain_id},
    )


def _safe_invoke(
    pipeline: CompanionPipeline,
    client: RuntimeClient,
    request: LLMInvocationRequest,
) -> Any:
    """Invoke once; failures become a retryable error, never a load."""
    try:
        return client.invoke(request)
    except CompanionError:
        raise
    except Exception as exc:
        raise _failed(pipeline, "inference failed") from exc


def _open_stream(
    pipeline: CompanionPipeline,
    client: RuntimeClient,
    request: LLMInvocationRequest,
) -> Any:
    """Open the runtime stream, or raise a retryable error."""
    try:
        return client.stream(request)
    except Exception as exc:
        raise _failed(pipeline, "stream failed to open") from exc


def _read_deltas(pipeline: CompanionPipeline, deltas: Any) -> Any:
    """Yield deltas; a mid-stream break is a retryable error."""
    try:
        yield from deltas
    except Exception as exc:
        raise _failed(pipeline, "stream broke mid-read") from exc


def _failed(pipeline: CompanionPipeline, what: str) -> CompanionError:
    """Build the retryable error for a failed local call."""
    return CompanionError(
        CompanionErrorCode(
            code=ERROR_INFERENCE_UNAVAILABLE,
            detail=f"'{pipeline.value}' local {what}; retry shortly",
            retryable=True,
        )
    )


def _response_text(response: Any) -> str:
    """Extract generated text from an invocation response."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return str(response.get("content", ""))
    return str(getattr(response, "content", ""))


__all__ = [
    "RegistryInferenceClient",
    "job_text_fn",
]
