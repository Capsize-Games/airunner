"""Application-level helpers for the content-safety input gate.

This module deliberately contains **no matching logic**. It is a thin
shared application layer that delegates to the hash-based matcher in
:mod:`airunner_services.content_safety` and centralizes the single
generic rejection message used by every generation entry point.

Both the HTTP generation route and the signal-driven art worker call
:func:`evaluate_prompt_fields`, so there is exactly one validator and one
generic message across the GUI path and the LLM image-tool path.

Ordering: the hash matcher runs first and a match blocks immediately without
consulting the optional semantic judge (fast path). Only a clean hash check
proceeds to the semantic layer, which is off by default and only ever adds a
block -- it can never turn a matcher block into an allow.

No function here logs, returns, or otherwise surfaces the checked text or
any matched term; only a boolean, a generic reason code and a field name
leave the matcher.
"""

from __future__ import annotations

from typing import Optional

from airunner_services.content_safety import (
    ContentSafetyResult,
    check_prompt_fields,
)
from airunner_services.content_safety.semantic import (
    REASON_BLOCKED as SEMANTIC_BLOCKED_REASON,
    evaluate_fields_semantic,
)

# Generic, content-free rejection surfaced to callers. It must never be
# altered to include field text, a field name, or a matched term.
GENERIC_REJECTION_MESSAGE = "Request rejected by content safety policy"


def evaluate_prompt_fields(
    fields: dict[str, Optional[str]],
) -> ContentSafetyResult:
    """Return the gate result for one generation request's text fields.

    The hash matcher runs first; a match blocks immediately and the semantic
    judge is never called. ``None`` and empty values are skipped. When no
    policy data set is loaded the matcher reports the request as allowed, so
    callers stay usable until a policy set is generated out of band.

    After a clean hash check, the optional semantic layer is consulted (off
    by default and inert unless a judge is registered). It blocks only on an
    explicit not-allowed verdict; unavailable, timed-out, erroring, or
    ambiguous outcomes leave the request allowed.
    """
    result = check_prompt_fields(**fields)
    if not result.allowed:
        return result
    semantic_fields = {
        name: value
        for name, value in fields.items()
        if isinstance(value, str) and value
    }
    if not semantic_fields:
        return result
    verdict = evaluate_fields_semantic(semantic_fields)
    if verdict.evaluated and not verdict.allowed:
        return ContentSafetyResult(
            allowed=False,
            reason=SEMANTIC_BLOCKED_REASON,
            field=None,
        )
    return result


__all__ = [
    "GENERIC_REJECTION_MESSAGE",
    "evaluate_prompt_fields",
]
