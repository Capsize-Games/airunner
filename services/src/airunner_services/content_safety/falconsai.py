"""Mandatory image adapter: Falconsai nsfw_image_detection (S09, #2252).

Approved narrow output-side evaluator (S07 section 2) through the
``image-classification`` pipeline. Scores at or above threshold plus
half the band withhold, at or below threshold minus half the band
release; band-interior, malformed, and missing scores yield None
(withheld as uncertain). The default operating point is PROVISIONAL
until the specialist calibrates E1.

:func:`load_falconsai_evaluator` builds its pipeline with
``local_files_only=True``. No image data is ever logged or
returned; only outcomes, counts, and generic reasons leave here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from airunner_services.content_safety.image_verdict import (
    ImageEvaluator,
    set_evaluator,
)

logger = logging.getLogger(__name__)

# Approved narrow image evaluator (S07 section 2). P11 records the
# immutable SHA pin for MODEL_REVISION once weights are provisioned;
# until then the loader resolves the cached default revision offline.
MODEL_ID = "Falconsai/nsfw_image_detection"
MODEL_REVISION: Optional[str] = None

# PROVISIONAL operating point: no vendor point is published, so the
# specialist calibrates on neutral sets first, then measures E1.
DEFAULT_THRESHOLD = 0.5
DEFAULT_BAND = 0.2

LABEL_NSFW = "nsfw"
LABEL_NORMAL = "normal"


class FalconsaiUnavailableError(RuntimeError):
    """Raised when the image guard cannot load from the local cache."""


def score_to_outcome(
    score: float, *, threshold: float, band: float
) -> Optional[bool]:
    """Map an NSFW probability to withhold/release/uncertain."""
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return None
    value = float(score)
    if value != value or value < 0.0 or value > 1.0:
        return None
    half = band / 2.0
    if value >= threshold + half:
        return True
    if value <= threshold - half:
        return False
    return None


def pick_nsfw_score(result: Any) -> Optional[float]:
    """Extract the NSFW probability from one pipeline result."""
    entries = result if isinstance(result, list) else [result]
    fallback: Optional[float] = None
    for entry in entries:
        split = _split_entry(entry)
        if split is None:
            continue
        label, score = split
        if label == LABEL_NSFW:
            return score
        if label == LABEL_NORMAL and fallback is None:
            fallback = 1.0 - score
    return fallback


def make_falconsai_evaluator(
    classify: Callable[[Sequence[Any]], Sequence[Any]],
    *, threshold: float = DEFAULT_THRESHOLD, band: float = DEFAULT_BAND,
) -> ImageEvaluator:
    """Adapt a batch classifier to the S09 evaluator seam."""
    def _evaluate(images: Sequence[Any]) -> list[Optional[bool]]:
        return [
            _map_result(item, threshold, band)
            for item in classify(list(images))
        ]

    return _evaluate


def load_falconsai_evaluator(
    *, model_id: str = MODEL_ID, revision: Optional[str] = MODEL_REVISION,
    threshold: float = DEFAULT_THRESHOLD, band: float = DEFAULT_BAND,
) -> ImageEvaluator:
    """Load the image guard from the local cache; never downloads."""
    classifier = _build_pipeline(model_id, revision)

    def _classify(images: Sequence[Any]) -> Sequence[Any]:
        return classifier(list(images))

    return make_falconsai_evaluator(
        _classify, threshold=threshold, band=band
    )


def register_falconsai_evaluator(
    *, model_id: str = MODEL_ID, revision: Optional[str] = MODEL_REVISION,
    threshold: float = DEFAULT_THRESHOLD, band: float = DEFAULT_BAND,
) -> ImageEvaluator:
    """Load the image guard and register it on the S09 seam."""
    evaluator = load_falconsai_evaluator(
        model_id=model_id, revision=revision,
        threshold=threshold, band=band,
    )
    set_evaluator(evaluator)
    logger.info("Registered the mandatory image evaluator")
    return evaluator


def _split_entry(entry: Any) -> Optional[tuple[str, float]]:
    """Normalize one label entry, or None when unusable."""
    if not isinstance(entry, dict):
        return None
    label, score = entry.get("label"), entry.get("score")
    if not isinstance(label, str) or not _is_number(score):
        return None
    return label.strip().lower(), float(score)


def _is_number(value: Any) -> bool:
    """Return True for real int/float values, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _map_result(
    result: Any, threshold: float, band: float
) -> Optional[bool]:
    """Map one pipeline result to withhold/release/uncertain."""
    score = pick_nsfw_score(result)
    if score is None:
        return None
    return score_to_outcome(score, threshold=threshold, band=band)


