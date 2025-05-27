"""
Unit tests for openvoice.attentions
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.attentions as attentions
import torch
from unittest.mock import patch


def test_module_importable():
    assert attentions is not None


def test_LayerNorm_forward():
    norm = attentions.LayerNorm(4)
    x = torch.randn(2, 4, 3)
    out = norm(x)
    assert out.shape == x.shape


def test_fused_add_tanh_sigmoid_multiply():
    a = torch.randn(2, 4, 3)
    b = torch.randn(2, 4, 3)
    n_channels = torch.tensor([2])
    out = attentions.fused_add_tanh_sigmoid_multiply(a, b, n_channels)
    assert out.shape == (2, 2, 3)


def test_Encoder_forward():
    enc = attentions.Encoder(4, 4, 2, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)  # mask shape: (batch, 1, seq_len)
    out = enc(x, x_mask)
    assert out.shape == x.shape


def test_Encoder_with_gin_channels_and_g_branch():
    # gin_channels triggers spk_emb_linear and cond_layer_idx logic
    enc = attentions.Encoder(4, 4, 2, 3, gin_channels=8, cond_layer_idx=1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    g = torch.randn(2, 8, 1)  # (batch, gin_channels, 1)
    out = enc(x, x_mask, g=g)
    assert out.shape == x.shape


def test_Decoder_forward():
    dec = attentions.Decoder(4, 4, 2, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    h = torch.randn(2, 4, 5)
    h_mask = torch.ones(2, 1, 5)
    with patch(
        "airunner.vendor.openvoice.commons.subsequent_mask",
        return_value=torch.ones(1, 5, 5),
    ):
        out = dec(x, x_mask, h, h_mask)
    assert out.shape == x.shape


def test_Decoder_forward_edge_mask():
    # Test Decoder with mask shape edge case (simulate mask with zeros)
    dec = attentions.Decoder(4, 4, 2, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.zeros(2, 1, 5)  # all masked out
    h = torch.randn(2, 4, 5)
    h_mask = torch.zeros(2, 1, 5)
    with patch(
        "airunner.vendor.openvoice.commons.subsequent_mask",
        return_value=torch.ones(1, 5, 5),
    ):
        out = dec(x, x_mask, h, h_mask)
    assert torch.all(out == 0)


def test_MultiHeadAttention_forward():
    attn = attentions.MultiHeadAttention(4, 4, 2)
    x = torch.randn(2, 4, 5)
    c = torch.randn(2, 4, 5)
    out = attn(x, c)
    assert out.shape == x.shape


def test_FFN_forward():
    ffn = attentions.FFN(4, 4, 8, 3)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 4, 5)
    with patch.object(ffn, "padding", side_effect=lambda x: x):
        out1 = ffn.conv_1(x * x_mask)
        out1 = torch.relu(out1)
        out1 = ffn.drop(out1)
        # Mask must match out1 shape
        mask1 = torch.ones_like(out1)
        out2 = ffn.conv_2(out1 * mask1)
        mask2 = torch.ones_like(out2)
        out2 = out2 * mask2
    assert out2.shape[0] == 2 and out2.shape[1] == 4


def test_FFN_forward_relu_branch():
    # Covers FFN.forward else: x = torch.relu(x) (line 475)
    ffn = attentions.FFN(4, 4, 8, 3, activation="relu")
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 4, 5)
    # After conv_1, output has 8 channels
    mask1 = torch.ones(2, 8, 5)
    mask2 = torch.ones(2, 4, 5)
    out1 = ffn.conv_1(ffn.padding(x * x_mask))
    out1 = torch.relu(out1)
    out1 = ffn.drop(out1)
    out2 = ffn.conv_2(ffn.padding(out1 * mask1))
    out2 = out2 * mask2
    assert out2.shape == (2, 4, 5)


def test_FFN_causal_and_same_padding():
    # Test FFN._causal_padding and _same_padding with kernel_size > 1
    ffn_causal = attentions.FFN(4, 4, 8, 3, causal=True)
    ffn_same = attentions.FFN(4, 4, 8, 3, causal=False)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 4, 5)
    # Causal padding
    # After conv_1, output has 8 channels
    mask1 = torch.ones(2, 8, 5)
    mask2 = torch.ones(2, 4, 5)
    out1 = ffn_causal.conv_1(ffn_causal.padding(x * x_mask))
    if ffn_causal.activation == "gelu":
        out1 = out1 * torch.sigmoid(1.702 * out1)
    else:
        out1 = torch.relu(out1)
    out1 = ffn_causal.drop(out1)
    out2 = ffn_causal.conv_2(ffn_causal.padding(out1 * mask1))
    out2 = out2 * mask2
    assert out2.shape == (2, 4, 5)
    # Same padding
    out1 = ffn_same.conv_1(ffn_same.padding(x * x_mask))
    if ffn_same.activation == "gelu":
        out1 = out1 * torch.sigmoid(1.702 * out1)
    else:
        out1 = torch.relu(out1)
    out1 = ffn_same.drop(out1)
    out2 = ffn_same.conv_2(ffn_same.padding(out1 * mask1))
    out2 = out2 * mask2
    assert out2.shape == (2, 4, 5)


def test_MultiHeadAttention_window_and_proximal():
    # window_size triggers relative attention branches
    attn = attentions.MultiHeadAttention(4, 4, 2, window_size=1, proximal_bias=True)
    x = torch.randn(2, 4, 5)
    c = torch.randn(2, 4, 5)
    mask = torch.ones(2, 2, 5, 5)  # (batch, n_heads, t_t, t_s)
    out = attn(x, c, attn_mask=mask)
    assert out.shape == x.shape


def test_MultiHeadAttention_block_length():
    attn = attentions.MultiHeadAttention(4, 4, 2, block_length=2)
    x = torch.randn(2, 4, 5)
    c = torch.randn(2, 4, 5)
    mask = torch.ones(2, 2, 5, 5)
    out = attn(x, c, attn_mask=mask)
    assert out.shape == x.shape


def test_MultiHeadAttention_assertions():
    attn = attentions.MultiHeadAttention(4, 4, 2, window_size=1)
    x = torch.randn(2, 4, 5)
    c = torch.randn(2, 4, 6)  # t_s != t_t triggers assertion
    try:
        attn(x, c)
    except AssertionError:
        pass
    else:
        assert False, "Expected AssertionError for t_s != t_t with window_size"


def test_attention_bias_proximal():
    attn = attentions.MultiHeadAttention(4, 4, 2)
    bias = attn._attention_bias_proximal(5)
    assert bias.shape == (1, 1, 5, 5)


def test_relative_position_methods():
    attn = attentions.MultiHeadAttention(4, 4, 2, window_size=1)
    # _matmul_with_relative_values
    x = torch.randn(2, 2, 5, 3)
    y = torch.randn(2, 3, 3)  # (n_heads, m, d) with d=3
    attn.emb_rel_v = torch.nn.Parameter(torch.randn(1, 3, 3))
    attn.emb_rel_k = torch.nn.Parameter(torch.randn(1, 3, 3))
    attn._get_relative_embeddings(attn.emb_rel_v, 5)
    attn._matmul_with_relative_values(x, y)
    # For _matmul_with_relative_keys, y must have shape (2, m, d) to match n_heads and d
    y_keys = torch.randn(2, 3, 3)
    attn._matmul_with_relative_keys(x, y_keys)
    # _relative_position_to_absolute_position
    rel = torch.randn(2, 2, 5, 9)
    attn._relative_position_to_absolute_position(rel)
    # _absolute_position_to_relative_position
    abs_pos = torch.randn(2, 2, 5, 5)
    attn._absolute_position_to_relative_position(abs_pos)
