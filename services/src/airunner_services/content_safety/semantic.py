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
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Environment switch. Any of "1"/"true"/"yes"/"on" (case-insensitive)
# enables the layer; everything else leaves it OFF.
SEMANTIC_ENV_VAR = "AIRUNNER_CONTENT_SAFETY_SEMANTIC"

# Hard ceiling on a single judge call. Kept short so a slow or stuck model
# can never stall generation through this optional layer.
SEMANTIC_TIMEOUT_SECONDS = 5.0

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


def _call_with_timeout(
    judge: Judge, fields: dict[str, str], timeout: float
) -> SemanticVerdict:
    """Run ``judge`` on a daemon thread and return within ``timeout`` seconds.

    A daemon thread is used so a stuck call can never block interpreter
    shutdown, and the caller raises :class:`_JudgeTimeout` rather than
    waiting indefinitely.
    """
    outcome: list = []

    def _run() -> None:
        try:
            outcome.append((True, judge(fields)))
        except BaseException as exc:  # noqa: BLE001 - re-raised to caller
            outcome.append((False, exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise _JudgeTimeout("semantic judge exceeded the timeout budget")
    if not outcome:
        raise RuntimeError("semantic judge produced no result")
    succeeded, value = outcome[0]
    if not succeeded:
        raise value
    return value


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


__all__ = [
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
    "evaluate_fields_semantic",
    "get_judge",
    "make_llm_judge",
    "parse_judge_response",
    "semantic_enabled",
    "set_judge",
]
