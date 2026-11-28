"""Unit tests for the zimage latents-preparation helpers.

The img2img path and batch-fit helper were extracted to keep
prepare_latents within the long-function threshold. These tests pin the
dispatch, the batch repeat/trim math, and the noise-blend wiring.
"""

from unittest.mock import MagicMock

import pytest
import torch

from airunner_services.art.managers.zimage.native.zimage_native_pipeline_sampling_helper import (
    ZImageNativePipelineSamplingHelper,
)


def _make_helper(owner):
    helper = ZImageNativePipelineSamplingHelper.__new__(
        ZImageNativePipelineSamplingHelper
    )
    helper._owner = owner
    return helper


def test_prepare_latents_dispatches_text2img():
    owner = MagicMock()
    helper = _make_helper(owner)
    helper._prepare_text2img_latents = MagicMock(return_value="txt")
    result = helper.prepare_latents(None, 1024, 1024, 1, None, None, torch.tensor([0]), False, 0.8)
    assert result == "txt"
    helper._prepare_text2img_latents.assert_called_once()


def test_prepare_latents_dispatches_img2img():
    owner = MagicMock()
    helper = _make_helper(owner)
    helper._prepare_img2img_latents = MagicMock(return_value="img")
    result = helper.prepare_latents("in", 512, 512, 1, None, None, torch.tensor([0]), True, 0.8)
    assert result == "img"
    helper._prepare_img2img_latents.assert_called_once()


def test_fit_latent_batch_repeats_to_batch():
    helper = _make_helper(MagicMock())
    latents = torch.zeros(2, 3)
    out = helper._fit_latent_batch(latents, 4)
    assert out.shape == (4, 3)


def test_fit_latent_batch_trims_to_batch():
    helper = _make_helper(MagicMock())
    latents = torch.zeros(4, 3)
    out = helper._fit_latent_batch(latents, 2)
    assert out.shape == (2, 3)


def test_fit_latent_batch_exact_match_unchanged():
    helper = _make_helper(MagicMock())
    latents = torch.zeros(3, 3)
    out = helper._fit_latent_batch(latents, 3)
    assert out.shape == (3, 3)


def test_fit_latent_batch_rejects_non_divisible_repeat():
    helper = _make_helper(MagicMock())
    latents = torch.zeros(2, 3)
    with pytest.raises(ValueError, match="Cannot duplicate"):
        helper._fit_latent_batch(latents, 3)


def test_img2img_requires_vae():
    owner = MagicMock()
    owner.vae = None
    helper = _make_helper(owner)
    with pytest.raises(RuntimeError, match="VAE must be loaded"):
        helper._prepare_img2img_latents("in", 512, 512, 1, None, None, torch.tensor([0]), 0.8)


def test_img2img_with_explicit_latents_skips_noise():
    owner = MagicMock()
    vae_helper = MagicMock()
    owner._get_vae_helper.return_value = vae_helper
    owner.vae.config.shift_factor = 0
    owner.vae.config.scaling_factor = 1
    owner.vae.encode.return_value.latent_dist.sample.return_value = torch.zeros(1, 4)
    owner.image_processor.preprocess.return_value.to.return_value = MagicMock()
    owner.device = "cpu"
    helper = _make_helper(owner)
    helper._resolve_image_size = lambda image, h, w: (h, w)
    helper._randn = MagicMock()
    provided = torch.zeros(1, 4)
    out = helper._prepare_img2img_latents(
        "in", 512, 512, 1, provided, None, torch.tensor([0]), 0.8
    )
    assert out.shape == provided.shape
    helper._randn.assert_not_called()
