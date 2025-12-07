"""Unit tests for embedder modules.

Tests TimestepEmbedder and EmbedND (RoPE) embeddings.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.embedders import (
    TimestepEmbedder,
    EmbedND,
)


class TestTimestepEmbedder:
    """Tests for TimestepEmbedder class."""

    def test_creation(self) -> None:
        """Test creating timestep embedder."""
        embedder = TimestepEmbedder(hidden_size=256)
        
        assert embedder.frequency_embedding_size == 256
        assert embedder.mlp is not None

    def test_forward_shape(self) -> None:
        """Test forward produces correct shape."""
        hidden_size = 256
        embedder = TimestepEmbedder(hidden_size=hidden_size)
        
        # Batch of timesteps
        t = torch.tensor([0.1, 0.5, 0.9])
        
        output = embedder(t)
        
        assert output.shape == (3, hidden_size)

    def test_forward_single_timestep(self) -> None:
        """Test forward with single timestep."""
        hidden_size = 128
        embedder = TimestepEmbedder(hidden_size=hidden_size)
        
        t = torch.tensor([0.5])
        
        output = embedder(t)
        
        assert output.shape == (1, hidden_size)

    def test_different_timesteps_different_embeddings(self) -> None:
        """Test that different timesteps produce different embeddings."""
        embedder = TimestepEmbedder(hidden_size=256)
        
        t1 = torch.tensor([0.1])
        t2 = torch.tensor([0.9])
        
        emb1 = embedder(t1)
        emb2 = embedder(t2)
        
        # Embeddings should be different
        assert not torch.allclose(emb1, emb2)

    def test_no_nan_output(self) -> None:
        """Test that output doesn't contain NaN."""
        embedder = TimestepEmbedder(hidden_size=256)
        
        # Test range of timesteps
        t = torch.linspace(0, 1, 10)
        
        output = embedder(t)
        
        assert not torch.isnan(output).any()
        assert not torch.isinf(output).any()

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self) -> None:
        """Test embedder on CUDA."""
        embedder = TimestepEmbedder(hidden_size=256).cuda()
        t = torch.tensor([0.5], device="cuda")
        
        output = embedder(t)
        
        assert output.device.type == "cuda"


class TestEmbedND:
    """Tests for EmbedND (RoPE) class."""

    def test_creation(self) -> None:
        """Test creating ND embedder."""
        embedder = EmbedND(dim=128, theta=10000.0, axes_dim=[16, 56, 56])
        
        assert embedder.dim == 128
        assert embedder.theta == 10000.0

    def test_forward_3d_ids(self) -> None:
        """Test forward with 3D position IDs (time, height, width)."""
        # axes_dim specifies dimension for each axis
        embedder = EmbedND(dim=128, theta=10000.0, axes_dim=[16, 56, 56])
        
        batch_size = 2
        seq_len = 64
        # 3D position IDs: [batch, seq, 3] for (time, h, w)
        ids = torch.randint(0, 32, (batch_size, seq_len, 3))
        
        output = embedder(ids)
        
        # RoPE output is concatenated rotation matrices along axes
        # Shape: (batch, seq, 1, n_axes * axes_dim/2, 2, 2)
        assert output.ndim == 6
        assert output.shape[0] == batch_size
        assert output.shape[1] == seq_len
        assert output.shape[2] == 1  # unsqueeze(2)
        # Final dimensions are rotation matrix (2, 2)
        assert output.shape[-2:] == (2, 2)

    def test_output_normalized(self) -> None:
        """Test that output values are reasonable."""
        embedder = EmbedND(dim=64, theta=10000.0, axes_dim=[16, 24, 24])
        
        ids = torch.zeros(1, 16, 3, dtype=torch.long)
        
        output = embedder(ids)
        
        # RoPE embeddings should be in reasonable range
        assert output.abs().max() < 100
        assert not torch.isnan(output).any()

    def test_different_positions_different_embeddings(self) -> None:
        """Test that different positions produce different embeddings."""
        embedder = EmbedND(dim=64, theta=10000.0, axes_dim=[16, 24, 24])
        
        ids1 = torch.tensor([[[0, 0, 0]]])  # Origin
        ids2 = torch.tensor([[[1, 5, 5]]])  # Different position
        
        emb1 = embedder(ids1)
        emb2 = embedder(ids2)
        
        assert not torch.allclose(emb1, emb2)

    def test_batch_consistency(self) -> None:
        """Test that batched computation matches individual."""
        embedder = EmbedND(dim=64, theta=10000.0, axes_dim=[16, 24, 24])
        
        # Single sample
        ids_single = torch.tensor([[[0, 1, 2], [1, 2, 3]]])
        emb_single = embedder(ids_single)
        
        # Batched (same data duplicated)
        ids_batch = torch.tensor([
            [[0, 1, 2], [1, 2, 3]],
            [[0, 1, 2], [1, 2, 3]]
        ])
        emb_batch = embedder(ids_batch)
        
        # Both samples should match single
        assert torch.allclose(emb_batch[0], emb_single[0])
        assert torch.allclose(emb_batch[1], emb_single[0])

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda(self) -> None:
        """Test embedder on CUDA."""
        embedder = EmbedND(dim=64, theta=10000.0, axes_dim=[16, 24, 24]).cuda()
        ids = torch.zeros(1, 8, 3, dtype=torch.long, device="cuda")
        
        output = embedder(ids)
        
        assert output.device.type == "cuda"
