"""
Unit tests for melo.models
"""

import pytest
import importlib
import torch

models = importlib.import_module("airunner.vendor.melo.models")


def test_models_module_importable():
    assert models is not None


def test_DurationDiscriminator_forward():
    m = models.DurationDiscriminator(4, 4, 3, 0.1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    dur_r = torch.randn(2, 1, 5)
    dur_hat = torch.randn(2, 1, 5)
    out = m(x, x_mask, dur_r, dur_hat)
    assert len(out) == 2
    assert out[0].shape == (2, 5, 1)
    assert not hasattr(m, "cond")


def test_TransformerCouplingBlock_forward_and_reverse():
    m = models.TransformerCouplingBlock(4, 4, 4, 2, 3, 3, 0.1, n_flows=2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = m(x, x_mask)
    assert out.shape == x.shape
    out_rev = m(x, x_mask, reverse=True)
    assert out_rev.shape == x.shape


def test_StochasticDurationPredictor_forward_and_reverse():
    m = models.StochasticDurationPredictor(4, 4, 3, 0.1, n_flows=2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    w = torch.randn(2, 1, 5)
    nll = m(x, x_mask, w=w)
    assert nll.shape[0] == 2
    logw = m(x, x_mask, reverse=True)
    assert logw.shape == (2, 1, 5)


def test_DurationPredictor_forward():
    m = models.DurationPredictor(4, 4, 3, 0.1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = m(x, x_mask)
    assert out.shape == (2, 1, 5)
    m_g = models.DurationPredictor(4, 4, 3, 0.1, gin_channels=2)
    g = torch.randn(2, 2, 5)
    out_g = m_g(x, x_mask, g)
    assert out_g.shape == (2, 1, 5)


def test_TextEncoder_forward():
    m = models.TextEncoder(
        n_vocab=10,
        out_channels=4,
        hidden_channels=4,
        filter_channels=4,
        n_heads=2,
        n_layers=2,
        kernel_size=3,
        p_dropout=0.1,
        num_languages=2,
        num_tones=2,
    )
    x = torch.randint(0, 10, (2, 5))
    x_lengths = torch.tensor([5, 5])
    tone = torch.randint(0, 2, (2, 5))
    language = torch.randint(0, 2, (2, 5))
    bert = torch.randn(2, 1024, 5)
    ja_bert = torch.randn(2, 768, 5)
    out = m(x, x_lengths, tone, language, bert, ja_bert)
    assert len(out) == 4
    assert out[0].shape[0] == 2


def test_ResidualCouplingBlock_forward_and_reverse():
    m = models.ResidualCouplingBlock(4, 4, 3, 1, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = m(x, x_mask)
    assert out.shape == x.shape
    out_rev = m(x, x_mask, reverse=True)
    assert out_rev.shape == x.shape


def test_PosteriorEncoder_forward():
    m = models.PosteriorEncoder(4, 4, 4, 3, 1, 2)
    x = torch.randn(2, 4, 5)
    x_lengths = torch.tensor([5, 5])
    out = m(x, x_lengths)
    assert len(out) == 4
    assert out[0].shape[0] == 2


def test_Generator_forward_and_remove_weight_norm():
    m = models.Generator(
        initial_channel=4,
        resblock="1",
        resblock_kernel_sizes=[3],
        resblock_dilation_sizes=[[1, 2, 3]],
        upsample_rates=[2],
        upsample_initial_channel=4,
        upsample_kernel_sizes=[4],
    )
    x = torch.randn(2, 4, 8)
    out = m(x)
    assert out.shape[0] == 2
    m.remove_weight_norm()


def test_DiscriminatorP_forward():
    m = models.DiscriminatorP(2)
    x = torch.randn(2, 1, 8)
    out, fmap = m(x)
    assert out.shape[0] == 2
    assert isinstance(fmap, list)


def test_DiscriminatorS_forward():
    m = models.DiscriminatorS()
    x = torch.randn(2, 1, 8)
    out, fmap = m(x)
    assert out.shape[0] == 2
    assert isinstance(fmap, list)


def test_MultiPeriodDiscriminator_forward():
    m = models.MultiPeriodDiscriminator()
    y = torch.randn(2, 1, 8)
    y_hat = torch.randn(2, 1, 8)
    y_d_rs, y_d_gs, fmap_rs, fmap_gs = m(y, y_hat)
    assert len(y_d_rs) == 6
    assert len(y_d_gs) == 6
    assert len(fmap_rs) == 6
    assert len(fmap_gs) == 6


def test_ReferenceEncoder_forward():
    m = models.ReferenceEncoder(80, gin_channels=4)
    x = torch.randn(2, 80 * 4).view(2, 4, 80)
    x = x.reshape(2, 80 * 4)
    out = m(x)
    assert out.shape[0] == 2


def test_SynthesizerTrn_forward_and_infer_and_voice_conversion():
    m = models.SynthesizerTrn(
        n_vocab=10,
        spec_channels=4,
        segment_size=2,
        inter_channels=4,
        hidden_channels=4,
        filter_channels=4,
        n_heads=2,
        n_layers=5,
        kernel_size=3,
        p_dropout=0.1,
        resblock="1",
        resblock_kernel_sizes=[3],
        resblock_dilation_sizes=[[1, 2, 3]],
        upsample_rates=[2],
        upsample_initial_channel=4,
        upsample_kernel_sizes=[4],
        n_speakers=2,
        gin_channels=4,
        n_flow_layer=3,
        n_layers_trans_flow=3,
        num_languages=2,
        num_tones=2,
    )
    x = torch.randint(0, 10, (2, 5))
    x_lengths = torch.tensor([5, 5])
    y = torch.randn(2, 4, 5)
    y_lengths = torch.tensor([5, 5])
    sid = torch.tensor([0, 1])
    tone = torch.randint(0, 2, (2, 5))
    language = torch.randint(0, 2, (2, 5))
    bert = torch.randn(2, 1024, 5)
    ja_bert = torch.randn(2, 768, 5)
    out = m(x, x_lengths, y, y_lengths, sid, tone, language, bert, ja_bert)
    assert isinstance(out, tuple)
    out_inf = m.infer(x, x_lengths, sid, tone, language, bert, ja_bert, max_len=5)
    assert isinstance(out_inf, tuple)
    sid_src = torch.randn(2, 4, 5)
    sid_tgt = torch.randn(2, 4, 5)
    o_hat, y_mask, _ = m.voice_conversion(y, y_lengths, sid_src, sid_tgt)
    assert o_hat.shape[0] == 2
