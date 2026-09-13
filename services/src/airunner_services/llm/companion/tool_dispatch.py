"""Tool dispatch contract bridging companion turns to Desktop's tool
registry (B01).

An interface only — B11 implements this against Desktop's existing
``airunner_services.llm.core.tool_registry.ToolRegistry`` (the ``@tool``
decorator system already used by every other Desktop LLM tool). This
contract exists specifically so companion code never imports or defines
a second, parallel tool system: it calls ``CompanionToolDispatcher``,
and the B11 implementation is the only thing that touches
``ToolRegistry`` directly.

W01 §3 found the upstream tool-classification/selection modules
(``llm/managers/route_policy.py``, ``llm/managers/tool_selection_plan.py``)
but could not locate their actual dispatch implementation in that pass
— flagged there as a gap, not resolved here either. This contract does
not assume upstream's classification approach is reused; it only fixes
the shape a companion turn calls once *some* classifier (upstream-
derived or Desktop-native) has already chosen a tool and arguments.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from .contracts import ChatbotId


class ToolDispatchRequest(BaseModel):
    """One resolved tool call a companion turn wants executed."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    chatbot_id: ChatbotId


class ToolDispatchResult(BaseModel):
    """The outcome of one tool dispatch.

    ``content`` is the tool's return value serialized as a string,
    matching the existing Desktop tool-execution convention (registered
    tool functions already return ``str`` — see
    ``tool_registry.py``'s own ``generate_image`` example).
    """

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    content: str
    succeeded: bool = True
    error_code: Optional[str] = None


@runtime_checkable
class CompanionToolDispatcher(Protocol):
    """Executes one already-selected tool call for a companion turn."""

    def available_tools(self, chatbot_id: ChatbotId) -> List[str]:
        """Return tool names available to this chatbot right now.

        Implementations filter Desktop's full ``ToolRegistry`` (e.g. by
        ``ToolCategory``, `requires_api`, or a companion-specific
        allow/deny list) — the upstream precedent for hard-disabling
        categories entirely (W01 §2: UwUchat disables `conversation`
        and `image` at the pipeline-config level, not merely leaving
        them unselected) is worth following here for any category that
        genuinely does not apply to a companion turn, rather than
        relying on a classifier to simply never pick it.
        """
        ...

    def dispatch(self, request: ToolDispatchRequest) -> ToolDispatchResult:
        """Execute one tool call and return its result.

        Must not raise for an ordinary tool-execution failure (a bad
        argument, a tool-internal error) — return
        ``ToolDispatchResult(succeeded=False, error_code=...)`` instead,
        so a companion turn can narrate the failure in character rather
        than aborting the whole turn. Only truly unexpected conditions
        (e.g. `tool_name` not found in the registry at all) should
        raise ``CompanionError``.
        """
        ...


__all__ = [
    "CompanionToolDispatcher",
    "ToolDispatchRequest",
    "ToolDispatchResult",
]
