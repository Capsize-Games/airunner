"""
Flow Matching Euler Scheduler for Z-Image.

This implements the flow matching discrete scheduler used by Z-Image Turbo,
with a shift parameter for better sample quality.

Based on diffusers FlowMatchEulerDiscreteScheduler with Z-Image specific settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union

import torch
import numpy as np


@dataclass
class FlowMatchSchedulerOutput:
    """Output from scheduler step."""
    
    prev_sample: torch.Tensor
    """Previous sample (x_{t-1})."""
    
    pred_original_sample: Optional[torch.Tensor] = None
    """Predicted denoised sample (x_0)."""


class FlowMatchEulerScheduler:
    """
    Flow matching Euler discrete scheduler.
    
    This scheduler implements the flow matching sampling method used by
    Z-Image and similar models. It uses a shifted sigma schedule for
    improved sample quality.
    
    Args:
        num_train_timesteps: Number of training timesteps
        shift: Shift parameter for sigma schedule (Z-Image uses 3.0)
        base_shift: Base shift (default 0.5)
        max_shift: Maximum shift (default 1.15)
        base_image_seq_len: Base sequence length for shift calculation
        max_image_seq_len: Max sequence length for shift calculation
        invert_sigmas: Whether to invert sigma schedule
    """
    
    def __init__(
        self,
        num_train_timesteps: int = 1000,
        shift: float = 3.0,
        base_shift: float = 0.5,
        max_shift: float = 1.15,
        base_image_seq_len: int = 256,
        max_image_seq_len: int = 4096,
        invert_sigmas: bool = False,
    ):
        self.num_train_timesteps = num_train_timesteps
        self.shift = shift
        self.base_shift = base_shift
        self.max_shift = max_shift
        self.base_image_seq_len = base_image_seq_len
        self.max_image_seq_len = max_image_seq_len
        self.invert_sigmas = invert_sigmas
        
        # Will be set by set_timesteps
        self.timesteps: Optional[torch.Tensor] = None
        self.sigmas: Optional[torch.Tensor] = None
        self.num_inference_steps: Optional[int] = None
        self._step_index: Optional[int] = None
    
    @property
    def step_index(self) -> Optional[int]:
        """Current step index."""
        return self._step_index
    
    @property
    def init_noise_sigma(self) -> float:
        """Initial noise sigma for the first timestep."""
        return 1.0
    
    def _sigma_to_t(self, sigma: torch.Tensor) -> torch.Tensor:
        """Convert sigma to timestep."""
        return sigma * self.num_train_timesteps
    
    def _compute_shift(self, image_seq_len: int) -> float:
        """
        Compute shift based on image sequence length.
        
        For Z-Image, we typically use a fixed shift of 3.0.
        """
        if self.shift is not None:
            return self.shift
        
        # Dynamic shift calculation based on resolution
        m = (self.max_shift - self.base_shift) / (
            self.max_image_seq_len - self.base_image_seq_len
        )
        b = self.base_shift - m * self.base_image_seq_len
        mu = image_seq_len * m + b
        return mu
    
    def set_timesteps(
        self,
        num_inference_steps: int,
        device: Union[str, torch.device] = "cpu",
        sigmas: Optional[torch.Tensor] = None,
        mu: Optional[float] = None,
    ):
        """
        Set the discrete timesteps for inference.
        
        Args:
            num_inference_steps: Number of denoising steps
            device: Target device
            sigmas: Optional custom sigma schedule
            mu: Optional shift override
        """
        self.num_inference_steps = num_inference_steps
        
        if sigmas is not None:
            # Use provided sigmas
            sigmas = sigmas.to(dtype=torch.float32, device=device)
        else:
            # Generate linear sigma schedule
            sigmas = torch.linspace(
                1.0, 0.0, num_inference_steps + 1, device=device, dtype=torch.float32
            )
        
        # Apply shift transformation
        shift = mu if mu is not None else self.shift
        if shift is not None:
            sigmas = shift * sigmas / (1 + (shift - 1) * sigmas)
        
        if self.invert_sigmas:
            sigmas = 1.0 - sigmas
        
        self.sigmas = sigmas
        self.timesteps = self._sigma_to_t(sigmas[:-1])
        
        self._step_index = None
    
    def scale_noise(
        self,
        sample: torch.Tensor,
        timestep: torch.Tensor,
        noise: torch.Tensor,
    ) -> torch.Tensor:
        """
        Scale the noise according to flow matching formula.
        
        For flow matching: x_t = (1 - sigma) * x_0 + sigma * noise
        
        Args:
            sample: Original sample (x_0)
            timestep: Current timestep/sigma
            noise: Random noise
            
        Returns:
            Noised sample
        """
        sigma = timestep
        if sigma.ndim == 0:
            sigma = sigma.unsqueeze(0)
        
        # Ensure proper broadcasting
        while sigma.ndim < sample.ndim:
            sigma = sigma.unsqueeze(-1)
        
        noised_sample = (1.0 - sigma) * sample + sigma * noise
        return noised_sample
    
    def step(
        self,
        model_output: torch.Tensor,
        timestep: Union[int, torch.Tensor],
        sample: torch.Tensor,
        return_dict: bool = True,
    ) -> Union[FlowMatchSchedulerOutput, torch.Tensor]:
        """
        Perform one denoising step.
        
        This implements the Euler step for flow matching:
        x_{t-1} = x_t + (sigma_{t-1} - sigma_t) * v_t
        
        Where v_t is the velocity prediction from the model.
        
        Args:
            model_output: Predicted velocity from model
            timestep: Current timestep
            sample: Current sample
            return_dict: Whether to return FlowMatchSchedulerOutput (default True)
            
        Returns:
            FlowMatchSchedulerOutput with prev_sample, or just the tensor if return_dict=False
        """
        # Get current step index
        if self._step_index is None:
            self._step_index = 0
        
        # Get current and next sigma
        sigma = self.sigmas[self._step_index]
        sigma_next = self.sigmas[self._step_index + 1]
        
        # Euler step using ComfyUI CONST formula:
        # Model predicts velocity v. After pipeline negation, model_output = -(clean - noise) = noise - clean
        # ComfyUI formula: x_new = x + model_output * dt
        # Where dt = sigma_next - sigma < 0 during denoising
        # So: x_new = x + (noise - clean) * (negative) = x - (noise - clean) * |dt|
        #           = x + (clean - noise) * |dt| → moves toward clean ✓
        dt = sigma_next - sigma
        prev_sample = sample + model_output * dt  # ComfyUI: x = x + d * dt
        
        # Increment step index
        self._step_index += 1
        
        if return_dict:
            # Compute predicted original sample
            denoised = sample - sigma * model_output
            return FlowMatchSchedulerOutput(
                prev_sample=prev_sample,
                pred_original_sample=denoised
            )
        
        return prev_sample
    
    def add_noise(
        self,
        original_samples: torch.Tensor,
        noise: torch.Tensor,
        timesteps: torch.Tensor,
    ) -> torch.Tensor:
        """
        Add noise to samples for training.
        
        Args:
            original_samples: Clean samples
            noise: Random noise
            timesteps: Timestep indices
            
        Returns:
            Noised samples
        """
        sigmas = self.sigmas[timesteps.long()]
        
        while sigmas.ndim < original_samples.ndim:
            sigmas = sigmas.unsqueeze(-1)
        
        noisy_samples = (1.0 - sigmas) * original_samples + sigmas * noise
        return noisy_samples
    
    def get_velocity(
        self,
        sample: torch.Tensor,
        noise: torch.Tensor,
        timesteps: torch.Tensor,
    ) -> torch.Tensor:
        """
        Get velocity targets for training.
        
        For flow matching: v = noise - sample
        
        Args:
            sample: Clean samples
            noise: Random noise
            timesteps: Timestep indices (unused for flow matching)
            
        Returns:
            Velocity targets
        """
        return noise - sample


class FlowMatchHeunScheduler(FlowMatchEulerScheduler):
    """
    Flow matching with Heun's method (2nd order).
    
    This provides higher quality samples at the cost of 2x model evaluations.
    """
    
    def step(
        self,
        model_output: torch.Tensor,
        timestep: Union[int, torch.Tensor],
        sample: torch.Tensor,
        model_fn: Optional[callable] = None,
        return_dict: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Perform one Heun step.
        
        Args:
            model_output: Predicted velocity from model
            timestep: Current timestep
            sample: Current sample
            model_fn: Model function for second evaluation
            return_dict: Whether to return additional info
            
        Returns:
            Denoised sample
        """
        if model_fn is None:
            # Fall back to Euler step
            return super().step(model_output, timestep, sample, return_dict)
        
        # Get current step index
        if self._step_index is None:
            self._step_index = 0
        
        sigma = self.sigmas[self._step_index]
        sigma_next = self.sigmas[self._step_index + 1]
        
        # First Euler step
        dt = sigma_next - sigma
        sample_pred = sample + model_output * dt
        
        # Second evaluation at predicted point
        if sigma_next > 0:
            model_output_2 = model_fn(sample_pred, sigma_next)
            
            # Heun correction
            prev_sample = sample + 0.5 * dt * (model_output + model_output_2)
        else:
            prev_sample = sample_pred
        
        self._step_index += 1
        
        if return_dict:
            denoised = sample - sigma * model_output
            return prev_sample, denoised
        
        return prev_sample
