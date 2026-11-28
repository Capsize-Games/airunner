"""Unit tests for the zimage native generation helper's delegation sequence.

The helper is a pure orchestrator: it validates inputs, prepares conditioning
and latents, runs the denoising loop, releases the transformer, and decodes.
These tests pin the wiring with mocks so refactors cannot silently reorder or
drop a step.
"""

from unittest.mock import MagicMock, call

from airunner_services.art.managers.zimage.native.zimage_native_pipeline_generation_helper import (
    ZImageNativePipelineGenerationHelper,
)


def _make_helper(owner):
    helper = ZImageNativePipelineGenerationHelper.__new__(
        ZImageNativePipelineGenerationHelper
    )
    helper._owner = owner
    sampling = MagicMock()
    sampling.prepare_scheduler_window.return_value = ["t1"]
    sampling.prepare_latents.return_value = "latents"
    sampling.run_denoising_loop.return_value = "clean"
    sampling.decode_output.return_value = "image"
    helper._sampling_helper = sampling
    helper._validate_generation_inputs = MagicMock()
    helper._prepare_transformer_for_denoising = MagicMock()
    helper._prepare_prompt_conditioning = MagicMock(
        return_value=(2, "pe", "ne", "mask")
    )
    helper._release_transformer_after_denoising = MagicMock()
    return helper


def test_generate_runs_full_delegation_sequence():
    owner = MagicMock()
    helper = _make_helper(owner)
    result = helper.generate(
        prompt="a cat",
        negative_prompt="blurry",
        num_inference_steps=4,
        guidance_scale=0.0,
        num_images_per_prompt=1,
        output_type="pil",
    )
    assert result == "image"
    helper._validate_generation_inputs.assert_called_once_with(4, None, 0.8)
    helper._prepare_transformer_for_denoising.assert_called_once()
    helper._prepare_prompt_conditioning.assert_called_once_with(
        "a cat", "blurry", 1
    )
    helper._sampling_helper.prepare_scheduler_window.assert_called_once_with(
        4, False, 0.8
    )
    helper._sampling_helper.prepare_latents.assert_called_once()
    helper._sampling_helper.run_denoising_loop.assert_called_once_with(
        "latents",
        ["t1"],
        "pe",
        "ne",
        "mask",
        0.0,
        2,
        None,
        1,
    )
    helper._release_transformer_after_denoising.assert_called_once()
    helper._sampling_helper.decode_output.assert_called_once_with(
        "clean", "pil"
    )


def test_generate_passes_image_through_as_img2img():
    owner = MagicMock()
    helper = _make_helper(owner)
    helper.generate(prompt="a cat", image="input-image", strength=0.6)
    helper._validate_generation_inputs.assert_called_once_with(4, "input-image", 0.6)
    helper._sampling_helper.prepare_scheduler_window.assert_called_once_with(
        4, True, 0.6
    )
    args, _ = helper._sampling_helper.prepare_latents.call_args
    assert args[0] == "input-image"
    assert args[7] is True
    assert args[8] == 0.6


def test_prepare_generation_inputs_returns_all_pieces():
    owner = MagicMock()
    helper = _make_helper(owner)
    pieces = helper._prepare_generation_inputs(
        "a cat", "blurry", None, 4, 1, 1024, 1024, None, None, 0.8
    )
    assert pieces == ("latents", ["t1"], "pe", "ne", "mask", 2)


def test_prepare_generation_inputs_validates_first():
    owner = MagicMock()
    helper = _make_helper(owner)
    order = []

    def _record(name):
        def _fn(*args, **kwargs):
            order.append(name)
            return MagicMock() if name == "conditioning" else None

        return _fn

    helper._validate_generation_inputs = _record("validate")
    helper._prepare_transformer_for_denoising = _record("transformer")

    def _conditioning(*args, **kwargs):
        order.append("conditioning")
        return (2, "pe", "ne", "mask")

    helper._prepare_prompt_conditioning = _conditioning
    helper._prepare_generation_inputs(
        "a cat", None, None, 4, 1, 1024, 1024, None, None, 0.8
    )
    assert order == ["validate", "transformer", "conditioning"]


def test_generate_propagates_validation_errors():
    import pytest

    owner = MagicMock()
    helper = _make_helper(owner)
    helper._validate_generation_inputs.side_effect = ValueError("bad")
    with pytest.raises(ValueError, match="bad"):
        helper.generate(prompt="a cat")
    helper._sampling_helper.run_denoising_loop.assert_not_called()
