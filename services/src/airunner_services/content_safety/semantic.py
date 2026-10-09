"""Optional, best-effort semantic content-safety layer (default OFF).

This module is a SECONDARY input-side signal that complements the primary
hash-based matcher in :mod:`airunner_services.content_safety.matcher`. It
asks a local language model (reusing the existing guardrails prompt when
available) to classify a generation request as allowed or not, catching
euphemisms and paraphrases a token matcher cannot see.

Design constraints (deliberately conservative):

* **Default OFF.** The layer only runs when the environment variable
  :data:`SEMANTIC_ENV_VAR` is truthy. With no judge registered it stays
  completely inert.
* **Never fail closed.** A missing judge, a disabled layer, a timeout, an
  exception, or an ambiguous/unparseable judge response all resolve to
  ``allowed`` with a generic, content-free status. This layer may only add
  a block; it can never turn a hash-matcher block into an allow, and it can
  never hang or hard-fail generation.
* **Bounded latency.** Every judge call is wrapped in a short,
  module-constant timeout (:data:`SEMANTIC_TIMEOUT_SECONDS`).
* **No content disclosure.** Nothing here logs, returns, or otherwise
  surfaces the checked text. Only booleans, counts, and generic reason
  codes leave these functions.

The judge is injected by the application through :func:`set_judge`; the
module never imports model machinery. :func:`make_llm_judge` builds a ready
adapter around any synchronous text-generation callable, composing its
instruction from the existing guardrails prompt (falling back to a short
built-in generic instruction) and parsing the response strictly.

S08 required contextual adapter (default OFF, pending S07 approval)
------------------------------------------------------------------
:func:`evaluate_fields_contextual` is the REQUIRED input-side contextual
check behind the S07 selection
(``release-planning/linux-v1/safety-evaluation.md``). That selection is a
DRAFT: the text slot has no approved evaluator and the proposed §4
thresholds are unapproved, so this layer stays OFF unless
:data:`CONTEXTUAL_ENV_VAR` is truthy. The evaluator choice stays behind
the injection seam (:func:`set_evaluator`, falling back to the approved
:func:`set_judge` seam); no model, provider, or download is wired in, and
inference is local-only through the injected callable.

Unlike the optional layer above, the required check fails closed: only an
explicit allowed verdict allows, while unavailable, timed-out, erroring,
or ambiguous outcomes all deny. Every call runs on one shared bounded
pool (:data:`CONTEXTUAL_MAX_WORKERS`), so a timeout cancels the queued
wait without spawning an unbounded chain of abandoned threads.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Environment switch. Any of "1"/"true"/"yes"/"on" (case-insensitive)
# enables the layer; everything else leaves it OFF.
SEMANTIC_ENV_VAR = "AIRUNNER_CONTENT_SAFETY_SEMANTIC"

# Hard ceiling on a single judge call. Kept short so a slow or stuck model
# can never stall generation through this optional layer.
SEMANTIC_TIMEOUT_SECONDS = 5.0

# Required contextual check (S08). Same 5 s ceiling as the optional layer
# (safety-evaluation.md §4 L4 keeps 5 s); still pending S07 approval, like
# every other proposed threshold -- no numeric threshold is approved yet.
CONTEXTUAL_ENV_VAR = "AIRUNNER_CONTENT_SAFETY_CONTEXTUAL"
CONTEXTUAL_TIMEOUT_SECONDS = 5.0

# Bound on the shared safety worker pool. One worker serializes judge
# calls so concurrent generations can never spawn unbounded threads.
CONTEXTUAL_MAX_WORKERS = 1

# Generic, content-free reason codes. These never contain field text.
REASON_DISABLED = "disabled"
REASON_UNAVAILABLE = "unavailable"
REASON_ALLOWED = "semantic_allowed"
REASON_BLOCKED = "semantic_review"
REASON_AMBIGUOUS = "semantic_ambiguous"
REASON_ERROR = "semantic_error"
REASON_TIMEOUT = "semantic_timeout"

# The single explicit token the judge must answer with. Only an explicit
# UNSAFE answer blocks; anything else is treated as ambiguous and allowed.
TOKEN_ALLOW = "SAFE"
TOKEN_BLOCK = "UNSAFE"

_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Generic classifier instruction used when no guardrails prompt is supplied.
# It deliberately contains no sensitive terms and no example content.
_DEFAULT_INSTRUCTION = (
    "You are a content-safety classifier. Read the user-provided text and "
    "decide whether it requests or describes prohibited content. "
    "Answer with exactly one word: SAFE or UNSAFE. Do not explain."
)

Judge = Callable[[dict[str, str]], "SemanticVerdict"]

_judge: Optional[Judge] = None

# S08 required-check evaluator. When unset, the required check falls back
# to the approved :func:`set_judge` seam so the evaluator choice stays
# behind one injection point; no model is ever wired in here.
_evaluator: Optional[Judge] = None

_executor_lock = threading.Lock()
_executor: Optional[ThreadPoolExecutor] = None


@dataclass(frozen=True)
class SemanticVerdict:
    """Outcome of one semantic review.

    ``evaluated`` is ``True`` only when the judge actually ran. ``reason`` is
    always a generic code and never contains field text or model output.
    """

    evaluated: bool
    allowed: bool
    reason: str

    @classmethod
    def allow(cls, reason: str, *, evaluated: bool = True) -> "SemanticVerdict":
        """Return an allowed verdict with a generic ``reason``."""
        return cls(evaluated=evaluated, allowed=True, reason=reason)

    @classmethod
    def block(cls, reason: str = REASON_BLOCKED) -> "SemanticVerdict":
        """Return a blocking verdict with a generic ``reason``."""
        return cls(evaluated=True, allowed=False, reason=reason)


def semantic_enabled() -> bool:
    """Return ``True`` when the optional semantic layer is switched on."""
    raw = os.environ.get(SEMANTIC_ENV_VAR)
    return isinstance(raw, str) and raw.strip().lower() in _TRUTHY


def set_judge(judge: Optional[Judge]) -> None:
    """Register (or clear with ``None``) the injected semantic judge."""
    global _judge
    _judge = judge


def get_judge() -> Optional[Judge]:
    """Return the currently registered judge, or ``None`` when unset."""
    return _judge


def set_evaluator(evaluator: Optional[Judge]) -> None:
    """Register (or clear with ``None``) the required-check evaluator."""
    global _evaluator
    _evaluator = evaluator


def get_evaluator() -> Optional[Judge]:
    """Return the registered required-check evaluator, or ``None``."""
    return _evaluator


def _resolve_evaluator() -> Optional[Judge]:
    """Return the required-check evaluator, falling back to the judge seam."""
    if _evaluator is not None:
        return _evaluator
    return get_judge()


def contextual_enabled() -> bool:
    """Return ``True`` when the required contextual check is switched on."""
    raw = os.environ.get(CONTEXTUAL_ENV_VAR)
    return isinstance(raw, str) and raw.strip().lower() in _TRUTHY


def contextual_max_workers() -> int:
    """Return the bound on shared safety worker threads."""
    return CONTEXTUAL_MAX_WORKERS


def build_judge_instruction(
    guardrails_prompt: Optional[str] = None,
) -> str:
    """Compose the judge instruction, reusing the guardrails prompt.

    When ``guardrails_prompt`` is a non-empty string it is prepended to the
    generic classifier instruction so the model is steered by the same
    policy wording the rest of the application already uses. Otherwise the
    short built-in generic instruction is returned unchanged.
    """
    guardrails = (guardrails_prompt or "").strip()
    if guardrails:
        return f"{guardrails}\n\n{_DEFAULT_INSTRUCTION}"
    return _DEFAULT_INSTRUCTION


def parse_judge_response(response: Optional[str]) -> SemanticVerdict:
    """Parse one judge response strictly; only an explicit UNSAFE blocks.

    Anything other than an explicit ``UNSAFE`` token -- including an empty,
    missing, or unparseable response -- is treated as ambiguous and allowed.
    The response text is never logged or returned.
    """
    if not isinstance(response, str) or not response.strip():
        return SemanticVerdict.allow(REASON_AMBIGUOUS)
    tokens = [
        token.upper()
        for token in re.findall(r"[A-Za-z]+", response)
    ]
    if TOKEN_BLOCK in tokens:
        return SemanticVerdict.block(REASON_BLOCKED)
    if TOKEN_ALLOW in tokens:
        return SemanticVerdict.allow(REASON_ALLOWED)
    return SemanticVerdict.allow(REASON_AMBIGUOUS)


def _render_judge_request(instruction: str, fields: dict[str, str]) -> str:
    """Render the internal judge request carrying the text to classify.

    The rendered request necessarily contains the field text so the model can
    classify it, but it is only ever passed to the injected callable -- it is
    never logged or surfaced.
    """
    parts = [instruction, ""]
    for name, value in fields.items():
        parts.append(f"{name}:\n{value}")
    return "\n".join(parts)


def make_llm_judge(
    generate: Callable[[str], Optional[str]],
    *,
    guardrails_prompt: Optional[str] = None,
) -> Judge:
    """Build a judge adapter around a synchronous text-generation callable.

    ``generate`` receives one already-composed request string and returns the
    model's raw text (or ``None``). The adapter composes the instruction from
    ``guardrails_prompt`` when available and parses the response strictly.
    Exceptions and timeouts are handled by :func:`evaluate_fields_semantic`,
    not here.
    """
    instruction = build_judge_instruction(guardrails_prompt)

    def _judge(fields: dict[str, str]) -> SemanticVerdict:
        request = _render_judge_request(instruction, fields)
        return parse_judge_response(generate(request))

    return _judge


class _JudgeTimeout(Exception):
    """Raised internally when the judge exceeds the timeout budget."""


def _get_executor() -> ThreadPoolExecutor:
    """Return the shared bounded safety worker pool (created once)."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=CONTEXTUAL_MAX_WORKERS,
                thread_name_prefix="airunner-safety",
            )
        return _executor


