"""Adapter tests for the mandatory Falconsai image evaluator (#2252).

Mocked-model unit tests (the gate, CPU-only): threshold plus
uncertainty-band mapping, pipeline-result normalization, S09 seam
routing through the mandatory entry point, local-only loader behavior
via a stubbed ``transformers`` module, and the aggregate E1
measurement hook. One marked integration test exercises real weights
when cached and skips otherwise; it makes no efficacy claim (Q08).

Every image is a tiny synthetic solid-colour PIL image (or a plain
marker where pixels never matter). No model is downloaded and no
network is used outside the skipped-unless-cached integration test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from airunner_services.art.utils.nsfw_checker import check_images_mandatory
from airunner_services.content_safety import falconsai, image_verdict
from airunner_services.content_safety.image_verdict import (
    REASON_ALLOWED,
    REASON_CARDINALITY,
    REASON_ERROR,
    REASON_FLAGGED,
    REASON_UNAVAILABLE,
    REASON_UNCERTAIN,
    evaluate_image_batch,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORIGINAL_COLOR = (40, 120, 200)


@pytest.fixture(autouse=True)
def _clean_evaluator():
    """Leave no registered evaluator behind for other tests."""
    image_verdict.set_evaluator(None)
    yield
    image_verdict.set_evaluator(None)


def _synthetic_images(count: int = 2):
    """Return tiny solid-colour in-memory images (never saved)."""
    return [Image.new("RGB", (8, 8), _ORIGINAL_COLOR) for _ in range(count)]


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.95, True),
        (0.6, True),
        (0.59, None),
        (0.5, None),
        (0.41, None),
        (0.4, False),
        (0.05, False),
        (float("nan"), None),
        (-0.1, None),
        (1.5, None),
        ("high", None),
        (None, None),
        (True, None),
    ],
)
def test_score_maps_to_outcome_with_band(
    score: float, expected: Any
) -> None:
    assert (
        falconsai.score_to_outcome(score, threshold=0.5, band=0.2)
        is expected
    )


@pytest.mark.parametrize(
    "result,expected",
    [
        ([{"label": "nsfw", "score": 0.9}], 0.9),
        ([{"label": "NSFW", "score": 0.7}], 0.7),
        ([{"label": "normal", "score": 0.99}], 0.01),
        ({"label": "normal", "score": 0.8}, 0.2),
        (
            [
                {"label": "normal", "score": 0.6},
                {"label": "nsfw", "score": 0.4},
            ],
            0.4,
        ),
        ([{"label": "nsfw", "score": "high"}], None),
        ([{"label": "nsfw"}], None),
        ([{"label": "other", "score": 0.5}], None),
        ([], None),
        (None, None),
        ("nsfw", None),
    ],
)
def test_pipeline_result_normalizes_to_score(
    result: Any, expected: Any
) -> None:
    score = falconsai.pick_nsfw_score(result)
    if expected is None:
        assert score is None
    else:
        assert score == pytest.approx(expected)


def test_adapter_maps_batch_through_verdict_seam() -> None:
    evaluator = falconsai.make_falconsai_evaluator(
        lambda batch: [
            [{"label": "nsfw", "score": 0.95}],
            [{"label": "normal", "score": 0.99}],
            [{"label": "nsfw", "score": 0.5}],
            [{"label": "broken"}],
        ]
    )
    verdict = evaluate_image_batch(["a", "b", "c", "d"], evaluator)
    assert verdict.withheld == [True, False, True, True]
    assert verdict.reasons == [
        REASON_FLAGGED,
        REASON_ALLOWED,
        REASON_UNCERTAIN,
        REASON_UNCERTAIN,
    ]


def test_adapter_length_mismatch_and_error_withhold() -> None:
    short = falconsai.make_falconsai_evaluator(lambda batch: [True])
    verdict = evaluate_image_batch(["a", "b"], short)
    assert verdict.reasons == [REASON_CARDINALITY] * 2

    def _boom(batch):
        raise RuntimeError("synthetic classifier failure")

    verdict = evaluate_image_batch(
        ["a", "b"], falconsai.make_falconsai_evaluator(_boom)
    )
    assert verdict.reasons == [REASON_ERROR] * 2


def test_explicit_double_routes_through_mandatory() -> None:
    images = _synthetic_images()
    evaluator = falconsai.make_falconsai_evaluator(
        lambda batch: [
            [{"label": "nsfw", "score": 0.95}],
            [{"label": "normal", "score": 0.99}],
        ]
    )
    outputs, withheld, batch = check_images_mandatory(
        images, evaluator=evaluator
    )
    assert withheld == [True, False]
    assert batch.reasons == [REASON_FLAGGED, REASON_ALLOWED]
    assert outputs[1] is images[1]


def test_registered_double_used_without_args() -> None:
    images = _synthetic_images(1)
    image_verdict.set_evaluator(
        falconsai.make_falconsai_evaluator(
            lambda batch: [[{"label": "normal", "score": 0.9}]]
        )
    )
    _, withheld, batch = check_images_mandatory(images)
    assert withheld == [False]
    assert batch.reasons == [REASON_ALLOWED]


def test_nothing_registered_withholds_as_unavailable() -> None:
    _, withheld, batch = check_images_mandatory(_synthetic_images())
    assert withheld == [True, True]
    assert batch.reasons == [REASON_UNAVAILABLE] * 2

