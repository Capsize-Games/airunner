"""Unit tests for FlowMatchEulerScheduler.

Tests the flow matching scheduler for Z-Image generation.
"""

import pytest
import torch

from airunner.components.art.managers.zimage.native.flow_match_scheduler import (
    FlowMatchEulerScheduler,
)


class TestFlowMatchEulerScheduler:
    """Tests for FlowMatchEulerScheduler class."""

    def test_creation_default_params(self) -> None:
        """Test scheduler creation with default parameters."""
        scheduler = FlowMatchEulerScheduler()
        
        assert scheduler.num_train_timesteps == 1000
        assert scheduler.shift == 3.0
        assert scheduler.num_inference_steps is None

    def test_creation_custom_params(self) -> None:
        """Test scheduler creation with custom parameters."""
        scheduler = FlowMatchEulerScheduler(
            num_train_timesteps=500,
            shift=2.0
        )
        
        assert scheduler.num_train_timesteps == 500
        assert scheduler.shift == 2.0

    def test_set_timesteps_basic(self) -> None:
        """Test setting timesteps for inference."""
        scheduler = FlowMatchEulerScheduler()
        
        scheduler.set_timesteps(10)
        
        assert scheduler.num_inference_steps == 10
        assert scheduler.timesteps is not None
        assert len(scheduler.timesteps) == 10
        assert scheduler.sigmas is not None
        # Sigmas should have one more element (terminal sigma)
        assert len(scheduler.sigmas) == 11

    def test_timesteps_decreasing(self) -> None:
        """Test that timesteps are in decreasing order."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(20)
        
        timesteps = scheduler.timesteps
        for i in range(len(timesteps) - 1):
            assert timesteps[i] > timesteps[i + 1]

    def test_sigmas_decreasing(self) -> None:
        """Test that sigmas decrease from ~1 to 0."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(20)
        
        sigmas = scheduler.sigmas
        
        # First sigma should be close to 1
        assert sigmas[0] > 0.9
        # Last sigma should be 0
        assert sigmas[-1] == 0.0
        # Should be monotonically decreasing
        for i in range(len(sigmas) - 1):
            assert sigmas[i] >= sigmas[i + 1]

    def test_shift_affects_sigmas(self) -> None:
        """Test that shift parameter affects sigma distribution."""
        scheduler_low_shift = FlowMatchEulerScheduler(shift=1.0)
        scheduler_high_shift = FlowMatchEulerScheduler(shift=5.0)
        
        scheduler_low_shift.set_timesteps(10)
        scheduler_high_shift.set_timesteps(10)
        
        # Different shifts should produce different sigma schedules
        assert not torch.allclose(
            scheduler_low_shift.sigmas,
            scheduler_high_shift.sigmas
        )

    def test_step_shape_preservation(self) -> None:
        """Test that step preserves tensor shapes."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(4)
        
        batch_size = 2
        channels = 16
        height = 8
        width = 8
        
        model_output = torch.randn(batch_size, channels, height, width)
        sample = torch.randn(batch_size, channels, height, width)
        
        result = scheduler.step(
            model_output=model_output,
            timestep=0,  # First step
            sample=sample
        )
        
        assert result.prev_sample.shape == sample.shape

    def test_step_denoising_progress(self) -> None:
        """Test that stepping reduces noise level."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(10)
        
        # Create noisy sample
        sample = torch.randn(1, 4, 8, 8)
        
        # Simulate denoising steps
        for i, t in enumerate(scheduler.timesteps):
            # Mock model output (predicting velocity)
            model_output = torch.randn_like(sample)
            result = scheduler.step(model_output, i, sample)
            sample = result.prev_sample
        
        # After all steps, should have some output
        assert sample.shape == (1, 4, 8, 8)
        assert not torch.isnan(sample).any()

    def test_add_noise(self) -> None:
        """Test adding noise to samples."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(10)
        
        original = torch.zeros(1, 4, 8, 8)
        noise = torch.ones(1, 4, 8, 8)
        
        # Add noise at first timestep (sigma near 1)
        noised = scheduler.add_noise(original, noise, timesteps=torch.tensor([0]))
        
        # Should be mostly noise
        assert noised.mean().abs() > 0.5

    def test_add_noise_at_end(self) -> None:
        """Test that noise scales correctly at different timesteps."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(10)
        
        original = torch.ones(1, 4, 8, 8)
        noise = torch.randn(1, 4, 8, 8)
        
        # At timestep 9 (second to last), sigma is 0.25
        # noised = (1 - sigma) * original + sigma * noise
        # noised = 0.75 * original + 0.25 * noise
        noised = scheduler.add_noise(original, noise, timesteps=torch.tensor([9]))
        
        # The mean should be closer to original (0.75 weight) than noise
        expected = 0.75 * original + 0.25 * noise
        assert torch.allclose(noised, expected, atol=1e-5)

    def test_device_handling(self) -> None:
        """Test scheduler works on CPU."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(5, device="cpu")
        
        assert scheduler.timesteps.device.type == "cpu"
        assert scheduler.sigmas.device.type == "cpu"

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
    def test_cuda_device(self) -> None:
        """Test scheduler works on CUDA."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(5, device="cuda:0")
        
        assert scheduler.timesteps.device.type == "cuda"
        assert scheduler.sigmas.device.type == "cuda"

    def test_scale_noise_no_nan(self) -> None:
        """Test that scaling noise doesn't produce NaN."""
        scheduler = FlowMatchEulerScheduler()
        scheduler.set_timesteps(20)
        
        sample = torch.randn(1, 16, 4, 4)
        noise = torch.randn(1, 16, 4, 4)
        
        for i in range(len(scheduler.timesteps)):
            sigma = scheduler.sigmas[i]
            scaled = scheduler.scale_noise(sample, sigma, noise)
            assert not torch.isnan(scaled).any()
            assert not torch.isinf(scaled).any()
