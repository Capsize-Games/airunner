"""Bounded multi-round tool execution for companion turns (B11).

Runs already-selected ``ToolDispatchRequest`` values through any
B01-compatible dispatch callable with bounded rounds
(``ContextBudget.max_tool_calls`` by default) and wall time,
honoring cancellation between rounds. Successful tool output is
run through the S12 publication gate before it enters a transcript;
denied content is replaced by the generic denial message while the
producing tool's name is preserved. Transcripts always label tool
content ``role: "tool"`` so it can never read as a system
instruction downstream.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .contracts import ContextBudget
from .tool_dispatch import ToolDispatchRequest, ToolDispatchResult
from .tool_routing import (
    ERROR_PUBLICATION_DENIED,
    default_publication_allowed,
    failed_dispatch,
)

STOP_COMPLETED = "completed"
STOP_LOOP_LIMIT = "loop_limit"
STOP_CANCELLED = "cancelled"
STOP_DEADLINE = "deadline"

DispatchFn = Callable[[ToolDispatchRequest], ToolDispatchResult]


@dataclass(frozen=True)
class ToolLoopResult:
    """Outcome of one bounded multi-round tool run."""

    results: List[ToolDispatchResult]
    stopped_reason: str
    rounds_executed: int


def format_tool_context(
    results: List[ToolDispatchResult],
) -> List[Dict[str, str]]:
    """Format results as quoted tool context for prompt composition."""
    return [
        {
            "role": "tool",
            "name": result.tool_name,
            "content": result.content,
        }
        for result in results
    ]


def run_tool_rounds(
    dispatch: DispatchFn,
    requests: List[ToolDispatchRequest],
    *,
    max_rounds: Optional[int] = None,
    time_limit_seconds: Optional[float] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    clock: Callable[[], float] = time.monotonic,
    gate_tool_output: bool = True,
    publication_allowed: Optional[Callable[[str], bool]] = None,
) -> ToolLoopResult:
    """Execute dispatch requests with bounded rounds and time."""
    allowed = publication_allowed or default_publication_allowed
    return _collect_rounds(
        dispatch,
        requests,
        _round_limit(max_rounds),
        clock(),
        time_limit_seconds,
        is_cancelled,
        clock,
        gate_tool_output,
        allowed,
    )


def _collect_rounds(
    dispatch: DispatchFn,
    requests: List[ToolDispatchRequest],
    limit: int,
    start: float,
    time_limit: Optional[float],
    is_cancelled: Optional[Callable[[], bool]],
    clock: Callable[[], float],
    gate: bool,
    allowed: Callable[[str], bool],
) -> ToolLoopResult:
    """Run rounds until requests end or a stop reason triggers."""
    results: List[ToolDispatchResult] = []
    for index, request in enumerate(requests):
        args = (index, limit, start, time_limit, is_cancelled, clock)
        stop = _stop_reason(*args)
        if stop is not None:
            return ToolLoopResult(results, stop, len(results))
        results.append(_run_round(dispatch, request, gate, allowed))
    return ToolLoopResult(results, STOP_COMPLETED, len(results))


def _run_round(
    dispatch: DispatchFn,
    request: ToolDispatchRequest,
    gate: bool,
    allowed: Callable[[str], bool],
) -> ToolDispatchResult:
    """Dispatch one round, gating successful output when asked."""
    result = dispatch(request)
    if gate and result.succeeded:
        return _apply_publication_gate(result, allowed)
    return result


def _apply_publication_gate(
    result: ToolDispatchResult,
    allowed: Callable[[str], bool],
) -> ToolDispatchResult:
    """Replace gate-denied tool content with the generic message."""
    if allowed(result.content):
        return result
    from airunner_services.content_safety_gate import (
        GENERIC_PUBLICATION_DENIAL_MESSAGE,
    )

    return failed_dispatch(
        result.tool_name,
        ERROR_PUBLICATION_DENIED,
        GENERIC_PUBLICATION_DENIAL_MESSAGE,
    )


def _round_limit(max_rounds: Optional[int]) -> int:
    """Return the round cap, defaulting to the context budget."""
    if max_rounds is not None:
        return max_rounds
    return ContextBudget().max_tool_calls


def _stop_reason(
    index: int,
    limit: int,
    start: float,
    time_limit: Optional[float],
    is_cancelled: Optional[Callable[[], bool]],
    clock: Callable[[], float],
) -> Optional[str]:
    """Return why the loop must stop before round ``index``, if so."""
    if index >= limit:
        return STOP_LOOP_LIMIT
    if is_cancelled is not None and is_cancelled():
        return STOP_CANCELLED
    if time_limit is not None and clock() - start > time_limit:
        return STOP_DEADLINE
    return None


__all__ = [
    "DispatchFn",
    "STOP_CANCELLED",
    "STOP_COMPLETED",
    "STOP_DEADLINE",
    "STOP_LOOP_LIMIT",
    "ToolLoopResult",
    "format_tool_context",
    "run_tool_rounds",
]
