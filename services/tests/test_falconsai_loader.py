"""Loader tests for the mandatory Falconsai image evaluator (#2252).

Local-only loader behavior via a stubbed transformers module,
seam registration, the aggregate E1 measurement hook, and the
no-model-stack import check. One marked integration test exercises
real weights when cached and skips otherwise; it makes no efficacy
claim (Q08).

Every image is a tiny synthetic solid-colour PIL image (or a plain
marker where pixels never matter). No model is downloaded and no
network is used outside the skipped-unless-cached integration test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from PIL import Image

from airunner_services.content_safety import falconsai, image_verdict
from airunner_services.content_safety.falconsai import (
    ImageCorpusCase,
    evaluate_image_corpus,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORIGINAL_COLOR = (40, 120, 200)


@pytest.fixture(autouse=True)
def _clean_evaluator():
    """Leave no registered evaluator behind for other tests."""
    image_verdict.set_evaluator(None)
    yield
    image_verdict.set_evaluator(None)


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
