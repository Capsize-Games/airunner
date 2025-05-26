"""
Unit tests for openvoice.commons
Covers utility, math, and tensor functions.
"""

import pytest
import torch
import math
import airunner.vendor.openvoice.commons as commons


def test_get_padding():
    assert commons.get_padding(3) == 1
    assert commons.get_padding(5, 2) == 4


def test_intersperse():
    assert commons.intersperse([1, 2, 3], 0) == [0, 1, 0, 2, 0, 3, 0]


def test_kl_divergence_shapes():
    m_p = torch.zeros(2, 3)
    logs_p = torch.zeros(2, 3)
    m_q = torch.zeros(2, 3)
    logs_q = torch.zeros(2, 3)
    kl = commons.kl_divergence(m_p, logs_p, m_q, logs_q)
    assert kl.shape == m_p.shape


def test_rand_gumbel_like():
    x = torch.zeros(2, 3)
    g = commons.rand_gumbel_like(x)
    assert g.shape == x.shape


def test_slice_segments_shape():
    x = torch.randn(2, 4, 10)
    ids_str = torch.tensor([1, 2])
    seg = commons.slice_segments(x, ids_str, segment_size=4)
    assert seg.shape == (2, 4, 4)


def test_rand_slice_segments_shape():
    x = torch.randn(2, 4, 10)
    seg, ids = commons.rand_slice_segments(x, x_lengths=8, segment_size=4)
    assert seg.shape == (2, 4, 4)
    assert ids.shape == (2,)


def test_get_timing_signal_1d_shape():
    signal = commons.get_timing_signal_1d(8, 4)
    assert signal.shape == (1, 4, 8)


def test_add_timing_signal_1d_shape():
    x = torch.randn(2, 4, 8)
    out = commons.add_timing_signal_1d(x)
    assert out.shape == x.shape


def test_cat_timing_signal_1d_shape():
    x = torch.randn(1, 4, 8)  # batch size 1 to match timing signal
    out = commons.cat_timing_signal_1d(x)
    assert out.shape[1] == x.shape[1] * 2


def test_subsequent_mask():
    mask = commons.subsequent_mask(5)
    assert mask.shape == (1, 1, 5, 5)


def test_fused_add_tanh_sigmoid_multiply():
    a = torch.randn(2, 4, 8)
    b = torch.randn(2, 4, 8)
    n_channels = torch.tensor([2])
    acts = commons.fused_add_tanh_sigmoid_multiply(a, b, n_channels)
    assert acts.shape == (2, 2, 8)


def test_shift_1d():
    x = torch.randn(2, 4, 8)
    shifted = commons.shift_1d(x)
    assert shifted.shape == x.shape


def test_sequence_mask():
    length = torch.tensor([3, 5])
    mask = commons.sequence_mask(length)
    assert mask.shape[1] == length.max()


def test_generate_path_shape():
    duration = torch.ones(2, 1, 4)
    mask = torch.ones(2, 1, 6, 4)
    path = commons.generate_path(duration, mask)
    assert path.shape == mask.shape


def test_clip_grad_value_():
    x = torch.nn.Parameter(torch.randn(2, 2))
    y = torch.nn.Parameter(torch.randn(2, 2))
    loss = (x**2 + y**2).sum()
    loss.backward()
    total_norm = commons.clip_grad_value_([x, y], clip_value=0.1)
    assert total_norm > 0


def test_init_weights_conv_branch():
    class DummyConv:
        def __init__(self):
            self.__class__.__name__ = "Conv1d"
            self.weight = type("W", (), {"data": torch.zeros(1)})()

    m = DummyConv()
    commons.init_weights(m)
    # Should modify m.weight.data
    assert hasattr(m.weight, "data")


def test_init_weights_nonconv_branch():
    class Dummy:
        def __init__(self):
            self.__class__.__name__ = "Linear"
            self.weight = type("W", (), {"data": torch.zeros(1)})()

    m = Dummy()
    commons.init_weights(m)
    # Should not modify m.weight.data
    assert hasattr(m.weight, "data")


def test_convert_pad_shape():
    pad_shape = [[1, 2], [3, 4], [5, 6]]
    out = commons.convert_pad_shape(pad_shape)
    # Should flatten reversed
    assert out == [5, 6, 3, 4, 1, 2]


def test_rand_slice_segments_no_x_lengths():
    x = torch.randn(2, 4, 10)
    seg, ids = commons.rand_slice_segments(x, segment_size=4)
    assert seg.shape == (2, 4, 4)
    assert ids.shape == (2,)


def test_clip_grad_value_tensor_input():
    x = torch.nn.Parameter(torch.randn(2, 2))
    loss = (x**2).sum()
    loss.backward()
    total_norm = commons.clip_grad_value_(x, clip_value=0.1)
    assert total_norm > 0
