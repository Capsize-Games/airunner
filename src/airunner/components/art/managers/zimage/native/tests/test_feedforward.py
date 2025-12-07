"""Unit tests for feedforward module.

Tests SiLU-gated FeedForward network.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.feedforward import (
    FeedForward,
)


class TestFeedForward:
    """Tests for FeedForward class."""

    def test_creation_default(self) -> None:
        """Test creating feedforward with default settings."""
        ff = FeedForward(dim=256)
        
        # Should have all three linear layers
        assert ff.w1 is not None
        assert ff.w2 is not None
        assert ff.w3 is not None

    def test_creation_custom_hidden_dim(self) -> None:
        """Test creating feedforward with custom hidden dimension."""
        ff = FeedForward(dim=128, hidden_dim=512, ffn_dim_multiplier=1.0)
        
        # With multiple_of=256 default, 512 stays 512
        assert ff.w1.out_features == 512

    def test_forward_shape(self) -> None:
        """Test forward preserves input shape."""
        ff = FeedForward(dim=256)
        
        batch_size = 2
        seq_len = 16
        x = torch.randn(batch_size, seq_len, 256)
        
        output = ff(x)
        
        assert output.shape == x.shape

    def test_forward_2d_input(self) -> None:
        """Test forward with 2D input."""
        ff = FeedForward(dim=128)
        x = torch.randn(8, 128)
        
        output = ff(x)
        
        assert output.shape == (8, 128)

    def test_forward_4d_input(self) -> None:
        """Test forward with 4D input (spatial)."""
        ff = FeedForward(dim=64)
        x = torch.randn(2, 4, 4, 64)  # Batch, H, W, C
        
        output = ff(x)
        
        assert output.shape == (2, 4, 4, 64)

    def test_different_inputs_different_outputs(self) -> None:
        """Test that different inputs produce different outputs."""
        ff = FeedForward(dim=128)
        
        x1 = torch.randn(1, 8, 128)
        x2 = torch.randn(1, 8, 128)
        
        out1 = ff(x1)
        out2 = ff(x2)
        
        assert not torch.allclose(out1, out2)

    def test_no_nan_output(self) -> None:
        """Test no NaN in output."""
        ff = FeedForward(dim=256)
        x = torch.randn(2, 16, 256)
        
        output = ff(x)
        
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    def test_silu_gating(self) -> None:
        """Test that SiLU gating is applied (output differs from simple linear)."""
        ff = FeedForward(dim=64)
        
        # SiLU gating should make output different from simple MLP
        x = torch.ones(1, 4, 64)
        output = ff(x)
        
        # Output should not be uniform due to gating
        assert output.std() > 0

    def test_large_batch(self) -> None:
        """Test with large batch size."""
        ff = FeedForward(dim=128)
        x = torch.randn(64, 32, 128)
        
        output = ff(x)
        
        assert output.shape == x.shape

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self) -> None:
        """Test feedforward on CUDA."""
        ff = FeedForward(dim=256).cuda()
        x = torch.randn(2, 8, 256, device="cuda")
        
        output = ff(x)
        
        assert output.device.type == "cuda"
        assert output.shape == x.shape

    def test_gradient_flow(self) -> None:
        """Test that gradients flow through the layer."""
        ff = FeedForward(dim=64)
        x = torch.randn(2, 4, 64, requires_grad=True)
        
        output = ff(x)
        loss = output.sum()
        loss.backward()
        
        assert x.grad is not None
        assert not torch.isnan(x.grad).any()
