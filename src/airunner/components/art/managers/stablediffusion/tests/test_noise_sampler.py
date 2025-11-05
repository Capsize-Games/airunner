"""
Unit tests for DeterministicSDENoiseSampler.

This module tests the deterministic noise sampling functionality used
for DPM++ SDE schedulers to ensure consistent results across batches.
"""

import pytest
import torch

from airunner.components.art.managers.stablediffusion.noise_sampler import (
    DeterministicSDENoiseSampler,
)


class TestDeterministicSDENoiseSampler:
    """Test suite for DeterministicSDENoiseSampler class."""

    def test_sampler_initialization(self):
        """Test that sampler initializes with seed and device."""
        seed = 42
        device = torch.device("cpu")

        sampler = DeterministicSDENoiseSampler(seed=seed, device=device)

        assert sampler.seed == seed
        assert sampler.device == device
        assert sampler.generator is not None
        assert isinstance(sampler.generator, torch.Generator)

    def test_deterministic_output_with_same_seed(self):
        """Test that same seed produces identical noise."""
        seed = 12345
        shape = (1, 4, 64, 64)
        device = torch.device("cpu")

        # Create two samplers with same seed
        sampler1 = DeterministicSDENoiseSampler(seed=seed, device=device)
        sampler2 = DeterministicSDENoiseSampler(seed=seed, device=device)

        # Generate noise from both
        noise1 = sampler1(shape)
        noise2 = sampler2(shape)

        # Noise should be identical
        assert torch.allclose(noise1, noise2)

    def test_different_seeds_produce_different_noise(self):
        """Test that different seeds produce different noise."""
        shape = (1, 4, 64, 64)
        device = torch.device("cpu")

        sampler1 = DeterministicSDENoiseSampler(seed=111, device=device)
        sampler2 = DeterministicSDENoiseSampler(seed=222, device=device)

        noise1 = sampler1(shape)
        noise2 = sampler2(shape)

        # Noise should be different
        assert not torch.allclose(noise1, noise2)

    def test_default_dtype_is_float32(self):
        """Test that default dtype is torch.float32."""
        sampler = DeterministicSDENoiseSampler(
            seed=42, device=torch.device("cpu")
        )

        noise = sampler(shape=(1, 4, 8, 8))

        assert noise.dtype == torch.float32

    def test_custom_dtype(self):
        """Test that custom dtype is respected."""
        sampler = DeterministicSDENoiseSampler(
            seed=42, device=torch.device("cpu")
        )

        noise = sampler(shape=(1, 4, 8, 8), dtype=torch.float16)

        assert noise.dtype == torch.float16

    def test_output_shape(self):
        """Test that output has correct shape."""
        sampler = DeterministicSDENoiseSampler(
            seed=42, device=torch.device("cpu")
        )

        batch_size = 2
        channels = 4
        height = 64
        width = 64
        shape = (batch_size, channels, height, width)

        noise = sampler(shape)

        assert noise.shape == shape

    def test_multiple_calls_same_sampler_produce_different_noise(self):
        """Test that calling same sampler multiple times gives different results."""
        sampler = DeterministicSDENoiseSampler(
            seed=42, device=torch.device("cpu")
        )

        shape = (1, 4, 8, 8)
        noise1 = sampler(shape)
        noise2 = sampler(shape)

        # Different calls should produce different noise
        # (generator state advances)
        assert not torch.allclose(noise1, noise2)

    def test_noise_distribution(self):
        """Test that noise follows approximately normal distribution."""
        sampler = DeterministicSDENoiseSampler(
            seed=42, device=torch.device("cpu")
        )

        # Generate large sample
        noise = sampler(shape=(1000, 4, 32, 32))

        # Check mean is close to 0
        assert abs(noise.mean().item()) < 0.1

        # Check std is close to 1
        assert abs(noise.std().item() - 1.0) < 0.1

    @pytest.mark.skipif(
        not torch.cuda.is_available(), reason="CUDA not available"
    )
    def test_cuda_device(self):
        """Test that sampler works with CUDA device."""
        device = torch.device("cuda")
        sampler = DeterministicSDENoiseSampler(seed=42, device=device)

        noise = sampler(shape=(1, 4, 8, 8))

        assert noise.device.type == "cuda"

    def test_consistency_across_batch_sizes(self):
        """Test that noise is consistent when generating in different batch sizes."""
        seed = 99999
        device = torch.device("cpu")

        # Generate single batch
        sampler1 = DeterministicSDENoiseSampler(seed=seed, device=device)
        noise_single = sampler1(shape=(1, 4, 8, 8))

        # Generate batch of 2, take first item
        sampler2 = DeterministicSDENoiseSampler(seed=seed, device=device)
        noise_batch = sampler2(shape=(2, 4, 8, 8))

        # First item in batch should match single generation
        assert torch.allclose(noise_single, noise_batch[0:1])
