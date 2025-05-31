"""
Unit tests for openvoice.models
"""

import pytest
import importlib
import torch
from unittest.mock import patch, MagicMock

import airunner.vendor.openvoice.models as models
import airunner.vendor.openvoice.modules as modules
import airunner.vendor.openvoice.attentions as attentions
import airunner.vendor.openvoice.commons as commons


def test_models_module_importable():
    assert models is not None


def test_TextEncoder_forward():
    encoder = models.TextEncoder(
        n_vocab=10,
        out_channels=4,
        hidden_channels=4,
        filter_channels=4,
        n_heads=2,
        n_layers=2,
        kernel_size=3,
        p_dropout=0.1,
    )
    x = torch.randint(0, 10, (2, 5))
    x_lengths = torch.tensor([5, 3])
    out = encoder(x, x_lengths)
    assert len(out) == 4
    assert out[0].shape[0] == 2


def test_DurationPredictor_forward():
    dp = models.DurationPredictor(4, 4, 3, 0.1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = dp(x, x_mask)
    assert out.shape == (2, 1, 5)

    dp_g = models.DurationPredictor(4, 4, 3, 0.1, gin_channels=2)
    g = torch.randn(2, 2, 5)
    out = dp_g(x, x_mask, g)
    assert out.shape == (2, 1, 5)


def test_StochasticDurationPredictor_forward_and_reverse():
    sdp = models.StochasticDurationPredictor(4, 4, 3, 0.1, n_flows=2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    w = torch.randn(2, 1, 5)
    # Ensure w is not empty and has valid shape
    assert w.numel() > 0
    nll = sdp(x, x_mask, w=w)
    assert nll.shape[0] == 2
    # reverse
    logw = sdp(x, x_mask, reverse=True)
    assert logw.shape == (2, 1, 5)


def test_PosteriorEncoder_forward():
    enc = models.PosteriorEncoder(4, 4, 4, 3, 1, 2)
    x = torch.randn(2, 4, 5)
    x_lengths = torch.tensor([5, 3])
    z, m, logs, x_mask = enc(x, x_lengths)
    assert z.shape == m.shape == logs.shape
    assert x_mask.shape[0] == 2


def test_Generator_forward_and_remove_weight_norm():
    gen = models.Generator(
        initial_channel=4,
        resblock="1",
        resblock_kernel_sizes=[3],
        resblock_dilation_sizes=[[1, 2, 3]],  # Must be length 3
        upsample_rates=[2],
        upsample_initial_channel=4,
        upsample_kernel_sizes=[4],
    )
    x = torch.randn(2, 4, 10)
    out = gen(x)
    assert out.shape[0] == 2
    gen.remove_weight_norm()


def test_ReferenceEncoder_forward():
    enc = models.ReferenceEncoder(spec_channels=8, gin_channels=4)
    x = torch.randn(2, 16, 8)
    out = enc(x)
    assert out.shape[0] == 2


def test_ReferenceEncoder_layernorm_false():
    enc = models.ReferenceEncoder(spec_channels=8, gin_channels=4, layernorm=False)
    x = torch.randn(2, 16, 8)
    out = enc(x)
    assert out.shape[0] == 2


def test_SynthesizerTrn_infer_and_voice_conversion():
    synth = models.SynthesizerTrn(
        n_vocab=10,
        spec_channels=4,
        inter_channels=4,
        hidden_channels=4,
        filter_channels=4,
        n_heads=2,
        n_layers=2,
        kernel_size=3,
        p_dropout=0.1,
        resblock="1",
        resblock_kernel_sizes=[3],
        resblock_dilation_sizes=[[1, 2, 3]],  # Must be length 3
        upsample_rates=[2],
        upsample_initial_channel=4,
        upsample_kernel_sizes=[4],
        n_speakers=2,
        gin_channels=4,
    )
    x = torch.randint(0, 10, (2, 5))
    x_lengths = torch.tensor([5, 5])
    sid = torch.tensor([0, 1])
    out = synth.infer(x, x_lengths, sid=sid, max_len=5)
    assert out[0].shape[0] == 2
    y = torch.randn(2, 4, 5)
    y_lengths = torch.tensor([5, 5])
    # Pass random tensor for sid_src and sid_tgt with shape [batch, gin_channels, time]
    sid_src = torch.randn(2, 4, 5)
    sid_tgt = torch.randn(2, 4, 5)
    o_hat, y_mask, _ = synth.voice_conversion(y, y_lengths, sid_src, sid_tgt)
    assert o_hat.shape[0] == 2


def test_SynthesizerTrn_n_speakers_zero():
    synth = models.SynthesizerTrn(
        n_vocab=10,
        spec_channels=4,
        inter_channels=4,
        hidden_channels=4,
        filter_channels=4,
        n_heads=2,
        n_layers=2,
        kernel_size=3,
        p_dropout=0.1,
        resblock="1",
        resblock_kernel_sizes=[3],
        resblock_dilation_sizes=[[1, 2, 3]],
        upsample_rates=[2],
        upsample_initial_channel=4,
        upsample_kernel_sizes=[4],
        n_speakers=0,
        gin_channels=4,
    )
    x = torch.randn(2, 4, 5)  # Correct shape: [batch, in_channels, time]
    x_lengths = torch.tensor([5, 5])
    # Should not raise
    out = synth.enc_q(x, x_lengths)
    assert out[0].shape[0] == 2


def test_StochasticDurationPredictor_gin_channels_zero():
    sdp = models.StochasticDurationPredictor(4, 4, 3, 0.1, n_flows=2, gin_channels=0)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    w = torch.randn(2, 1, 5)
    nll = sdp(x, x_mask, w=w)
    assert nll.shape[0] == 2
    logw = sdp(x, x_mask, reverse=True)
    assert logw.shape == (2, 1, 5)


def test_ResidualCouplingBlock_forward():
    block = models.ResidualCouplingBlock(4, 4, 3, 1, 2, n_flows=2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = block(x, x_mask)
    assert out.shape == x.shape
    out_rev = block(x, x_mask, reverse=True)
    assert out_rev.shape == x.shape


def test_ResidualCouplingBlock_reverse_branch():
    block = models.ResidualCouplingBlock(4, 4, 3, 1, 2, n_flows=2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = block(x, x_mask, reverse=True)
    assert out.shape == x.shape
