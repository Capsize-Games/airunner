"""Regression tests: vision inputs pass the mandatory image screen.

Gap G1 (Q08): remote image inputs entering the vision path had no
mandatory image check. Every image here is a tiny synthetic
solid-colour PIL image created in-process, and every evaluator is a
synthetic double. No real image, prompt, or policy term is used, no
network is touched, and nothing is written to disk.

Contract under test: ``collect_vision_images`` runs the final batch
through ``check_images_mandatory`` before it can reach the model
processor. Withheld images (flagged or evaluator-unavailable) deny
the request with only the shared generic message; allowed images
pass; image-free requests still fall through to text-only inputs.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from PIL import Image

from airunner_services.content_safety import image_verdict
from airunner_services.content_safety.image_verdict import (
    REASON_FLAGGED,
    REASON_UNAVAILABLE,
)
from airunner_services.content_safety_gate import (
    GENERIC_REJECTION_MESSAGE,
)
from airunner_services.llm.adapters.mixins import (
    generation_vision_inputs as vision_inputs,
)
from airunner_services.llm.adapters.mixins.generation_vision_inputs import (
    VisionImageSafetyDenied,
    collect_vision_images,
)

_FIXTURE_COLOR = (40, 120, 200)


@pytest.fixture(autouse=True)
def _clean_evaluator():
    """Leave no registered evaluator behind for other tests."""
    image_verdict.set_evaluator(None)
    yield
    image_verdict.set_evaluator(None)


def _stub_adapter() -> SimpleNamespace:
    """Return the minimum adapter surface the collector reads."""
    return SimpleNamespace(logger=logging.getLogger("vision-gate-test"))


def _synthetic_image() -> Image.Image:
    """Return one tiny solid-colour in-memory image (never saved)."""
    return Image.new("RGB", (8, 8), _FIXTURE_COLOR)


def test_withheld_vision_input_denied_generically() -> None:
    image_verdict.set_evaluator(lambda imgs: [True] * len(imgs))
    with pytest.raises(VisionImageSafetyDenied) as exc_info:
        collect_vision_images(_stub_adapter(), [_synthetic_image()])
    assert str(exc_info.value) == GENERIC_REJECTION_MESSAGE
    assert exc_info.value.verdict.reasons == [REASON_FLAGGED]


def test_vision_input_denied_when_evaluator_unavailable() -> None:
    image_verdict.set_evaluator(None)
    with pytest.raises(VisionImageSafetyDenied) as exc_info:
        collect_vision_images(_stub_adapter(), [_synthetic_image()])
    assert str(exc_info.value) == GENERIC_REJECTION_MESSAGE
    assert exc_info.value.verdict.reasons == [REASON_UNAVAILABLE]


def test_allowed_vision_input_passes_screen() -> None:
    seen: list[int] = []
    image_verdict.set_evaluator(
        lambda imgs: seen.append(len(imgs)) or [False] * len(imgs)
    )
    images = collect_vision_images(_stub_adapter(), [_synthetic_image()])
    assert len(images) == 1
    assert seen == [1]


def test_imageless_request_skips_screen() -> None:
    image_verdict.set_evaluator(None)
    assert collect_vision_images(_stub_adapter(), []) == []


def test_remote_url_entry_flows_through_screen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A remote-fetched image meets the same gate (fetch doubled)."""
    fetched = _synthetic_image()
    monkeypatch.setattr(
        vision_inputs,
        "image_from_remote_url",
        lambda adapter, url: fetched,
    )
    seen: list[int] = []
    image_verdict.set_evaluator(
        lambda imgs: seen.append(len(imgs)) or [False] * len(imgs)
    )
    images = collect_vision_images(
        _stub_adapter(), ["https://example.invalid/x.png"]
    )
    assert len(images) == 1
    assert seen == [1]


def test_remote_url_entry_denied_when_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vision_inputs,
        "image_from_remote_url",
        lambda adapter, url: _synthetic_image(),
    )
    image_verdict.set_evaluator(lambda imgs: [True] * len(imgs))
    with pytest.raises(VisionImageSafetyDenied) as exc_info:
        collect_vision_images(
            _stub_adapter(), ["https://example.invalid/x.png"]
        )
    assert str(exc_info.value) == GENERIC_REJECTION_MESSAGE
