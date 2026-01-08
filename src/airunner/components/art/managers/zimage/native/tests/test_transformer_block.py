"""Unit tests for transformer block module.

Tests JointTransformerBlock with AdaLN modulation for Z-Image.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.transformer_block import (
    JointTransformerBlock,
)


class TestJointTransformerBlock:
    """Tests for JointTransformerBlock class."""

    def _make_freqs_cis(self, batch_size: int, seq_len: int, head_dim: int) -> torch.Tensor:
        """Create mock RoPE frequencies for testing."""
        return torch.randn(batch_size, seq_len, 1, head_dim // 2, 2, 2)

    def test_creation_basic(self) -> None:
        """Test creating transformer block."""
        block = JointTransformerBlock(
            layer_id=0,
            dim=256,
            n_heads=8
        )
        
        assert block.dim == 256
        assert block.head_dim == 32  # 256 / 8

    def test_creation_with_kv_heads(self) -> None:
        """Test creating with grouped query attention."""
        block = JointTransformerBlock(
            layer_id=0,
            dim=256,
            n_heads=8,
            n_kv_heads=4
        )
        
        assert block.attention.n_local_heads == 8
        assert block.attention.n_kv_heads == 4

    def test_creation_with_ffn_mult(self) -> None:
        """Test creating with custom FFN multiplier."""
        block = JointTransformerBlock(
            layer_id=0,
            dim=128,
            n_heads=4,
            ffn_dim_multiplier=2.0
        )
        
        # FFN w1 output features should reflect multiplier
        assert block.feed_forward is not None

    def test_forward_shape(self) -> None:
        """Test forward produces correct shape."""
        dim = 256
        n_heads = 8
        block = JointTransformerBlock(layer_id=0, dim=dim, n_heads=n_heads)
        
        batch_size = 2
        seq_len = 16
        x = torch.randn(batch_size, seq_len, dim)
        # AdaLN input has dimension min(dim, 1024) = 256 when dim=256
        adaln_input = torch.randn(batch_size, dim)  # Must match adaLN input dim
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = block(x, x_mask=None, freqs_cis=freqs_cis, adaln_input=adaln_input)
        
        assert output.shape == x.shape

    def test_forward_no_modulation(self) -> None:
        """Test forward without AdaLN modulation."""
        dim = 128
        n_heads = 4
        block = JointTransformerBlock(
            layer_id=0, dim=dim, n_heads=n_heads, modulation=False
        )
        
        batch_size = 2
        seq_len = 8
        x = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = block(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert output.shape == x.shape

    def test_adaln_modulation(self) -> None:
        """Test that modulation vector affects output."""
        dim = 256
        n_heads = 8
        block = JointTransformerBlock(layer_id=0, dim=dim, n_heads=n_heads)
        
        batch_size = 1
        seq_len = 8
        x = torch.randn(batch_size, seq_len, dim)
        adaln1 = torch.randn(batch_size, dim)
        adaln2 = torch.randn(batch_size, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        out1 = block(x.clone(), x_mask=None, freqs_cis=freqs_cis, adaln_input=adaln1)
        out2 = block(x.clone(), x_mask=None, freqs_cis=freqs_cis, adaln_input=adaln2)
        
        # Different modulation should produce different outputs
        assert not torch.allclose(out1, out2)

    def test_no_nan_output(self) -> None:
        """Test no NaN in output."""
        dim = 256
        n_heads = 8
        block = JointTransformerBlock(layer_id=0, dim=dim, n_heads=n_heads)
        
        batch_size = 2
        seq_len = 16
        x = torch.randn(batch_size, seq_len, dim)
        adaln_input = torch.randn(batch_size, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = block(x, x_mask=None, freqs_cis=freqs_cis, adaln_input=adaln_input)
        
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    def test_gradient_flow(self) -> None:
        """Test that gradients flow through the block."""
        dim = 128
        n_heads = 4
        block = JointTransformerBlock(layer_id=0, dim=dim, n_heads=n_heads, modulation=False)
        
        batch_size = 1
        seq_len = 4
        x = torch.randn(batch_size, seq_len, dim, requires_grad=True)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        output = block(x, x_mask=None, freqs_cis=freqs_cis)
        loss = output.sum()
        loss.backward()
        
        assert x.grad is not None
        assert not torch.isnan(x.grad).any()

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self) -> None:
        """Test transformer block on CUDA."""
        dim = 128
        n_heads = 4
        block = JointTransformerBlock(
            layer_id=0, dim=dim, n_heads=n_heads, modulation=False
        ).cuda()
        
        batch_size = 2
        seq_len = 8
        x = torch.randn(batch_size, seq_len, dim, device="cuda")
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads).cuda()
        
        output = block(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert output.device.type == "cuda"
        assert output.shape == x.shape

    def test_eval_mode(self) -> None:
        """Test block in eval mode produces deterministic output."""
        dim = 128
        n_heads = 4
        block = JointTransformerBlock(
            layer_id=0, dim=dim, n_heads=n_heads, modulation=False
        )
        block.eval()
        
        batch_size = 1
        seq_len = 4
        x = torch.randn(batch_size, seq_len, dim)
        freqs_cis = self._make_freqs_cis(batch_size, seq_len, dim // n_heads)
        
        out1 = block(x, x_mask=None, freqs_cis=freqs_cis)
        out2 = block(x, x_mask=None, freqs_cis=freqs_cis)
        
        assert torch.allclose(out1, out2)
