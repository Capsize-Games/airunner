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
block -- it can never turn a matcher block into an allow. A clean optional
check then proceeds to the required contextual layer (S08), which is
likewise OFF by default -- the S07 evaluator selection behind it is
approved (see ``release-planning/linux-v1/safety-evaluation.md`` §2;
adapter: ``content_safety.qwen_guard``) -- and fails closed when
enabled: unavailable, timed-out, erroring, or ambiguous outcomes deny.
Matcher denials are always preserved: no later layer runs after a
matcher block.

When mandatory policy data is missing, empty, or invalid, the gate denies
generation before any side effect; callers surface the actionable
installation/policy error from :func:`rejection_message` for that reason.

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
from airunner_services.content_safety.matcher import (
    REASON_POLICY_UNAVAILABLE,
)
from airunner_services.content_safety.semantic import (
    REASON_BLOCKED as SEMANTIC_BLOCKED_REASON,
    contextual_enabled,
    evaluate_fields_contextual,
    evaluate_fields_semantic,
)

# Generic, content-free rejection surfaced to callers. It must never be
# altered to include field text, a field name, or a matched term.
GENERIC_REJECTION_MESSAGE = "Request rejected by content safety policy"

# Generic, actionable error surfaced when mandatory policy data is
# unavailable. It names only the installation/policy failure and the
# operator repair step; it never includes field text or a matched term.
GENERIC_POLICY_ERROR_MESSAGE = (
    "Image generation is unavailable: content safety policy data "
    "is missing or invalid; repair or reinstall the application"
)

# Generic, content-free final message published when the output gate
# withholds generated text or derived speech. It is intentionally
# distinct from model-failure text ("Error: ...", empty-reply fallbacks):
# a denial is a policy decision, not a broken model run.
GENERIC_PUBLICATION_DENIAL_MESSAGE = (
    "Response withheld by content safety policy"
)


def rejection_message(result: ContentSafetyResult) -> str:
    """Return the caller-facing message for one gate ``result``.

    Unavailable-policy denials surface the actionable installation/policy
    error; every other denial surfaces the generic rejection message.
    Neither message echoes checked text or a matched term.
    """
    if result.reason == REASON_POLICY_UNAVAILABLE:
        return GENERIC_POLICY_ERROR_MESSAGE
    return GENERIC_REJECTION_MESSAGE


def evaluate_prompt_fields(
    fields: dict[str, Optional[str]],
) -> ContentSafetyResult:
    """Return the gate result for one generation request's text fields.

    The hash matcher runs first; a match blocks immediately and the semantic
    judge is never called. ``None`` and empty values are skipped. When no
    policy data set is loaded the matcher denies the request with the
    policy-unavailable reason, so generation cannot proceed without its
    mandatory check; callers surface that denial via :func:`rejection_message`.

    After a clean hash check, the optional semantic layer is consulted (off
    by default and inert unless a judge is registered). It blocks only on an
    explicit not-allowed verdict; unavailable, timed-out, erroring, or
    ambiguous outcomes leave the request allowed. A clean optional check
    then proceeds to the required contextual layer, which runs only when
    explicitly enabled (OFF by default until release enablement) and
    fails closed: any non-allowed contextual outcome denies with a
    generic, content-free reason.
    """
    result = check_prompt_fields(**fields)
    if not result.allowed:
        return result
    denial = _check_post_match_layers(fields)
    return denial if denial is not None else result


def evaluate_publication_fields(
    fields: dict[str, Optional[str]],
) -> ContentSafetyResult:
    """Return the gate result for generated text before publication.

    Same layering as :func:`evaluate_prompt_fields`: the mandatory hash
    matcher runs first and blocks immediately (including when policy data
    is unavailable), then the optional semantic layer, then the required
    contextual layer which fails closed when enabled. Callers evaluate the
    complete buffered output -- streamed tokens, tool-originated final
    text, and text handed to speech -- and publish only when allowed.
    """
    result = check_prompt_fields(**fields)
    if not result.allowed:
        return result
    denial = _check_post_match_layers(fields)
    return denial if denial is not None else result


def _check_post_match_layers(
    fields: dict[str, Optional[str]],
) -> Optional[ContentSafetyResult]:
    """Return a post-matcher denial, or ``None`` when layers pass."""
    semantic_fields = {
        name: value
        for name, value in fields.items()
        if isinstance(value, str) and value
    }
    if not semantic_fields:
        return None
    verdict = evaluate_fields_semantic(semantic_fields)
    if verdict.evaluated and not verdict.allowed:
        return ContentSafetyResult(
            allowed=False,
            reason=SEMANTIC_BLOCKED_REASON,
            field=None,
        )
    if contextual_enabled():
        contextual = evaluate_fields_contextual(semantic_fields)
        if not contextual.allowed:
            return ContentSafetyResult(
                allowed=False,
                reason=contextual.reason,
                field=None,
            )
    return None


__all__ = [
    "GENERIC_POLICY_ERROR_MESSAGE",
    "GENERIC_PUBLICATION_DENIAL_MESSAGE",
    "GENERIC_REJECTION_MESSAGE",
    "evaluate_prompt_fields",
    "evaluate_publication_fields",
    "rejection_message",
]
