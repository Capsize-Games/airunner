"""Companion tool routing over Desktop's registered tools (B11).

Implements the B01 ``CompanionToolDispatcher`` protocol against the
existing ``ToolRegistry`` (``airunner_services.llm.core.tool_registry``)
— the same ``@tool`` decorator system every other Desktop LLM tool
uses. This module creates no parallel tool runtime: selection input
arrives as ``ToolDispatchRequest`` values and execution always goes
through a registered tool function.

Arguments are validated against the registered signature before the
call; network-requiring tools cannot execute while offline mode
(O01/O02) is on while local tools stay available; tools needing an
agent instance are excluded as a capability mismatch. See
``tool_loop.py`` for bounded multi-round execution over this
dispatcher.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Protocol

from .contracts import (
    ERROR_TOOL_DISPATCH_FAILED,
    ChatbotId,
    CompanionError,
    CompanionErrorCode,
)
from .tool_arguments import (
    merge_chatbot_id,
    serialize_result,
    validate_arguments,
)
from .tool_dispatch import ToolDispatchRequest, ToolDispatchResult

logger = logging.getLogger(__name__)

ERROR_INVALID_ARGUMENTS = "invalid_arguments"
ERROR_TOOL_FAILED = "tool_failed"
ERROR_OFFLINE_BLOCKED = "offline_blocked"
ERROR_CAPABILITY_UNAVAILABLE = "capability_unavailable"
ERROR_PUBLICATION_DENIED = "publication_denied"

# Registered Desktop tools needing external network egress. Name
# based, not category based: local RAG helpers share RESEARCH with
# the crawler, so a category rule would mislabel them (see #2140).
NETWORK_TOOL_NAMES = frozenset(
    {
        "search_web",
        "search_news",
        "scrape_website",
        "intelligent_crawl",
    }
)


class RegisteredTool(Protocol):
    """Structural shape of one ``ToolRegistry`` entry we execute."""

    name: str
    func: Callable[..., Any]
    requires_agent: bool


ToolLookup = Callable[[str], Optional[RegisteredTool]]
ToolLister = Callable[[], Dict[str, RegisteredTool]]


def _default_lookup(name: str) -> Optional[RegisteredTool]:
    """Return one Desktop-registered tool by name (lazy import)."""
    from airunner_services.llm.core.tool_registry import ToolRegistry

    return ToolRegistry.get(name)


def _default_lister() -> Dict[str, RegisteredTool]:
    """Return all Desktop-registered tools (lazy import)."""
    from airunner_services.llm.core.tool_registry import ToolRegistry

    return ToolRegistry.all()


def _default_is_offline() -> bool:
    """Return the O01 offline-mode flag (lazy import)."""
    from airunner_services.url_safety import is_offline_mode

    return is_offline_mode()


def default_publication_allowed(text: str) -> bool:
    """Return the S12 publication verdict for tool content."""
    from airunner_services.content_safety_gate import (
        evaluate_publication_fields,
    )

    return bool(evaluate_publication_fields({"tool_output": text}).allowed)


def failed_dispatch(
    tool_name: str, code: str, content: str
) -> ToolDispatchResult:
    """Build a failed dispatch result with generic, safe content."""
    return ToolDispatchResult(
        tool_name=tool_name,
        content=content,
        succeeded=False,
        error_code=code,
    )


class DesktopToolDispatcher:
    """Route companion tool calls to Desktop-registered tools."""

    def __init__(
        self,
        *,
        lookup: Optional[ToolLookup] = None,
        lister: Optional[ToolLister] = None,
        is_offline: Optional[Callable[[], bool]] = None,
        publication_allowed: Optional[Callable[[str], bool]] = None,
        extra_network_tools: frozenset[str] = frozenset(),
    ) -> None:
        self._lookup = lookup or _default_lookup
        self._lister = lister or _default_lister
        self._is_offline = is_offline or _default_is_offline
        self._publication_allowed = (
            publication_allowed or default_publication_allowed
        )
        self._extra_network_tools = extra_network_tools

    def available_tools(self, chatbot_id: ChatbotId) -> List[str]:
        """Return registered tool names usable by a companion turn."""
        del chatbot_id
        offline = self._is_offline()
        names = [
            name
            for name, entry in self._lister().items()
            if not getattr(entry, "requires_agent", False)
            and not (offline and self._requires_network(name))
        ]
        return sorted(names)

    def dispatch(self, request: ToolDispatchRequest) -> ToolDispatchResult:
        """Execute one selected tool call against the registry."""
        entry = self._resolve_entry(request.tool_name)
        blocked = self._preflight(request.tool_name, entry)
        if blocked is not None:
            return blocked
        return self._invoke(request, entry)

    def _invoke(
        self, request: ToolDispatchRequest, entry: RegisteredTool
    ) -> ToolDispatchResult:
        """Validate arguments, call the tool, serialize its result."""
        merged = merge_chatbot_id(
            entry.func, request.arguments, request.chatbot_id
        )
        if not validate_arguments(entry.func, merged):
            return failed_dispatch(
                request.tool_name,
                ERROR_INVALID_ARGUMENTS,
                "invalid tool arguments",
            )
        return self._execute(request.tool_name, entry.func, merged)

    def _execute(
        self,
        tool_name: str,
        func: Callable[..., Any],
        merged: Dict[str, Any],
    ) -> ToolDispatchResult:
        """Call one validated tool and serialize its result."""
        try:
            raw = func(**merged)
        except Exception:
            logger.debug("companion tool failed", exc_info=True)
            return failed_dispatch(tool_name, ERROR_TOOL_FAILED, "tool failed")
        return ToolDispatchResult(
            tool_name=tool_name,
            content=serialize_result(raw),
            succeeded=True,
        )

    def _resolve_entry(self, tool_name: str) -> RegisteredTool:
        """Return the registry entry, raising for an unknown tool."""
        entry = self._lookup(tool_name)
        if entry is None:
            raise CompanionError(
                CompanionErrorCode(
                    code=ERROR_TOOL_DISPATCH_FAILED,
                    detail=f"unknown tool '{tool_name}'",
                )
            )
        return entry

    def _preflight(
        self, tool_name: str, entry: RegisteredTool
    ) -> Optional[ToolDispatchResult]:
        """Return a policy failure, or None when dispatch may run."""
        if getattr(entry, "requires_agent", False):
            return failed_dispatch(
                tool_name,
                ERROR_CAPABILITY_UNAVAILABLE,
                "tool unavailable to companion turns",
            )
        if self._requires_network(tool_name) and self._is_offline():
            return failed_dispatch(
                tool_name,
                ERROR_OFFLINE_BLOCKED,
                f"'{tool_name}' needs a network connection "
                "and is unavailable while offline",
            )
        return None

    def _requires_network(self, tool_name: str) -> bool:
        """Return whether one tool needs external network egress."""
        return (
            tool_name in NETWORK_TOOL_NAMES
            or tool_name in self._extra_network_tools
        )


__all__ = [
    "DesktopToolDispatcher",
    "ERROR_CAPABILITY_UNAVAILABLE",
    "ERROR_INVALID_ARGUMENTS",
    "ERROR_OFFLINE_BLOCKED",
    "ERROR_PUBLICATION_DENIED",
    "ERROR_TOOL_FAILED",
    "NETWORK_TOOL_NAMES",
    "RegisteredTool",
    "default_publication_allowed",
    "failed_dispatch",
]
