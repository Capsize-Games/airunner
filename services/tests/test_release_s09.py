"""Release regression tests for S09 (mandatory image evaluator seam).

Every image here is a tiny synthetic solid-colour PIL image created
in-process, and every evaluator/checker model is a synthetic double. No
real image, prompt, or policy term is used, and nothing is written to
disk: originals stay privately in memory until the verdict.

The contract under test: the mandatory evaluator runs independently of
the optional adult-content filter (no switch can disable it), batch
cardinality is validated, and missing models, errors, and uncertainty
all withhold instead of releasing unchecked images.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any

import pytest
from PIL import Image

from airunner_services.art.utils.nsfw_checker import (
    check_and_mark_nsfw_images,
    check_images_mandatory,
    make_sd_safety_checker_evaluator,
)
from airunner_services.content_safety import image_verdict
from airunner_services.content_safety.image_verdict import (
    REASON_ALLOWED,
    REASON_CARDINALITY,
    REASON_ERROR,
    REASON_FLAGGED,
    REASON_UNAVAILABLE,
    REASON_UNCERTAIN,
    evaluate_image_batch,
)

_ORIGINAL_COLOR = (40, 120, 200)
_SENTINEL = "synthetic-sentinel-payload-9c1e"


@pytest.fixture(autouse=True)
def _clean_evaluator():
    """Leave no registered evaluator behind for other tests."""
    image_verdict.set_evaluator(None)
    yield
    image_verdict.set_evaluator(None)


def _synthetic_images(count: int = 2, size=(8, 8)):
    """Return tiny solid-colour in-memory images (never saved)."""
    return [Image.new("RGB", size, _ORIGINAL_COLOR) for _ in range(count)]


def _is_withheld_copy(output: Image.Image, original: Image.Image) -> bool:
    """True when output is a fresh image holding no original pixels.

    The marker always blackens first, then centers its label; label
    glyphs may cover any single probe pixel on tiny fixtures, so scan
    the whole image instead of sampling one corner.
    """
    if output is original:
        return False
    pixels = output.convert("RGB")
    width, height = pixels.size
    return all(
        pixels.getpixel((x, y)) != _ORIGINAL_COLOR
        for y in range(height)
        for x in range(width)
    )


def _is_original(image: Image.Image) -> bool:
    """True when the image still holds the untouched fixture colour."""
    return image.convert("RGB").getpixel((0, 0)) == _ORIGINAL_COLOR


class _FakePixels:
    """Stand-in for tensor input with a chainable ``.to()``."""

    def __init__(self) -> None:
        self.device: Any = None

    def to(self, device: str) -> "_FakePixels":
        self.device = device
        return self


class _FakeExtractorOutput:
    def __init__(self) -> None:
        self.pixel_values = _FakePixels()

    def to(self, device: str) -> "_FakeExtractorOutput":
        return self


class _FakeExtractor:
    """Feature-extractor double recording the incumbent call shape."""

    def __init__(self) -> None:
        self.calls: list[tuple[list, Any]] = []

    def __call__(self, images, return_tensors=None):
        self.calls.append((list(images), return_tensors))
        return _FakeExtractorOutput()


class _FakeChecker:
    """Safety-checker double returning scripted per-image flags."""

    def __init__(self, flags) -> None:
        self._flags = list(flags)
        self.calls: list[tuple[Any, Any]] = []

    def __call__(self, images=None, clip_input=None):
        self.calls.append((images, clip_input))
        return None, list(self._flags)


class _RaisingEvaluator:
    def __call__(self, images):
        raise RuntimeError(_SENTINEL)


class _ListLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@contextmanager
def _captured_logger(name: str):
    logger = logging.getLogger(name)
    handler = _ListLogHandler()
    previous_level = logger.level
    previous_disabled = logger.disabled
    previous_global = logging.root.manager.disable
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.disabled = False
    logging.disable(logging.NOTSET)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled
        logging.disable(previous_global)


# --------------------------------------------------------------------------
# Verdict mapping: every reason via doubles
# --------------------------------------------------------------------------


def test_all_false_releases_batch() -> None:
    verdict = evaluate_image_batch(["a", "b"], lambda imgs: [False, False])
    assert verdict.all_allowed is True
    assert verdict.withheld == [False, False]
    assert verdict.reasons == [REASON_ALLOWED] * 2


def test_true_flag_withholds_only_that_image() -> None:
    verdict = evaluate_image_batch(["a", "b"], lambda imgs: [False, True])
    assert verdict.all_allowed is False
    assert verdict.withheld == [False, True]
    assert verdict.reasons == [REASON_ALLOWED, REASON_FLAGGED]


def test_missing_evaluator_withholds_as_unavailable() -> None:
    verdict = evaluate_image_batch(["a", "b"], None)
    assert verdict.withheld == [True, True]
    assert verdict.reasons == [REASON_UNAVAILABLE] * 2
    assert all(not item.evaluated for item in verdict.verdicts)


def test_raising_evaluator_withholds_as_error() -> None:
    def _boom(images):
        raise RuntimeError("synthetic evaluator failure")

    verdict = evaluate_image_batch(["a", "b"], _boom)
    assert verdict.withheld == [True, True]
    assert verdict.reasons == [REASON_ERROR] * 2


@pytest.mark.parametrize(
    "result", [[False], [False, False, False], [], "ab", 7, None]
)
def test_cardinality_mismatch_withholds_batch(result) -> None:
    verdict = evaluate_image_batch(["a", "b"], lambda imgs: result)
    assert verdict.withheld == [True, True]
    assert verdict.reasons == [REASON_CARDINALITY] * 2


@pytest.mark.parametrize("outcome", [None, "maybe", 0.5, 1, object()])
def test_uncertain_outcome_withholds_image(outcome) -> None:
    verdict = evaluate_image_batch(["a"], lambda imgs: [outcome])
    assert verdict.withheld == [True]
    assert verdict.reasons == [REASON_UNCERTAIN]


def test_error_log_omits_exception_message() -> None:
    with _captured_logger(
        "airunner_services.content_safety.image_verdict"
    ) as handler:
        verdict = evaluate_image_batch(["a"], _RaisingEvaluator())
    assert verdict.reasons == [REASON_ERROR]
    assert _SENTINEL not in " ".join(handler.messages)


def test_selection_status_flags_pending_approval() -> None:
    assert "PENDING" in image_verdict.EVALUATOR_SELECTION_STATUS
    assert "S07" in image_verdict.EVALUATOR_SELECTION_STATUS


# --------------------------------------------------------------------------
# Mandatory entry point: independence from the optional filter
# --------------------------------------------------------------------------


def test_optional_off_never_disables_mandatory_unavailable() -> None:
    images = _synthetic_images()
    # Optional monitor mode passes through ...
    passed, optional_flags = check_and_mark_nsfw_images(
        images, None, None, fail_closed=False
    )
    assert passed is images
    assert optional_flags == [False] * len(images)
    # ... while the mandatory path withholds the same batch.
    outputs, withheld, batch = check_images_mandatory(images)
    assert withheld == [True] * len(images)
    assert batch.reasons == [REASON_UNAVAILABLE] * len(images)
    assert all(
        _is_withheld_copy(out, img) for out, img in zip(outputs, images)
    )
    assert all(_is_original(img) for img in images)


def test_optional_off_never_disables_mandatory_flagged() -> None:
    images = _synthetic_images()
    outputs, withheld, batch = check_images_mandatory(
        images, evaluator=lambda imgs: [True, False]
    )
    assert withheld == [True, False]
    assert batch.reasons == [REASON_FLAGGED, REASON_ALLOWED]
    assert _is_withheld_copy(outputs[0], images[0])
    assert outputs[1] is images[1]
    assert all(_is_original(img) for img in images)


def test_registered_evaluator_used_without_models() -> None:
    image_verdict.set_evaluator(lambda imgs: [False, False])
    assert image_verdict.get_evaluator() is not None
    images = _synthetic_images()
    outputs, withheld, batch = check_images_mandatory(images)
    assert batch.all_allowed is True
    assert withheld == [False, False]
    assert outputs == images


def test_explicit_evaluator_wins_over_registered() -> None:
    image_verdict.set_evaluator(lambda imgs: [False])
    images = _synthetic_images(1)
    _, withheld, batch = check_images_mandatory(
        images, evaluator=lambda imgs: [True]
    )
    assert withheld == [True]
    assert batch.reasons == [REASON_FLAGGED]


def test_raising_registered_evaluator_withholds() -> None:
    image_verdict.set_evaluator(_RaisingEvaluator())
    images = _synthetic_images()
    outputs, withheld, batch = check_images_mandatory(images)
    assert withheld == [True] * len(images)
    assert batch.reasons == [REASON_ERROR] * len(images)
    assert all(
        _is_withheld_copy(out, img) for out, img in zip(outputs, images)
    )


# --------------------------------------------------------------------------
# Incumbent SD safety checker adapter
# --------------------------------------------------------------------------


def test_adapter_reproduces_incumbent_call_shape() -> None:
    extractor, checker = _FakeExtractor(), _FakeChecker([False, True])
    evaluator = make_sd_safety_checker_evaluator(
        extractor, checker, device="cpu"
    )
    images = _synthetic_images()
    flags = evaluator(images)
    assert flags == [False, True]
    assert all(type(flag) is bool for flag in flags)
    assert extractor.calls == [(images, "pt")]
    assert len(checker.calls) == 1
    checked, clip_input = checker.calls[0]
    assert len(checked) == len(images)
    assert clip_input.device == "cpu"


def test_mandatory_with_incumbent_models_end_to_end() -> None:
    extractor, checker = _FakeExtractor(), _FakeChecker([False, True])
    images = _synthetic_images()
    outputs, withheld, batch = check_images_mandatory(
        images, extractor, checker, device="cpu"
    )
    assert withheld == [False, True]
    assert batch.reasons == [REASON_ALLOWED, REASON_FLAGGED]
    assert outputs[0] is images[0]
    assert _is_withheld_copy(outputs[1], images[1])
    assert all(_is_original(img) for img in images)


def test_mandatory_with_single_model_still_unavailable() -> None:
    images = _synthetic_images()
    _, withheld, batch = check_images_mandatory(images, _FakeExtractor(), None)
    assert withheld == [True] * len(images)
    assert batch.reasons == [REASON_UNAVAILABLE] * len(images)
