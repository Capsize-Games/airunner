"""Regression tests for release issue D04.

Proves art generation requests are bounded before any tracker/model
side effect: FastAPI validates the request body into ``GenerationRequest``
before ``create_generation_job``/the route handler ever runs, so a
rejecting field/model validator here is sufficient to guarantee "no
tracker/model side effect" without touching the route handler itself.

Covers dimensions, total pixel count, steps, batch size (num_images),
prompt length, strength, cfg_scale and decoded input-image size:
negative/zero/excessive/non-finite/malformed values are rejected, valid
boundary values pass, and nothing is silently clamped.

No GUI/model launch or network/database access — this only constructs
``GenerationRequest`` instances directly.
"""

from __future__ import annotations

import base64
import json

import pytest
from pydantic import ValidationError

from airunner_services.api.routes import art_contracts
from airunner_services.api.routes.art_contracts import GenerationRequest


def _make(**overrides) -> GenerationRequest:
    payload = {"prompt": "a cat wearing a hat"}
    payload.update(overrides)
    return GenerationRequest(**payload)


def test_defaults_are_accepted() -> None:
    request = _make()
    assert request.width == 1024
    assert request.height == 1024
    assert request.num_images == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("width", 0),
        ("width", -1),
        ("height", 0),
        ("steps", 0),
        ("steps", -5),
        ("num_images", 0),
        ("num_images", -1),
        ("cfg_scale", -1.0),
    ],
)
def test_negative_or_zero_values_are_rejected(field, value) -> None:
    with pytest.raises(ValidationError):
        _make(**{field: value})


def test_cfg_scale_zero_is_accepted() -> None:
    """Z-Image Turbo is documented to work best with guidance_scale=0.0
    (zimage_generation_mixin.py), so 0 must be a valid cfg_scale, unlike
    the other fields above where zero is meaningless."""
    request = _make(cfg_scale=0.0)
    assert request.cfg_scale == 0.0


@pytest.mark.parametrize(
    "field,value",
    [
        ("width", art_contracts._DEFAULT_CAPABILITIES.max_width + 1),
        ("height", art_contracts._DEFAULT_CAPABILITIES.max_height + 1),
        ("steps", art_contracts._max_steps() + 1),
        ("num_images", art_contracts._max_batch_size() + 1),
        ("cfg_scale", 101.0),
    ],
)
def test_excessive_values_are_rejected(field, value) -> None:
    with pytest.raises(ValidationError):
        _make(**{field: value})


def test_boundary_values_are_accepted() -> None:
    request = _make(
        width=art_contracts._DEFAULT_CAPABILITIES.max_width,
        height=art_contracts._DEFAULT_CAPABILITIES.min_height,
        steps=art_contracts._max_steps(),
        num_images=art_contracts._max_batch_size(),
        cfg_scale=100.0,
        strength=1.0,
    )
    assert request.num_images == art_contracts._max_batch_size()


def test_pixel_count_bound_is_enforced_independent_of_dimension_bounds(
    monkeypatch,
) -> None:
    """Not reachable via today's symmetric default profile alone; forcing
    a tighter budget here proves the mechanism itself is correct so it is
    load-bearing the moment an asymmetric per-model profile is wired in."""
    monkeypatch.setattr(art_contracts, "_MAX_PIXELS", 100 * 100)
    with pytest.raises(ValidationError, match="pixel count"):
        _make(width=100, height=101)
    # Still within the tightened budget:
    _make(width=100, height=100)


@pytest.mark.parametrize(
    "field,raw_value",
    [("cfg_scale", "NaN"), ("cfg_scale", "Infinity"), ("strength", "NaN")],
)
def test_nonfinite_values_are_rejected(field, raw_value) -> None:
    # json.loads accepts NaN/Infinity/-Infinity by default (a real gap
    # this fix closes), so exercise it exactly as a client request body
    # would arrive rather than passing a Python float directly.
    payload = json.loads(f'{{"{field}": {raw_value}}}')
    with pytest.raises(ValidationError):
        _make(**payload)


def test_strength_out_of_unit_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _make(strength=1.5)
    with pytest.raises(ValidationError):
        _make(strength=-0.1)


def test_prompt_length_is_bounded() -> None:
    with pytest.raises(ValidationError):
        _make(prompt="x" * (art_contracts._max_prompt_chars() + 1))
    # Boundary value passes:
    _make(prompt="x" * art_contracts._max_prompt_chars())


def test_empty_prompt_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _make(prompt="")


def test_malformed_prompt_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(prompt=12345)


def test_decoded_image_size_is_bounded_not_the_base64_string_length() -> None:
    max_bytes = art_contracts._max_image_bytes()
    oversized = base64.b64encode(b"0" * (max_bytes + 1)).decode()
    with pytest.raises(ValidationError, match="exceeds the maximum"):
        _make(image_b64=oversized)

    within_bound = base64.b64encode(b"0" * max_bytes).decode()
    _make(image_b64=within_bound)


def test_malformed_base64_image_is_rejected() -> None:
    with pytest.raises(ValidationError, match="not valid base64"):
        _make(image_b64="not-valid-base64!!!")


def test_empty_image_b64_is_treated_as_absent() -> None:
    request = _make(image_b64="")
    assert request.image_b64 == ""


def test_downstream_runtime_errors_remain_a_separate_concern() -> None:
    """A structurally valid, in-bounds request must construct cleanly;
    whatever the runtime does with it afterward is not this layer's job."""
    request = _make(model="does-not-exist", version="also-fake")
    assert request.model == "does-not-exist"
