"""Typed contracts for the Desktop companion port (release issue B01).

These are interfaces only: stable ID types, one request/response/stream
shape for a companion turn, cancellation, errors, and a context budget.
No business logic lives here — B02-B16 implement against this module,
not the other way around.

Deliberately reuses the Desktop daemon's existing conventions instead of
inventing parallel ones:

- ``ChatMessage``/``MessageRole``/``LLMInvocationRequest`` from
  ``airunner_services.runtimes.contracts`` (the existing LLM runtime
  contract) for the actual model call shape.
- ``EnvelopeStatus`` from ``airunner_services.ipc.messages`` (the
  existing streaming-status vocabulary already used by
  ``StreamDelta``/art and LLM generation routes) for turn/stream status,
  so a companion turn's terminal states line up with every other
  streamed operation in this codebase.

Import boundary (verified by ``services/tests/test_release_b01.py``):
this module and its siblings in this package must import cleanly with
no Qt, no torch, no web ``airunner_services`` package, and no
Postgres/Redis driver on the path — a companion turn is orchestration,
not inference; the actual model call is delegated through
``inference.py`` to the existing runtime registry.
"""

from __future__ import annotations

from typing import Any, Dict, List, NewType, Optional

from pydantic import BaseModel, ConfigDict, Field

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.runtimes.contracts import ChatMessage

# ---------------------------------------------------------------------------
# Stable IDs
# ---------------------------------------------------------------------------
# Integer, matching the upstream UwUchat schema shape frozen in W01
# (ConversationTurn/ChatSession primary keys) rather than inventing a new
# ID scheme the Desktop SQLite schema (B02) would then have to translate.
ChatbotId = NewType("ChatbotId", int)
SessionId = NewType("SessionId", int)
TurnId = NewType("TurnId", int)

# A per-request trace ID threaded through one turn's LLM call, background
# jobs, and logs, matching the upstream ``call_chain_id`` field on
# ConversationTurn (W01 §3) — a string, not an int, since it is generated
# client/request-side (e.g. a UUID) rather than assigned by a DB sequence.
CallChainId = NewType("CallChainId", str)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class CompanionErrorCode(BaseModel):
    """A closed, deterministic error code — never a raw exception message.

    Mirrors the release-wide pattern already established for the LLM
    WebSocket (release S02: ``rate_limited``, ``invalid_request``, ...):
    callers key behavior off ``code``, and ``detail`` is safe to show a
    user but must never embed prompt/turn content.
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    detail: str = ""
    retryable: bool = False


class CompanionError(Exception):
    """Raised by any companion component for a caller-visible failure."""

    def __init__(self, error: CompanionErrorCode) -> None:
        self.error = error
        super().__init__(error.code)


# Known, stable codes. Additive only — do not repurpose an existing code
# for a new meaning once B02+ ships against it.
ERROR_UNKNOWN_CHATBOT = "unknown_chatbot"
ERROR_SESSION_EXPIRED = "session_expired"
ERROR_CONTEXT_BUDGET_EXCEEDED = "context_budget_exceeded"
ERROR_TOOL_DISPATCH_FAILED = "tool_dispatch_failed"
ERROR_INFERENCE_UNAVAILABLE = "inference_unavailable"
ERROR_CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Context budget
# ---------------------------------------------------------------------------
class ContextBudget(BaseModel):
    """Bounds on how much context/work one companion turn may consume.

    A companion turn composes recent turns, facts, and a narrative
    summary into one prompt (B10); this is the shared cap all of those
    sources are trimmed against, and the ceiling on how many background
    jobs (B06) or tool calls (B11) one turn may fan out to.
    """

    model_config = ConfigDict(extra="forbid")

    max_prompt_tokens: int = 4096
    max_output_tokens: int = 1024
    max_recent_turns: int = 20
    max_facts: int = 20
    max_tool_calls: int = 3


# ---------------------------------------------------------------------------
# One companion turn
# ---------------------------------------------------------------------------
class CompanionTurnRequest(BaseModel):
    """One inbound request to advance a chatbot's conversation by a turn."""

    model_config = ConfigDict(extra="forbid")

    chatbot_id: ChatbotId
    session_id: Optional[SessionId] = None
    call_chain_id: CallChainId
    message: str
    context_budget: ContextBudget = Field(default_factory=ContextBudget)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompanionStreamEvent(BaseModel):
    """One streamed unit of a companion turn's response.

    Shaped like ``airunner_services.ipc.messages.StreamDelta`` (the
    existing LLM-stream contract) rather than a new envelope, so a
    companion turn can be relayed over the same
    ``/api/v1/llm/stream``-style WebSocket surface without a second
    parallel wire format (see release S01/S02 for that endpoint's
    existing auth/rate-limit contract, which a companion route would
    reuse rather than reimplement).
    """

    model_config = ConfigDict(extra="forbid")

    call_chain_id: CallChainId
    sequence: int = 0
    delta_text: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    final: bool = False
    status: EnvelopeStatus = EnvelopeStatus.STREAM
    error: Optional[CompanionErrorCode] = None


class CompanionTurnResult(BaseModel):
    """The completed, non-streaming result of one companion turn."""

    model_config = ConfigDict(extra="forbid")

    call_chain_id: CallChainId
    turn_id: Optional[TurnId] = None
    session_id: Optional[SessionId] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    content: str = ""
    status: EnvelopeStatus = EnvelopeStatus.SUCCEEDED
    error: Optional[CompanionErrorCode] = None


class CancellationRequest(BaseModel):
    """Requests cancellation of one in-flight companion turn.

    Deliberately mirrors ``RuntimeAction.CANCEL``
    (``airunner_services.runtimes.contracts``): cancelling a companion
    turn cancels its underlying inference call the same way any other
    runtime invocation is cancelled today, rather than a second
    cancellation mechanism.
    """

    model_config = ConfigDict(extra="forbid")

    call_chain_id: CallChainId


__all__ = [
    "CallChainId",
    "CancellationRequest",
    "ChatbotId",
    "CompanionError",
    "CompanionErrorCode",
    "CompanionStreamEvent",
    "CompanionTurnRequest",
    "CompanionTurnResult",
    "ContextBudget",
    "ERROR_CANCELLED",
    "ERROR_CONTEXT_BUDGET_EXCEEDED",
    "ERROR_INFERENCE_UNAVAILABLE",
    "ERROR_SESSION_EXPIRED",
    "ERROR_TOOL_DISPATCH_FAILED",
    "ERROR_UNKNOWN_CHATBOT",
    "SessionId",
    "TurnId",
]
