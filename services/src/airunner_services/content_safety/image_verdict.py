"""Mandatory image-evaluator verdict seam (S09).

This module maps one batch of in-memory images to per-image release
verdicts for the MANDATORY output-side evaluator. It is independent of
the optional adult-content filter: there is no enable/disable switch
here, and nothing in this module consults the optional setting.

Evaluator selection status (S07 #2094, approved for #2252); see
:data:`EVALUATOR_SELECTION_STATUS`. The concrete evaluator stays behind
the injected :data:`ImageEvaluator` seam; the approved Falconsai
adapter (:mod:`airunner_services.content_safety.falconsai`) is
registered on it, and the SD safety checker boolean path is
superseded for the mandatory slot.

Fail-closed mapping (no unchecked fallback):

* missing evaluator -> every image withheld (``image_unavailable``)
* evaluator raised -> every image withheld (``image_error``)
* result length differs from the batch -> withheld (``image_cardinality``)
* ``True`` item -> that image withheld (``image_flagged``)
* ``False`` item -> that image released (``image_allowed``)
* ``None`` or any other item -> withheld (``image_uncertain``)

Images are opaque here: they are never inspected, mutated, logged, or
written anywhere. Callers keep the originals privately in memory until
the verdict; no automatic export happens in this module.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# S07 selection is SELECTED (owner-approved for #2252): the approved
# Falconsai adapter is registered behind the seam; the SD safety
# checker boolean path is superseded for the mandatory slot.
EVALUATOR_SELECTION_STATUS = (
    "SELECTED (S07 #2094, approved for #2252): Falconsai "
    "nsfw_image_detection via the content_safety.falconsai adapter; "
    "the SD safety checker boolean path is superseded here"
)

# Generic, content-free reason codes. These never contain image data.
REASON_ALLOWED = "image_allowed"
REASON_FLAGGED = "image_flagged"
REASON_UNAVAILABLE = "image_unavailable"
REASON_ERROR = "image_error"
REASON_CARDINALITY = "image_cardinality"
REASON_UNCERTAIN = "image_uncertain"

# One evaluator call reviews a whole batch. Each returned item must be a
# built-in bool (True = withhold, False = release) or None (uncertain,
# withheld). Adapters normalize model-specific outputs to this contract.
ImageEvaluator = Callable[[Sequence[Any]], Sequence[Any]]

_evaluator: Optional[ImageEvaluator] = None


@dataclass(frozen=True)
class ImageVerdict:
    """Outcome for one image. ``reason`` is always a generic code."""

    evaluated: bool
    allowed: bool
    reason: str

    @classmethod
    def allow(cls, reason: str = REASON_ALLOWED) -> "ImageVerdict":
        """Return a release verdict with a generic ``reason``."""
        return cls(evaluated=True, allowed=True, reason=reason)

    @classmethod
    def withhold(
        cls, reason: str, *, evaluated: bool = True
    ) -> "ImageVerdict":
        """Return a withholding verdict with a generic ``reason``."""
        return cls(evaluated=evaluated, allowed=False, reason=reason)


@dataclass(frozen=True)
class ImageBatchVerdict:
    """Per-image verdicts for one batch, in input order."""

    verdicts: tuple[ImageVerdict, ...]

    @property
    def all_allowed(self) -> bool:
        """Return ``True`` only when every image may be released."""
        return all(verdict.allowed for verdict in self.verdicts)

    @property
    def withheld(self) -> list[bool]:
        """Return per-image withhold flags in input order."""
        return [not verdict.allowed for verdict in self.verdicts]

    @property
    def reasons(self) -> list[str]:
        """Return per-image generic reason codes in input order."""
        return [verdict.reason for verdict in self.verdicts]


def set_evaluator(evaluator: Optional[ImageEvaluator]) -> None:
    """Register (or clear with ``None``) the mandatory evaluator."""
    global _evaluator
    _evaluator = evaluator


def get_evaluator() -> Optional[ImageEvaluator]:
    """Return the registered evaluator, or ``None`` when unset."""
    return _evaluator


def _withhold_all(count: int, reason: str) -> ImageBatchVerdict:
    """Return a batch verdict withholding ``count`` images."""
    evaluated = reason != REASON_UNAVAILABLE
    return ImageBatchVerdict(
        verdicts=tuple(
            ImageVerdict.withhold(reason, evaluated=evaluated)
            for _ in range(count)
        )
    )


def evaluate_image_batch(
    images: Sequence[Any],
    evaluator: Optional[ImageEvaluator],
) -> ImageBatchVerdict:
    """Map one batch to per-image verdicts; unknown means withheld.

    ``images`` are passed to ``evaluator`` untouched and never logged.
    Only counts and generic reason codes leave this function.
    """
    batch = list(images)
    if evaluator is None:
        logger.warning(
            "Mandatory image evaluator unavailable; withholding batch "
            "(images=%d, reason=%s)",
            len(batch),
            REASON_UNAVAILABLE,
        )
        return _withhold_all(len(batch), REASON_UNAVAILABLE)
    try:
        result = evaluator(batch)
    except Exception as exc:
        # Never include the exception text: it could echo image data.
        logger.warning(
            "Mandatory image evaluator error (%s); withholding batch "
            "(images=%d, reason=%s)",
            type(exc).__name__,
            len(batch),
            REASON_ERROR,
        )
        return _withhold_all(len(batch), REASON_ERROR)
    if isinstance(result, (str, bytes)):
        outcomes: Sequence[Any] | None = None
    else:
        try:
            outcomes = list(result)
        except TypeError:
            outcomes = None
    if outcomes is None or len(outcomes) != len(batch):
        logger.warning(
            "Mandatory image evaluator returned an unusable result; "
            "withholding batch (images=%d, reason=%s)",
            len(batch),
            REASON_CARDINALITY,
        )
        return _withhold_all(len(batch), REASON_CARDINALITY)
    verdicts = tuple(_map_outcome(outcome) for outcome in outcomes)
    verdict = ImageBatchVerdict(verdicts=verdicts)
    if not verdict.all_allowed:
        withheld = sum(1 for flag in verdict.withheld if flag)
        logger.info(
            "Mandatory image evaluator withheld images "
            "(withheld=%d, images=%d)",
            withheld,
            len(batch),
        )
    return verdict


def _map_outcome(outcome: Any) -> ImageVerdict:
    """Map one evaluator item; only an explicit ``False`` releases."""
    if outcome is True:
        return ImageVerdict.withhold(REASON_FLAGGED)
    if outcome is False:
        return ImageVerdict.allow(REASON_ALLOWED)
    return ImageVerdict.withhold(REASON_UNCERTAIN)


def evaluate_images(images: Sequence[Any]) -> ImageBatchVerdict:
    """Evaluate ``images`` with the registered evaluator (fail closed).

    With no evaluator registered every image is withheld as unavailable;
    the mandatory path has no pass-through mode.
    """
    return evaluate_image_batch(images, get_evaluator())


__all__ = [
    "EVALUATOR_SELECTION_STATUS",
    "REASON_ALLOWED",
    "REASON_CARDINALITY",
    "REASON_ERROR",
    "REASON_FLAGGED",
    "REASON_UNAVAILABLE",
    "REASON_UNCERTAIN",
    "ImageBatchVerdict",
    "ImageEvaluator",
    "ImageVerdict",
    "evaluate_image_batch",
    "evaluate_images",
    "get_evaluator",
    "set_evaluator",
]
