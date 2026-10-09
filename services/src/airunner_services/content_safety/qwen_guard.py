"""Required contextual text adapter: Qwen3Guard-Gen-0.6B (S08, #2252).

Approved input-side evaluator (S07 section 2): Qwen3Guard-Gen-0.6B
(Apache-2.0) on the pinned transformers stack, strict mode
(Controversial counts as unsafe). Only an explicit Safety Safe
verdict allows; Unsafe, strict Controversial, missing, empty, and
unparseable replies all deny.

:func:`load_qwen_guard_evaluator` builds its pipeline with
``local_files_only=True``: a missing cache entry fails as
unavailable instead of downloading. No reply or field text is ever
logged or returned; only verdicts and generic reasons leave here.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from airunner_services.content_safety.semantic import (
    REASON_ALLOWED,
    REASON_AMBIGUOUS,
    REASON_BLOCKED,
    Judge,
    SemanticVerdict,
    set_evaluator,
)

logger = logging.getLogger(__name__)

# Approved text evaluator (S07 section 2). P11 records the immutable
# SHA pin for MODEL_REVISION once weights are provisioned; until then
# the loader resolves the cached default revision, still offline.
MODEL_ID = "Qwen/Qwen3Guard-Gen-0.6B"
MODEL_REVISION: Optional[str] = None

# Generation budget per the S07 seam-fit note (at most 128 new tokens).
MAX_NEW_TOKENS = 128

# Bound on one rendered request so a huge field cannot stall the
# shared single-worker pool behind the contextual seam.
MAX_INPUT_CHARS = 4000

_LABEL_SAFE = "safe"
_LABEL_UNSAFE = "unsafe"
_LABEL_CONTROVERSIAL = "controversial"

_SAFETY_LINE = re.compile(
    r"^\s*safety\s*:\s*([A-Za-z]+)", re.IGNORECASE | re.MULTILINE
)


class QwenGuardUnavailableError(RuntimeError):
    """Raised when the guard cannot be loaded from the local cache."""


def parse_guard_response(
    response: Optional[str], *, strict: bool = True
) -> SemanticVerdict:
    """Parse a guard reply; only an explicit Safe verdict allows."""
    label = _safety_label(response)
    if label == _LABEL_SAFE:
        return SemanticVerdict.allow(REASON_ALLOWED)
    if label == _LABEL_UNSAFE:
        return SemanticVerdict.block(REASON_BLOCKED)
    if label == _LABEL_CONTROVERSIAL and strict:
        return SemanticVerdict.block(REASON_BLOCKED)
    return _deny_ambiguous()


def build_guard_request(fields: dict[str, str]) -> str:
    """Render fields into one bounded classification request."""
    parts = []
    for name in sorted(fields):
        value = fields[name]
        if isinstance(value, str) and value:
            parts.append(f"{name}:\n{value}")
    return "\n\n".join(parts)[:MAX_INPUT_CHARS]


def make_qwen_guard_evaluator(
    generate: Callable[[str], Optional[str]], *, strict: bool = True
) -> Judge:
    """Adapt a text-generation callable to the S08 evaluator seam."""
    def _evaluate(fields: dict[str, str]) -> SemanticVerdict:
        request = build_guard_request(fields)
        return parse_guard_response(generate(request), strict=strict)

    return _evaluate


def load_qwen_guard_evaluator(
    *, model_id: str = MODEL_ID, revision: Optional[str] = MODEL_REVISION,
    strict: bool = True,
) -> Judge:
    """Load the guard from the local cache; never uses the network."""
    classifier = _build_pipeline(model_id, revision)
    apply_template = classifier.tokenizer.apply_chat_template

    def _generate(request: str) -> Optional[str]:
        prompt = apply_template(
            [{"role": "user", "content": request}],
            tokenize=False, add_generation_prompt=True,
        )
        outputs = classifier(
            prompt, max_new_tokens=MAX_NEW_TOKENS,
            return_full_text=False,
        )
        return outputs[0]["generated_text"]

    return make_qwen_guard_evaluator(_generate, strict=strict)


def register_qwen_guard_evaluator(
    *, model_id: str = MODEL_ID, revision: Optional[str] = MODEL_REVISION,
    strict: bool = True,
) -> Judge:
    """Load the guard and register it on the S08 seam; return it."""
    evaluator = load_qwen_guard_evaluator(
        model_id=model_id, revision=revision, strict=strict
    )
    set_evaluator(evaluator)
    logger.info("Registered the required contextual evaluator")
    return evaluator


def _safety_label(response: Optional[str]) -> Optional[str]:
    """Return the normalized Safety label, or None when absent."""
    if not isinstance(response, str):
        return None
    match = _SAFETY_LINE.search(response)
    if match is None:
        return None
    return match.group(1).strip().lower()


def _deny_ambiguous() -> SemanticVerdict:
    """Return a deny verdict for an ambiguous guard reply."""
    return SemanticVerdict(
        evaluated=True, allowed=False, reason=REASON_AMBIGUOUS
    )


def _build_pipeline(model_id: str, revision: Optional[str]) -> Any:
    """Create a local-only text-generation pipeline for the guard."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise QwenGuardUnavailableError("guard stack missing") from exc
    try:
        return pipeline(
            "text-generation",
            model=model_id,
            revision=revision,
            local_files_only=True,
            trust_remote_code=False,
        )
    except Exception as exc:
        raise QwenGuardUnavailableError("guard weights missing") from exc


