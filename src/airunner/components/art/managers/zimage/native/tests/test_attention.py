"""Unit tests for attention module.

Tests JointAttention with RoPE and multi-head attention.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.attention import (
    JointAttention,
    RMSNorm,
)


class TestRMSNorm:
    """Tests for RMSNorm class."""

    def test_creation(self) -> None:
        """Test creating RMSNorm."""
        norm = RMSNorm(dim=256)
        
        assert norm.dim == 256

    def test_forward_shape(self) -> None:
        """Test forward preserves shape."""
        norm = RMSNorm(dim=128)
        x = torch.randn(2, 16, 128)
        
        output = norm(x)
        
        assert output.shape == x.shape

    def test_normalization(self) -> None:
        """Test that output is normalized."""
        norm = RMSNorm(dim=64)
        x = torch.randn(1, 8, 64) * 10  # Large values
        
        output = norm(x)
        
        # RMS should be close to 1
        rms = torch.sqrt(torch.mean(output ** 2, dim=-1))
        assert torch.allclose(rms, torch.ones_like(rms), atol=0.1)

    def test_no_nan(self) -> None:
        """Test no NaN in output."""
        norm = RMSNorm(dim=32)
        x = torch.randn(4, 10, 32)
        
        output = norm(x)
        
        assert not torch.isnan(output).any()


class TestJointAttention:
    """Tests for JointAttention class."""

    def test_creation(self) -> None:
        """Test creating attention layer."""
        attn = JointAttention(
            dim=256,
            n_heads=8,
        )
        
        assert attn.n_local_heads == 8
        assert attn.head_dim == 32  # 256 / 8

    def test_creation_with_kv_heads(self) -> None:
        """Test creating with different KV heads (GQA)."""
        attn = JointAttention(
            dim=256,
            n_heads=8,
            n_kv_heads=4,  # Grouped query attention
        )
        
        assert attn.n_local_heads == 8
        assert attn.n_kv_heads == 4

    def _make_freqs_cis(self, batch_size: int, seq_len: int, head_dim: int) -> torch.Tensor:
        """Create mock RoPE frequencies for testing."""
        # Shape should match what apply_rope expects
        # Return a tensor that can be used with rope_impl output format
        # rope_impl returns (batch, seq, dim/2, 2, 2)
        return torch.randn(batch_size, seq_len, 1, head_dim // 2, 2, 2)

    def test_forward_shape(self) -> None:
        """Test forward produces correct shape."""
        dim = 256
        n_heads = 8
        attn = JointAttention(dim=dim, n_heads=n_heads)
        
        batch_size = 2
        seq_len = 16
        x = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = attn(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert output.shape == x.shape

    def test_forward_with_mask(self) -> None:
        """Test forward with attention mask."""
        dim = 128
        n_heads = 4
        attn = JointAttention(dim=dim, n_heads=n_heads)
        
        batch_size = 2
        seq_len = 8
        x = torch.randn(batch_size, seq_len, dim)
        mask = torch.ones(batch_size, seq_len, dtype=torch.bool)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = attn(x, x_mask=mask, freqs_cis=freqs_cis)
        
        assert output.shape == x.shape

    def test_attention_different_inputs(self) -> None:
        """Test that different inputs produce different outputs."""
        dim = 64
        n_heads = 2
        attn = JointAttention(dim=dim, n_heads=n_heads)
        
        batch_size = 1
        seq_len = 8
        
        x1 = torch.randn(batch_size, seq_len, dim)
        x2 = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        out1 = attn(x1, x_mask=None, freqs_cis=freqs_cis)
        out2 = attn(x2, x_mask=None, freqs_cis=freqs_cis)
        
        assert not torch.allclose(out1, out2)

    def test_no_nan_output(self) -> None:
        """Test no NaN in output."""
        dim = 128
        n_heads = 4
        attn = JointAttention(dim=dim, n_heads=n_heads)
        
        batch_size = 2
        seq_len = 16
        x = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = attn(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    def test_deterministic(self) -> None:
        """Test that same input produces same output (no dropout in eval)."""
        dim = 64
        n_heads = 2
        attn = JointAttention(dim=dim, n_heads=n_heads)
        attn.eval()
        
        batch_size = 1
        seq_len = 4
        x = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        out1 = attn(x, x_mask=None, freqs_cis=freqs_cis)
        out2 = attn(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert torch.allclose(out1, out2)

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self) -> None:
        """Test attention on CUDA."""
        dim = 128
        n_heads = 4
        attn = JointAttention(dim=dim, n_heads=n_heads).cuda()
        
        batch_size = 2
        seq_len = 8
        x = torch.randn(batch_size, seq_len, dim, device="cuda")
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads).cuda()
        
        output = attn(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert output.device.type == "cuda"
        assert output.shape == x.shape
