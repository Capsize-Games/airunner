"""Application-level helpers for the content-safety input gate.

This module deliberately contains **no matching logic**. It is a thin
shared application layer that delegates to the hash-based matcher in
:mod:`airunner_services.content_safety` and centralizes the single
generic rejection message used by every generation entry point.

Enforcement architecture: the authoritative choke point sits
in-pipeline -- the art manager ``_generate`` paths and the Z-Image
pipeline ``__call__`` entries call :func:`enforce_prompt_fields` (or
:func:`enforce_prompt_text`) first, so a direct in-process generate
call cannot bypass the mandatory hash check. The HTTP generation
routes, the signal-driven art worker, and the LLM image tool keep
calling :func:`evaluate_prompt_fields` as early defense-in-depth
pre-checks that reject before side effects; they share exactly the one
validator and one generic message with the choke point.

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


class ContentSafetyDenied(Exception):
    """Raised by in-pipeline choke points on a gate denial.

    Carries only the gate ``result`` (a boolean, a generic reason code,
    and a field name). ``str()`` is exactly :func:`rejection_message`,
    so no checked text or matched term can leave through the exception.
    """

    def __init__(self, result: ContentSafetyResult) -> None:
        self.result = result
        super().__init__(rejection_message(result))


def has_checkable_text(fields: dict[str, Optional[str]]) -> bool:
    """Return whether any field holds text the gate can match.

    Mirrors :func:`check_text`: empty and non-string values carry
    nothing to match, so a request with no text at all is vacuous for
    the hash gate even when policy data is unavailable.
    """
    return any(
        isinstance(value, str) and value for value in fields.values()
    )


def enforce_prompt_fields(
    fields: dict[str, Optional[str]],
) -> None:
    """Evaluate ``fields`` and raise :class:`ContentSafetyDenied`.

    The single raising validator for in-pipeline choke points: it runs
    :func:`evaluate_prompt_fields` and raises on any denial, including
    the fail-closed policy-unavailable denial when mandatory policy
    data is missing, empty, or invalid. When no field holds text there
    is nothing to match, so the call passes -- this never weakens a
    text-bearing call, which always fails closed when data is unusable.
    """
    if not has_checkable_text(fields):
        return
    result = evaluate_prompt_fields(fields)
    if not result.allowed:
        raise ContentSafetyDenied(result)


def enforce_prompt_text(
    prompt: str | list[str] | None,
    negative_prompt: str | list[str] | None = None,
) -> None:
    """Enforce the gate over raw pipeline prompt arguments.

    Each non-empty text is checked on its own so batched prompts never
    merge across element boundaries. ``None`` (embeddings-only calls,
    which carry no text to match) is skipped: text-bearing flows are
    always gated with their request text at the manager entry above.
    """
    for name, value in (
        ("prompt", prompt),
        ("negative_prompt", negative_prompt),
    ):
        if value is None:
            continue
        texts = [value] if isinstance(value, str) else list(value)
        for text in texts:
            if isinstance(text, str) and text:
                enforce_prompt_fields({name: text})


def prompt_fields_from_request(
    request: object,
) -> dict[str, Optional[str]]:
    """Return the four gated text fields read off a request object.

    Missing attributes read as ``None`` and are skipped by the gate,
    mirroring the sources the worker and managers already use.
    """
    return {
        name: getattr(request, name, None)
        for name in (
            "prompt",
            "negative_prompt",
            "second_prompt",
            "second_negative_prompt",
        )
    }


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
    "ContentSafetyDenied",
    "GENERIC_POLICY_ERROR_MESSAGE",
    "GENERIC_PUBLICATION_DENIAL_MESSAGE",
    "GENERIC_REJECTION_MESSAGE",
    "enforce_prompt_fields",
    "enforce_prompt_text",
    "evaluate_prompt_fields",
    "evaluate_publication_fields",
    "has_checkable_text",
    "prompt_fields_from_request",
    "rejection_message",
]