@dataclass(frozen=True)
class GuardCorpusCase:
    """One labelled E2 case: fields plus the expected allow flag."""
    fields: dict[str, str]
    expected_allowed: bool


@dataclass(frozen=True)
class GuardCorpusMetrics:
    """Aggregate E2 metrics over labelled cases (no content)."""
    cases: int
    denied: int
    denied_ambiguous: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def evaluate_guard_corpus(
    cases: Sequence[GuardCorpusCase], evaluator: Judge
) -> GuardCorpusMetrics:
    """Score labelled cases; returns aggregate counts only, no text."""
    tallies = {"denied": 0, "ambiguous": 0, "tp": 0, "fp": 0, "fn": 0}
    items = list(cases)
    for case in items:
        _tally_case(tallies, case, evaluator(case.fields))
    return _to_metrics(len(items), tallies)


def _tally_case(
    tallies: dict[str, int],
    case: GuardCorpusCase,
    verdict: SemanticVerdict,
) -> None:
    """Fold one case verdict into aggregate tallies (no content)."""
    denied = not verdict.allowed
    tallies["denied"] += 1 if denied else 0
    if denied and verdict.reason == REASON_AMBIGUOUS:
        tallies["ambiguous"] += 1
    if denied:
        tallies["tp" if not case.expected_allowed else "fp"] += 1
    elif not case.expected_allowed:
        tallies["fn"] += 1


def _to_metrics(count: int, tallies: dict[str, int]) -> GuardCorpusMetrics:
    """Build aggregate metrics from case tallies (no content)."""
    precision, recall, f1 = _prf(tallies["tp"], tallies["fp"], tallies["fn"])
    return GuardCorpusMetrics(
        cases=count,
        denied=tallies["denied"],
        denied_ambiguous=tallies["ambiguous"],
        true_positives=tallies["tp"],
        false_positives=tallies["fp"],
        false_negatives=tallies["fn"],
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Return precision, recall, and F1 for positive=denied."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    denom = precision + recall
    f1 = 2 * precision * recall / denom if denom else 0.0
    return precision, recall, f1


__all__ = [
    "MAX_INPUT_CHARS", "MAX_NEW_TOKENS", "MODEL_ID", "MODEL_REVISION",
    "GuardCorpusCase", "GuardCorpusMetrics", "QwenGuardUnavailableError",
    "build_guard_request", "evaluate_guard_corpus",
    "load_qwen_guard_evaluator", "make_qwen_guard_evaluator",
    "parse_guard_response", "register_qwen_guard_evaluator",
]