def reset_contextual_workers() -> None:
    """Shut down the shared safety worker pool (test hook).

    Queued work is cancelled and a running judge call is awaited so the
    worker count returns to zero; the pool is recreated on next use with
    :data:`CONTEXTUAL_MAX_WORKERS` workers. Only tests need this.
    """
    global _executor
    with _executor_lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=True, cancel_futures=True)


def _call_with_timeout(
    judge: Judge, fields: dict[str, str], timeout: float
) -> SemanticVerdict:
    """Run ``judge`` on the shared bounded pool within ``timeout`` seconds.

    The pool holds at most :data:`CONTEXTUAL_MAX_WORKERS` workers, so
    concurrent or repeated calls can never spawn an unbounded chain of
    threads. On timeout the queued wait is cancelled and the caller raises
    :class:`_JudgeTimeout` rather than waiting indefinitely.
    """
    future = _get_executor().submit(judge, fields)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError:
        future.cancel()
        raise _JudgeTimeout("semantic judge exceeded the timeout budget")


def evaluate_fields_semantic(fields: dict[str, str]) -> SemanticVerdict:
    """Run the optional semantic review over a request's text fields.

    Returns an allowed verdict (with a generic reason) whenever the layer is
    unavailable in any way: disabled, no judge registered, judge timed out,
    judge raised, or the judge returned an unexpected value. Only an explicit
    evaluated not-allowed verdict blocks. No field text is ever logged.
    """
    if not semantic_enabled():
        return SemanticVerdict.allow(REASON_DISABLED, evaluated=False)
    judge = get_judge()
    if judge is None:
        logger.warning(
            "Semantic content-safety layer enabled but no judge is "
            "registered; allowing request (reason=%s)",
            REASON_UNAVAILABLE,
        )
        return SemanticVerdict.allow(REASON_UNAVAILABLE, evaluated=False)
    cleaned = {
        name: value
        for name, value in (fields or {}).items()
        if isinstance(value, str) and value
    }
    if not cleaned:
        return SemanticVerdict.allow(REASON_ALLOWED, evaluated=False)
    field_count = len(cleaned)
    try:
        verdict = _call_with_timeout(judge, cleaned, SEMANTIC_TIMEOUT_SECONDS)
    except _JudgeTimeout:
        logger.warning(
            "Semantic content-safety judge timed out; allowing request "
            "(fields=%d, reason=%s)",
            field_count,
            REASON_TIMEOUT,
        )
        return SemanticVerdict.allow(REASON_TIMEOUT, evaluated=True)
    except Exception:
        # Never include the exception text: it could embed prompt content.
        logger.warning(
            "Semantic content-safety judge error; allowing request "
            "(fields=%d, reason=%s)",
            field_count,
            REASON_ERROR,
        )
        return SemanticVerdict.allow(REASON_ERROR, evaluated=True)
    if not isinstance(verdict, SemanticVerdict):
        logger.warning(
            "Semantic content-safety judge returned an unexpected result; "
            "allowing request (fields=%d, reason=%s)",
            field_count,
            REASON_AMBIGUOUS,
        )
        return SemanticVerdict.allow(REASON_AMBIGUOUS, evaluated=True)
    if verdict.evaluated and not verdict.allowed:
        # Echo only the fixed generic reason, never the judge's own text.
        logger.info(
            "Semantic content-safety judge flagged a request "
            "(fields=%d, reason=%s)",
            field_count,
            REASON_BLOCKED,
        )
        return SemanticVerdict.block(REASON_BLOCKED)
    return verdict


