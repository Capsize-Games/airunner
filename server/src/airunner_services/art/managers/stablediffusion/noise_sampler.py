"""
Noise sampler utilities for Stable Diffusion.

This module provides deterministic noise sampling for DPM++ SDE schedulers
to ensure consistent results across different batch sizes.
"""

import torch


class DeterministicSDENoiseSampler:
    """
    Deterministic noise sampler for DPM++ SDE schedulers.

    Ensures consistent results across different batch sizes by using
    per-seed generators for noise sampling, similar to AUTOMATIC1111's
    BrownianTreeNoiseSampler approach.

    Args:
        seed: Random seed for noise generation
        device: PyTorch device for tensor allocation

    Example:
        >>> sampler = DeterministicSDENoiseSampler(seed=42, device="cuda")
        >>> noise = sampler(shape=(1, 4, 64, 64), dtype=torch.float16)
    """

    def __init__(self, seed: int, device: torch.device):
        """Initialize the noise sampler with a seed and device."""
        self.seed = seed
        self.device = device
        self.generator = torch.Generator(device=device).manual_seed(seed)

    def __call__(self, shape, dtype=None):
        """
        Generate deterministic noise tensor.

        Args:
            shape: Shape of the noise tensor (batch, channels, height, width)
            dtype: PyTorch dtype for the tensor (default: torch.float32)

        Returns:
            torch.Tensor: Random noise tensor with the specified shape
        """
        if dtype is None:
            dtype = torch.float32
        return torch.randn(
            shape, generator=self.generator, device=self.device, dtype=dtype
        )