def _build_pipeline(model_id: str, revision: Optional[str]) -> Any:
    """Create a local-only image-classification pipeline."""
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise FalconsaiUnavailableError("image stack missing") from exc
    try:
        return pipeline(
            "image-classification",
            model=model_id,
            revision=revision,
            local_files_only=True,
            trust_remote_code=False,
        )
    except Exception as exc:
        raise FalconsaiUnavailableError("image weights missing") from exc


@dataclass(frozen=True)
class ImageCorpusCase:
    """One labelled E1 case: an image plus expected withhold flag."""
    image: Any
    expected_withheld: bool


@dataclass(frozen=True)
class ImageCorpusMetrics:
    """Aggregate E1 metrics over labelled images (never pixels)."""
    cases: int
    withheld: int
    uncertain_withheld: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    recall: float
    false_positive_rate: float


def evaluate_image_corpus(
    cases: Sequence[ImageCorpusCase], evaluator: ImageEvaluator
) -> ImageCorpusMetrics:
    """Score labelled images; returns aggregate counts, never pixels."""
    items = list(cases)
    outcomes = list(evaluator([case.image for case in items]))
    if len(outcomes) != len(items):
        raise ValueError("evaluator broke batch cardinality")
    tallies = {"w": 0, "u": 0, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for case, outcome in zip(items, outcomes):
        _tally_image(tallies, case, outcome)
    return _to_image_metrics(len(items), tallies)


def _tally_image(
    tallies: dict[str, int], case: ImageCorpusCase, outcome: Any
) -> None:
    """Fold one image outcome into aggregate tallies (no pixels)."""
    withheld = outcome is not False
    tallies["w"] += 1 if withheld else 0
    if outcome is None:
        tallies["u"] += 1
    if withheld:
        tallies["tp" if case.expected_withheld else "fp"] += 1
    elif case.expected_withheld:
        tallies["fn"] += 1
    else:
        tallies["tn"] += 1


def _to_image_metrics(
    count: int, tallies: dict[str, int]
) -> ImageCorpusMetrics:
    """Build aggregate E1 metrics from tallies (no pixels)."""
    positives = tallies["tp"] + tallies["fn"]
    negatives = tallies["fp"] + tallies["tn"]
    recall = tallies["tp"] / positives if positives else 0.0
    fpr = tallies["fp"] / negatives if negatives else 0.0
    return ImageCorpusMetrics(
        cases=count,
        withheld=tallies["w"],
        uncertain_withheld=tallies["u"],
        true_positives=tallies["tp"],
        false_positives=tallies["fp"],
        false_negatives=tallies["fn"],
        true_negatives=tallies["tn"],
        recall=recall,
        false_positive_rate=fpr,
    )


__all__ = [
    "DEFAULT_BAND", "DEFAULT_THRESHOLD", "LABEL_NORMAL", "LABEL_NSFW",
    "MODEL_ID", "MODEL_REVISION", "FalconsaiUnavailableError",
    "ImageCorpusCase", "ImageCorpusMetrics", "evaluate_image_corpus",
    "load_falconsai_evaluator", "make_falconsai_evaluator",
    "pick_nsfw_score", "register_falconsai_evaluator", "score_to_outcome",
]
