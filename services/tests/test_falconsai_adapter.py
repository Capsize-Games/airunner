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

import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from PIL import Image

from airunner_services.art.utils.nsfw_checker import check_images_mandatory
from airunner_services.content_safety import falconsai, image_verdict
from airunner_services.content_safety.falconsai import (
    ImageCorpusCase,
    evaluate_image_corpus,
)
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


class _StubImageClassifier:
    def __init__(self, results: list) -> None:
        self.calls: list = []
        self._results = list(results)

    def __call__(self, images):
        self.calls.append(list(images))
        return list(self._results)


class _StubPipelines:
    def __init__(self, results: list) -> None:
        self.kwargs: dict = {}
        self.classifier = _StubImageClassifier(results)

    def __call__(self, task, **kwargs):
        self.kwargs = {"task": task, **kwargs}
        return self.classifier


def _install_stub_transformers(
    monkeypatch: pytest.MonkeyPatch, results: list
) -> _StubPipelines:
    fake = ModuleType("transformers")
    pipelines = _StubPipelines(results)
    setattr(fake, "pipeline", pipelines)
    monkeypatch.setitem(sys.modules, "transformers", fake)
    return pipelines


def test_loader_is_local_only_and_maps_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipelines = _install_stub_transformers(
        monkeypatch, [[{"label": "nsfw", "score": 0.95}]]
    )
    evaluator = falconsai.load_falconsai_evaluator()
    assert pipelines.kwargs["task"] == "image-classification"
    assert pipelines.kwargs["model"] == falconsai.MODEL_ID
    assert pipelines.kwargs["revision"] is None
    assert pipelines.kwargs["local_files_only"] is True
    assert pipelines.kwargs["trust_remote_code"] is False
    assert list(evaluator(["marker"])) == [True]
    assert pipelines.classifier.calls == [["marker"]]


def test_loader_failure_and_missing_stack_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = ModuleType("transformers")

    def _boom(task, **kwargs):
        raise OSError("no cached weights")

    setattr(fake, "pipeline", _boom)
    monkeypatch.setitem(sys.modules, "transformers", fake)
    with pytest.raises(falconsai.FalconsaiUnavailableError):
        falconsai.load_falconsai_evaluator()
    monkeypatch.setitem(sys.modules, "transformers", None)
    with pytest.raises(falconsai.FalconsaiUnavailableError):
        falconsai.load_falconsai_evaluator()


def test_register_installs_evaluator_on_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_stub_transformers(
        monkeypatch, [[{"label": "normal", "score": 0.9}]]
    )
    evaluator = falconsai.register_falconsai_evaluator()
    assert image_verdict.get_evaluator() is evaluator


def test_image_corpus_metrics_count_only_aggregates() -> None:
    table = {"tp": True, "fp": True, "fn": False, "tn": False, "amb": None}

    def _scripted(images):
        return [table[image] for image in images]

    cases = [
        ImageCorpusCase("tp", True),
        ImageCorpusCase("fp", False),
        ImageCorpusCase("fn", True),
        ImageCorpusCase("tn", False),
        ImageCorpusCase("amb", True),
    ]
    metrics = evaluate_image_corpus(cases, _scripted)
    assert metrics.cases == 5
    assert metrics.withheld == 3
    assert metrics.uncertain_withheld == 1
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.true_negatives == 1
    assert metrics.recall == pytest.approx(2 / 3)
    assert metrics.false_positive_rate == pytest.approx(1 / 2)


def test_image_corpus_rejects_broken_cardinality() -> None:
    cases = [ImageCorpusCase("a", True)]
    with pytest.raises(ValueError, match="cardinality"):
        evaluate_image_corpus(cases, lambda images: [])


def test_adapter_import_loads_no_model_stack() -> None:
    src = _REPO_ROOT / "services" / "src"
    code = (
        "import sys; "
        f"sys.path.insert(0, r'{src}'); "
        "import airunner_services.content_safety.falconsai as m; "
        "assert 'torch' not in sys.modules; "
        "assert 'transformers' not in sys.modules; "
        "assert m.MODEL_ID.startswith('Falconsai/')"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )


@pytest.mark.integration
def test_real_falconsai_classifies_synthetic_image() -> None:
    """Real-model smoke: one shaped outcome only, no efficacy claim."""
    pytest.importorskip("transformers")
    try:
        evaluator = falconsai.load_falconsai_evaluator()
    except falconsai.FalconsaiUnavailableError:
        pytest.skip("Falconsai weights are not cached locally")
    image = Image.new("RGB", (32, 32), _ORIGINAL_COLOR)
    outcomes = list(evaluator([image]))
    assert len(outcomes) == 1
    assert outcomes[0] in (True, False, None)
