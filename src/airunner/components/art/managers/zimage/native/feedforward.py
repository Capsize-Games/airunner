"""
FeedForward modules for NextDiT transformer.

This module provides the SiLU-gated feedforward network used in
Z-Image/Lumina2 architecture.
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


def clamp_fp16(x: torch.Tensor) -> torch.Tensor:
    """
    Clamp tensor values to prevent FP16 overflow.
    
    Args:
        x: Input tensor
        
    Returns:
        Clamped tensor (only affects FP16)
    """
    if x.dtype == torch.float16:
        return torch.nan_to_num(x, nan=0.0, posinf=65504, neginf=-65504)
    return x


class FeedForward(nn.Module):
    """
    SiLU-gated feedforward network.
    
    This implements the gated MLP used in Z-Image/Lumina2:
    output = w2(SiLU(w1(x)) * w3(x))
    
    Args:
        dim: Input/output dimension
        hidden_dim: Base hidden dimension (will be scaled)
        multiple_of: Ensure hidden dimension is multiple of this
        ffn_dim_multiplier: Multiplier for hidden dimension
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        dim: int,
        hidden_dim: int = None,
        multiple_of: int = 256,
        ffn_dim_multiplier: Optional[float] = None,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        # Calculate hidden dimension
        if hidden_dim is None:
            hidden_dim = dim
        
        if ffn_dim_multiplier is not None:
            hidden_dim = int(ffn_dim_multiplier * hidden_dim)
        
        # Round to multiple
        hidden_dim = multiple_of * ((hidden_dim + multiple_of - 1) // multiple_of)
        
        # Gated MLP layers
        self.w1 = nn.Linear(dim, hidden_dim, bias=False, device=device, dtype=dtype)
        self.w2 = nn.Linear(hidden_dim, dim, bias=False, device=device, dtype=dtype)
        self.w3 = nn.Linear(dim, hidden_dim, bias=False, device=device, dtype=dtype)
    
    def _forward_silu_gating(self, x1: torch.Tensor, x3: torch.Tensor) -> torch.Tensor:
        """
        Apply SiLU gating with FP16 clamping.
        
        Args:
            x1: Output of w1
            x3: Output of w3 (gate)
            
        Returns:
            Gated result
        """
        return clamp_fp16(F.silu(x1) * x3)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, S, D)
            
        Returns:
            Output tensor of shape (B, S, D)
        """
        return self.w2(self._forward_silu_gating(self.w1(x), self.w3(x)))


class MLPBlock(nn.Module):
    """
    Standard MLP block without gating.
    
    Simple feedforward: output = Linear(GELU(Linear(x)))
    
    Args:
        dim: Input/output dimension
        hidden_dim: Hidden layer dimension
        bias: Whether to use bias
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        dim: int,
        hidden_dim: int = None,
        bias: bool = True,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        if hidden_dim is None:
            hidden_dim = dim * 4
        
        self.fc1 = nn.Linear(dim, hidden_dim, bias=bias, device=device, dtype=dtype)
        self.fc2 = nn.Linear(hidden_dim, dim, bias=bias, device=device, dtype=dtype)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor
            
        Returns:
            Output tensor
        """
        x = self.fc1(x)
        x = F.gelu(x)
        x = self.fc2(x)
        return x
