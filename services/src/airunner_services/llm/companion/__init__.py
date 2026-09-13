"""Desktop companion contracts (release issue B01).

This package defines interfaces only, ported and mapped from the frozen
UwUchat behavior inventory (W01:
https://github.com/Capsize-Games/airunnerweb/blob/8157628a.../wiki/Desktop-Bot-Port-Reference.md).
See ``release-planning/linux-v1/companion-contracts.md`` for the full
capability-to-issue mapping and the worked example trace this issue's
acceptance criteria require.

B02+ implementations (e.g. ``repository.py``'s ``SqlCompanionMemoryRepository``,
release issue B02) live as submodules of this package per each ticket's
read/change boundary, but are deliberately **not** re-exported here:
this package's own import (``import airunner_services.llm.companion``)
must stay free of Qt/torch/SQL-driver imports (see
``services/tests/test_release_b01.py``), which a concrete,
database-backed implementation cannot be. Import a submodule directly
(``from airunner_services.llm.companion.repository import
SqlCompanionMemoryRepository``) to use one.
"""

from __future__ import annotations

from .contracts import (
    ERROR_CANCELLED,
    ERROR_CONTEXT_BUDGET_EXCEEDED,
    ERROR_INFERENCE_UNAVAILABLE,
    ERROR_SESSION_EXPIRED,
    ERROR_TOOL_DISPATCH_FAILED,
    ERROR_UNKNOWN_CHATBOT,
    CallChainId,
    CancellationRequest,
    ChatbotId,
    CompanionError,
    CompanionErrorCode,
    CompanionStreamEvent,
    CompanionTurnRequest,
    CompanionTurnResult,
    ContextBudget,
    SessionId,
    TurnId,
)
from .inference import CompanionInferenceClient, CompanionInferenceRequest
from .memory_repository import (
    CompanionMemoryRepository,
    FactRecord,
    SessionRecord,
    TurnRecord,
)
from .scheduler import (
    CompanionJobHandle,
    CompanionJobRequest,
    CompanionJobType,
    CompanionScheduler,
)
from .tool_dispatch import (
    CompanionToolDispatcher,
    ToolDispatchRequest,
    ToolDispatchResult,
)

__all__ = [
    "ERROR_CANCELLED",
    "ERROR_CONTEXT_BUDGET_EXCEEDED",
    "ERROR_INFERENCE_UNAVAILABLE",
    "ERROR_SESSION_EXPIRED",
    "ERROR_TOOL_DISPATCH_FAILED",
    "ERROR_UNKNOWN_CHATBOT",
    "CallChainId",
    "CancellationRequest",
    "ChatbotId",
    "CompanionError",
    "CompanionErrorCode",
    "CompanionInferenceClient",
    "CompanionInferenceRequest",
    "CompanionJobHandle",
    "CompanionJobRequest",
    "CompanionJobType",
    "CompanionMemoryRepository",
    "CompanionScheduler",
    "CompanionStreamEvent",
    "CompanionToolDispatcher",
    "CompanionTurnRequest",
    "CompanionTurnResult",
    "ContextBudget",
    "FactRecord",
    "SessionId",
    "SessionRecord",
    "ToolDispatchRequest",
    "ToolDispatchResult",
    "TurnId",
    "TurnRecord",
]
