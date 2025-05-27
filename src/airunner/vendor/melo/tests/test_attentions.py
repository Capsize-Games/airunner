"""
Unit tests for melo.attentions
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.attentions as attentions
import torch
from airunner.vendor.melo.attentions import (
    LayerNorm,
    fused_add_tanh_sigmoid_multiply,
    FFN,
    MultiHeadAttention,
    Encoder,
    Decoder,
)


def test_module_importable():
    assert attentions is not None


def test_layernorm_forward_shapes_and_values():
    ln = LayerNorm(4)
    x = torch.randn(2, 4, 5)
    out = ln(x)
    assert out.shape == x.shape
    # Should have zero mean and unit variance along channel dim (dim=1) for each sample/timestep
    normed = out
    mean = normed.mean(dim=1)
    std = normed.std(dim=1, unbiased=False)
    assert torch.allclose(mean, torch.zeros_like(mean), atol=1e-5)
    assert torch.allclose(
        std, torch.ones_like(std), atol=1e-3
    )  # Loosen tolerance for float error


def test_fused_add_tanh_sigmoid_multiply_basic():
    a = torch.ones(2, 4, 3)
    b = torch.zeros(2, 4, 3)
    n_channels = torch.tensor([2])
    out = fused_add_tanh_sigmoid_multiply(a, b, n_channels)
    assert out.shape == (2, 2, 3)
    # Check that output is in expected range
    assert torch.all((out >= -1) & (out <= 1))


def test_fused_add_tanh_sigmoid_multiply_edge_channels():
    a = torch.randn(1, 6, 2)
    b = torch.randn(1, 6, 2)
    n_channels = torch.tensor([3])
    out = fused_add_tanh_sigmoid_multiply(a, b, n_channels)
    assert out.shape == (1, 3, 2)


def test_ffn_forward_relu_and_gelu():
    # Test both relu and gelu activations, causal and non-causal
    for activation in [None, "gelu"]:
        for causal in [False, True]:
            ffn = FFN(4, 4, 8, 3, activation=activation, causal=causal)
            x = torch.randn(2, 4, 5)
            mask = torch.ones(
                2, 4, 5
            )  # Use all-ones mask to avoid shape mismatch in intermediate conv
            out = ffn(x, mask)
            assert out.shape == (2, 4, 5)


def test_ffn_forward_kernel_size_one():
    ffn = FFN(4, 4, 8, 1)
    x = torch.randn(2, 4, 5)
    mask = torch.ones(2, 4, 5)
    out = ffn(x, mask)
    assert out.shape == (2, 4, 5)


def test_ffn_invalid_kernel_size():
    # Should not raise for kernel_size=1, but should work for odd/even sizes
    FFN(4, 4, 8, 1)
    FFN(4, 4, 8, 2)
    FFN(4, 4, 8, 3)


def test_ffn_mask_shape_mismatch():
    ffn = FFN(4, 4, 8, 3)
    x = torch.randn(2, 4, 5)
    mask = torch.ones(2, 3, 5)  # Wrong channel dim
    with pytest.raises(RuntimeError):
        ffn(x, mask)


def test_multiheadattention_forward_basic():
    mha = MultiHeadAttention(4, 4, 2)
    x = torch.randn(2, 4, 5)
    out = mha(x, x)
    assert out.shape == (2, 4, 5)
    # Attention weights should sum to 1 along last dim
    attn = mha.attn
    assert attn is not None
    assert torch.allclose(
        attn.sum(dim=-1), torch.ones_like(attn.sum(dim=-1)), atol=1e-5
    )


def test_multiheadattention_masking():
    mha = MultiHeadAttention(4, 4, 2)
    x = torch.randn(1, 4, 3)
    # Mask shape: [batch, n_heads, tgt_len, src_len]
    mask = torch.ones(1, 2, 3, 3)
    mask[:, :, :, 2] = 0  # Mask out last position
    out = mha(x, x, attn_mask=mask)
    assert out.shape == (1, 4, 3)


def test_encoder_forward_basic():
    enc = Encoder(4, 8, 2, 2)
    x = torch.randn(1, 4, 5)
    # Use mask shape [batch, 1, seq_len] to allow broadcasting in attention
    mask = torch.ones(1, 1, 5)
    out = enc(x, mask)
    assert out.shape == (1, 4, 5)


def test_decoder_forward_basic():
    dec = Decoder(4, 8, 2, 2)
    x = torch.randn(1, 4, 5)
    mask = torch.ones(1, 1, 5)
    h = torch.randn(1, 4, 5)
    h_mask = torch.ones(1, 1, 5)
    out = dec(x, mask, h, h_mask)
    assert out.shape == (1, 4, 5)


def test_multiheadattention_error_branches():
    # Test window_size branch
    mha = MultiHeadAttention(4, 4, 2, window_size=1)
    x = torch.randn(1, 4, 3)
    # Should raise assertion if t_s != t_t
    with pytest.raises(AssertionError):
        mha(x, torch.randn(1, 4, 2))
    # Test proximal_bias branch
    mha = MultiHeadAttention(4, 4, 2, proximal_bias=True)
    x = torch.randn(1, 4, 3)
    # Should raise assertion if t_s != t_t
    with pytest.raises(AssertionError):
        mha(x, torch.randn(1, 4, 2))
    # Test block_length branch (masking)
    mha = MultiHeadAttention(4, 4, 2, block_length=1)
    x = torch.randn(1, 4, 3)
    mask = torch.ones(1, 2, 3, 3)
    out = mha(x, x, attn_mask=mask)
    assert out.shape == (1, 4, 3)


def test_ffn_causal_and_same_padding():
    # Test _causal_padding and _same_padding branches
    ffn_causal = FFN(4, 4, 8, 3, causal=True)
    ffn_same = FFN(4, 4, 8, 3, causal=False)
    x = torch.randn(2, 4, 5)
    mask = torch.ones(2, 4, 5)
    out1 = ffn_causal(x, mask)
    out2 = ffn_same(x, mask)
    assert out1.shape == out2.shape == (2, 4, 5)


def test_multiheadattention_internal_helpers():
    # Test _matmul_with_relative_values and _matmul_with_relative_keys
    mha = MultiHeadAttention(4, 4, 2, window_size=1)
    x = torch.randn(1, 2, 3, 2)  # [b, h, l, d]
    y = torch.randn(2, 2, 2)  # [h, m, d] (h=2, m=2, d=2)
    out1 = mha._matmul_with_relative_values(x, y)
    assert out1.shape == (1, 2, 3, 2)
    out2 = mha._matmul_with_relative_keys(x, y)
    assert out2.shape == (1, 2, 3, 2)
    # Test _get_relative_embeddings
    rel_emb = torch.randn(1, 3, 2)
    used = mha._get_relative_embeddings(rel_emb, 2)
    assert used.shape[1] == 3 or used.shape[1] == 2
    # Test _relative_position_to_absolute_position and _absolute_position_to_relative_position
    x = torch.randn(1, 2, 2, 3)
    abs_pos = mha._relative_position_to_absolute_position(x)
    rel_pos = mha._absolute_position_to_relative_position(abs_pos)
    assert rel_pos.shape[2] == abs_pos.shape[2]
    # Test _attention_bias_proximal
    bias = mha._attention_bias_proximal(3)
    assert bias.shape == (1, 1, 3, 3)
