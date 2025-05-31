"""
Unit tests for melo.commons
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.commons as commons
import torch


def test_module_importable():
    assert commons is not None


def test_init_weights_conv():
    import torch.nn as nn

    conv = nn.Conv1d(4, 4, 3)
    commons.init_weights(conv)
    assert conv.weight is not None


def test_get_padding():
    assert commons.get_padding(3) == 1
    assert commons.get_padding(5, 2) == 4


def test_convert_pad_shape():
    # The function reverses the list of pairs, then flattens
    assert commons.convert_pad_shape([[1, 2], [3, 4]]) == [3, 4, 1, 2]


def test_intersperse():
    assert commons.intersperse([1, 2, 3], 0) == [0, 1, 0, 2, 0, 3, 0]


def test_kl_divergence():
    m_p = torch.zeros(2, 3)
    logs_p = torch.zeros(2, 3)
    m_q = torch.zeros(2, 3)
    logs_q = torch.zeros(2, 3)
    kl = commons.kl_divergence(m_p, logs_p, m_q, logs_q)
    assert kl.shape == m_p.shape


def test_rand_gumbel_and_like():
    g = commons.rand_gumbel((2, 3))
    assert g.shape == (2, 3)
    x = torch.zeros(2, 3)
    g2 = commons.rand_gumbel_like(x)
    assert g2.shape == (2, 3)


def test_slice_segments():
    x = torch.arange(24).reshape(2, 3, 4)
    ids_str = torch.tensor([0, 1])
    out = commons.slice_segments(x, ids_str, 2)
    assert out.shape == (2, 3, 2)


def test_rand_slice_segments():
    x = torch.randn(2, 3, 8)
    out, ids = commons.rand_slice_segments(x, torch.tensor(8), 4)
    assert out.shape == (2, 3, 4)
    assert ids.shape[0] == 2


def test_get_add_cat_timing_signal_1d():
    x = torch.randn(1, 4, 8)  # batch size 1 to match signal
    signal = commons.get_timing_signal_1d(8, 4)
    assert signal.shape == (1, 4, 8)
    added = commons.add_timing_signal_1d(x)
    assert added.shape == x.shape
    cat = commons.cat_timing_signal_1d(x)
    assert (
        cat.shape[1] == x.shape[1] * 2 or cat.shape[1] == x.shape[1] + signal.shape[1]
    )


def test_subsequent_mask():
    mask = commons.subsequent_mask(4)
    assert mask.shape == (1, 1, 4, 4)
    # The mask should be lower-triangular
    assert torch.all(mask[0, 0] == mask[0, 0].tril())


def test_fused_add_tanh_sigmoid_multiply():
    a = torch.ones(2, 4, 3)
    b = torch.zeros(2, 4, 3)
    n_channels = torch.tensor([2])
    out = commons.fused_add_tanh_sigmoid_multiply(a, b, n_channels)
    assert out.shape == (2, 2, 3)


def test_shift_1d():
    x = torch.arange(8).reshape(1, 2, 4).float()
    shifted = commons.shift_1d(x)
    assert shifted.shape == x.shape
    assert torch.all(shifted[:, :, 1:] == x[:, :, :-1])


def test_sequence_mask():
    lengths = torch.tensor([2, 4])
    mask = commons.sequence_mask(lengths)
    assert mask.shape == (2, 4)
    assert torch.all(mask[0, :2]) and not torch.any(mask[0, 2:])


def test_generate_path():
    duration = torch.tensor([[[2, 2]]])
    mask = torch.ones(1, 1, 4, 2)
    path = commons.generate_path(duration, mask)
    assert path.shape == (1, 1, 4, 2)


def test_clip_grad_value_():
    x = torch.nn.Parameter(torch.randn(3, 3))
    y = torch.nn.Parameter(torch.randn(3, 3))
    for p in [x, y]:
        p.grad = torch.ones_like(p)
    total_norm = commons.clip_grad_value_([x, y], 0.1)
    assert total_norm > 0
    assert torch.all(x.grad.abs() <= 0.1)
    assert torch.all(y.grad.abs() <= 0.1)
