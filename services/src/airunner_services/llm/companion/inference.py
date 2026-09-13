"""Inference contract for companion turns (B01).

An interface only. Deliberately thin: a companion turn does not get its
own model-invocation mechanism. It composes a prompt (B10: prompt
composition and mood context) and calls this contract, whose
implementation (B12) resolves and invokes the *existing* Desktop LLM
runtime via ``airunner_services.runtimes.registry.RuntimeRegistry`` and
``airunner_services.runtimes.contracts.LLMInvocationRequest`` — the same
runtime path ``/api/v1/llm/stream`` and ``/api/v1/llm/generate`` already
use, per the parent spec's "reuse existing Desktop inference" and B12's
"route every companion pipeline through local inference by default."

Nothing here talks to a cloud provider. W01 §2 confirms upstream is
cloud-only for every pipeline stage today (OpenRouter); B12 exists
specifically to invert that default for the Desktop port, so this
contract's implementation must not default to a remote provider even
though the interface itself does not forbid one being configured
explicitly (the parent spec: "Explicit remote mode and optional online
providers retain clear consent and authentication" — that consent/
routing decision lives in B12's implementation, not this file).
"""

from __future__ import annotations

from typing import AsyncIterator, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from airunner_services.runtimes.contracts import ChatMessage

from .contracts import CallChainId, CompanionStreamEvent


class CompanionInferenceRequest(BaseModel):
    """One resolved prompt ready for the LLM runtime.

    ``messages`` is already fully composed (system prompt, mood
    context, recent turns, facts — all B10's job) by the time it
    reaches this contract; this file has no opinion on how a prompt is
    assembled, only on how it is invoked.
    """

    model_config = ConfigDict(extra="forbid")

    call_chain_id: CallChainId
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: float = 0.7


@runtime_checkable
class CompanionInferenceClient(Protocol):
    """Invokes the Desktop LLM runtime on behalf of a companion turn."""

    async def stream(
        self, request: CompanionInferenceRequest
    ) -> AsyncIterator[CompanionStreamEvent]:
        """Stream one companion turn's response.

        An implementation adapts the existing
        ``airunner_services.ipc.messages.StreamDelta`` sequence (the
        same one ``stream_runtime()`` in
        ``api/routes/llm_runtime.py`` already yields) into
        ``CompanionStreamEvent`` — B12's job, not redefined here.
        """
        ...
        yield  # pragma: no cover - Protocol stub, never executed


__all__ = [
    "CompanionInferenceClient",
    "CompanionInferenceRequest",
]
