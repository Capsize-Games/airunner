"""Unit tests for NextDiT model.

Tests the complete NextDiT transformer for Z-Image.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.nextdit_model import (
    NextDiT,
    ZIMAGE_CONFIG,
)


class TestNextDiTConfig:
    """Tests for Z-Image configuration."""

    def test_config_values(self) -> None:
        """Test configuration has expected values."""
        assert ZIMAGE_CONFIG["dim"] == 3840
        assert ZIMAGE_CONFIG["n_layers"] == 32
        assert ZIMAGE_CONFIG["n_heads"] == 30
        assert ZIMAGE_CONFIG["n_kv_heads"] == 6
        assert ZIMAGE_CONFIG["multiple_of"] == 256
        assert ZIMAGE_CONFIG["ffn_dim_multiplier"] == 1.3
        assert ZIMAGE_CONFIG["context_processor_layers"] == 2


class TestNextDiT:
    """Tests for NextDiT model class."""

    @pytest.fixture
    def small_model(self) -> NextDiT:
        """Create a small model for testing."""
        return NextDiT(
            dim=64,
            n_layers=2,
            n_heads=4,
            n_kv_heads=2,
            context_processor_layers=1,
            in_channels=16,
            out_channels=16,
            context_dim=64,
            multiple_of=32,
            ffn_dim_multiplier=1.0
        )

    def test_creation(self, small_model: NextDiT) -> None:
        """Test model creation."""
        assert small_model is not None
        assert small_model.dim == 64
        assert small_model.n_layers == 2

    def test_parameter_count(self, small_model: NextDiT) -> None:
        """Test parameter counting."""
        params = sum(p.numel() for p in small_model.parameters())
        assert params > 0

    def test_forward_shape(self, small_model: NextDiT) -> None:
        """Test forward produces correct output shape."""
        batch_size = 1
        height = 8
        width = 8
        channels = 16
        ctx_len = 4
        
        x = torch.randn(batch_size, height * width, channels)
        t = torch.tensor([0.5])  # Timestep
        context = torch.randn(batch_size, ctx_len, 64)  # Text embeddings
        x_ids = torch.zeros(batch_size, height * width, 3, dtype=torch.long)
        context_ids = torch.zeros(batch_size, ctx_len, 3, dtype=torch.long)
        
        output = small_model(x, t, context, x_ids, context_ids)
        
        assert output.shape == x.shape

    def test_different_timesteps(self, small_model: NextDiT) -> None:
        """Test that different timesteps produce different outputs."""
        x = torch.randn(1, 64, 16)
        context = torch.randn(1, 4, 64)
        x_ids = torch.zeros(1, 64, 3, dtype=torch.long)
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long)
        
        t1 = torch.tensor([0.1])
        t2 = torch.tensor([0.9])
        
        out1 = small_model(x, t1, context, x_ids, context_ids)
        out2 = small_model(x, t2, context, x_ids, context_ids)
        
        assert not torch.allclose(out1, out2)

    def test_different_contexts(self, small_model: NextDiT) -> None:
        """Test that different contexts produce different outputs."""
        x = torch.randn(1, 64, 16)
        t = torch.tensor([0.5])
        x_ids = torch.zeros(1, 64, 3, dtype=torch.long)
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long)
        
        ctx1 = torch.randn(1, 4, 64)
        ctx2 = torch.randn(1, 4, 64)
        
        out1 = small_model(x, t, ctx1, x_ids, context_ids)
        out2 = small_model(x, t, ctx2, x_ids, context_ids)
        
        assert not torch.allclose(out1, out2)

    def test_no_nan_output(self, small_model: NextDiT) -> None:
        """Test no NaN in output."""
        x = torch.randn(1, 32, 16)
        t = torch.tensor([0.5])
        context = torch.randn(1, 4, 64)
        x_ids = torch.zeros(1, 32, 3, dtype=torch.long)
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long)
        
        output = small_model(x, t, context, x_ids, context_ids)
        
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    def test_batch_processing(self, small_model: NextDiT) -> None:
        """Test processing multiple samples in batch."""
        batch_size = 4
        x = torch.randn(batch_size, 32, 16)
        t = torch.tensor([0.2, 0.4, 0.6, 0.8])
        context = torch.randn(batch_size, 4, 64)
        x_ids = torch.zeros(batch_size, 32, 3, dtype=torch.long)
        context_ids = torch.zeros(batch_size, 4, 3, dtype=torch.long)
        
        output = small_model(x, t, context, x_ids, context_ids)
        
        assert output.shape == (batch_size, 32, 16)

    def test_eval_mode_deterministic(self, small_model: NextDiT) -> None:
        """Test model in eval mode is deterministic."""
        small_model.eval()
        
        x = torch.randn(1, 16, 16)
        t = torch.tensor([0.5])
        context = torch.randn(1, 4, 64)
        x_ids = torch.zeros(1, 16, 3, dtype=torch.long)
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long)
        
        out1 = small_model(x, t, context, x_ids, context_ids)
        out2 = small_model(x, t, context, x_ids, context_ids)
        
        assert torch.allclose(out1, out2)

    def test_gradient_flow(self, small_model: NextDiT) -> None:
        """Test that gradients flow through the model."""
        x = torch.randn(1, 16, 16, requires_grad=True)
        t = torch.tensor([0.5])
        context = torch.randn(1, 4, 64, requires_grad=True)
        x_ids = torch.zeros(1, 16, 3, dtype=torch.long)
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long)
        
        output = small_model(x, t, context, x_ids, context_ids)
        loss = output.sum()
        loss.backward()
        
        assert x.grad is not None
        assert context.grad is not None

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self, small_model: NextDiT) -> None:
        """Test model on CUDA."""
        model = small_model.cuda()
        
        x = torch.randn(1, 32, 16, device="cuda")
        t = torch.tensor([0.5], device="cuda")
        context = torch.randn(1, 4, 64, device="cuda")
        x_ids = torch.zeros(1, 32, 3, dtype=torch.long, device="cuda")
        context_ids = torch.zeros(1, 4, 3, dtype=torch.long, device="cuda")
        
        output = model(x, t, context, x_ids, context_ids)
        
        assert output.device.type == "cuda"


class TestNextDiTFullConfig:
    """Tests for full Z-Image configuration (resource intensive)."""

    @pytest.mark.slow
    def test_full_config_creation(self) -> None:
        """Test creating model with full Z-Image config."""
        # This test is slow and memory intensive
        model = NextDiT(**ZIMAGE_CONFIG)
        
        # Check parameter count is approximately correct
        params = sum(p.numel() for p in model.parameters())
        # Should be around 8.64B for Z-Image
        assert params > 8_000_000_000
        assert params < 9_000_000_000