def evaluate_fields_contextual(
    fields: dict[str, str],
) -> SemanticVerdict:
    """Run the REQUIRED contextual check over a request's text fields.

    Fail-closed: only an explicit evaluated allowed verdict allows. A
    missing evaluator, a timeout, an error, an unexpected return value,
    or an ambiguous outcome all deny. No field text is ever logged. The
    layer runs only when :func:`contextual_enabled` is true; while the
    S07 selection is an unapproved draft it stays OFF by default.
    """
    if not contextual_enabled():
        return SemanticVerdict.allow(REASON_DISABLED, evaluated=False)
    evaluator = _resolve_evaluator()
    if evaluator is None:
        logger.warning(
            "Contextual content-safety check enabled but no evaluator "
            "is registered; denying request (reason=%s)",
            REASON_UNAVAILABLE,
        )
        return SemanticVerdict(
            evaluated=False, allowed=False, reason=REASON_UNAVAILABLE
        )
    cleaned = {
        name: value
        for name, value in (fields or {}).items()
        if isinstance(value, str) and value
    }
    if not cleaned:
        return SemanticVerdict.allow(REASON_ALLOWED, evaluated=False)
    field_count = len(cleaned)
    try:
        verdict = _call_with_timeout(
            evaluator, cleaned, CONTEXTUAL_TIMEOUT_SECONDS
        )
    except _JudgeTimeout:
        logger.warning(
            "Contextual content-safety evaluator timed out; denying "
            "request (fields=%d, reason=%s)",
            field_count,
            REASON_TIMEOUT,
        )
        return SemanticVerdict(
            evaluated=True, allowed=False, reason=REASON_TIMEOUT
        )
    except Exception:
        # Never include the exception text: it could embed prompt content.
        logger.warning(
            "Contextual content-safety evaluator error; denying "
            "request (fields=%d, reason=%s)",
            field_count,
            REASON_ERROR,
        )
        return SemanticVerdict(
            evaluated=True, allowed=False, reason=REASON_ERROR
        )
    if not isinstance(verdict, SemanticVerdict):
        logger.warning(
            "Contextual content-safety evaluator returned an "
            "unexpected result; denying request (fields=%d, reason=%s)",
            field_count,
            REASON_AMBIGUOUS,
        )
        return SemanticVerdict(
            evaluated=True, allowed=False, reason=REASON_AMBIGUOUS
        )
    if verdict.evaluated and verdict.allowed:
        if verdict.reason == REASON_ALLOWED:
            return verdict
        # An allowed verdict without the explicit allowed reason is
        # ambiguous: only an explicit SAFE allows.
        logger.warning(
            "Contextual content-safety evaluator was ambiguous; "
            "denying request (fields=%d, reason=%s)",
            field_count,
            REASON_AMBIGUOUS,
        )
        return SemanticVerdict(
            evaluated=True, allowed=False, reason=REASON_AMBIGUOUS
        )
    # Echo only the fixed generic reason, never the evaluator's own text.
    logger.info(
        "Contextual content-safety evaluator flagged a request "
        "(fields=%d, reason=%s)",
        field_count,
        REASON_BLOCKED,
    )
    return SemanticVerdict.block(REASON_BLOCKED)


__all__ = [
    "CONTEXTUAL_ENV_VAR",
    "CONTEXTUAL_MAX_WORKERS",
    "CONTEXTUAL_TIMEOUT_SECONDS",
    "SEMANTIC_ENV_VAR",
    "SEMANTIC_TIMEOUT_SECONDS",
    "REASON_ALLOWED",
    "REASON_AMBIGUOUS",
    "REASON_BLOCKED",
    "REASON_DISABLED",
    "REASON_ERROR",
    "REASON_TIMEOUT",
    "REASON_UNAVAILABLE",
    "TOKEN_ALLOW",
    "TOKEN_BLOCK",
    "Judge",
    "SemanticVerdict",
    "build_judge_instruction",
    "contextual_enabled",
    "contextual_max_workers",
    "evaluate_fields_contextual",
    "evaluate_fields_semantic",
    "get_evaluator",
    "get_judge",
    "make_llm_judge",
    "parse_judge_response",
    "reset_contextual_workers",
    "semantic_enabled",
    "set_evaluator",
    "set_judge",
]
