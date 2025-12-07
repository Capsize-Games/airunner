"""
Embedder modules for NextDiT transformer.

This module provides timestep embedders and positional encoding
for the Z-Image transformer.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

import torch
import torch.nn as nn


class TimestepEmbedder(nn.Module):
    """
    Embeds scalar timesteps into vector representations.
    
    Uses sinusoidal positional encoding followed by MLP projection.
    
    Args:
        hidden_size: Dimension of the embedding
        frequency_embedding_size: Size of sinusoidal embedding (default: 256)
        output_size: Optional output projection size
        operations: Operation factory for layers
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        hidden_size: int,
        frequency_embedding_size: int = 256,
        output_size: Optional[int] = None,
        operations=None,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        self.mlp = nn.Sequential(
            nn.Linear(
                frequency_embedding_size,
                hidden_size,
                bias=True,
                device=device,
                dtype=dtype,
            ),
            nn.SiLU(),
            nn.Linear(
                hidden_size,
                output_size if output_size is not None else hidden_size,
                bias=True,
                device=device,
                dtype=dtype,
            ),
        )
        self.frequency_embedding_size = frequency_embedding_size
    
    @staticmethod
    def timestep_embedding(
        t: torch.Tensor,
        dim: int,
        max_period: int = 10000,
    ) -> torch.Tensor:
        """
        Create sinusoidal timestep embeddings.
        
        Note: Unlike some implementations, this does NOT multiply t by time_factor.
        The time scaling should be done by the caller (t * time_scale) before
        calling this function.
        
        Args:
            t: 1-D tensor of N timesteps, one per batch element
               (should already be scaled, e.g., in [0, 1000] range)
            dim: Embedding dimension
            max_period: Maximum period for sinusoidal encoding
            
        Returns:
            Tensor of shape (N, dim) with timestep embeddings
        """
        half = dim // 2
        freqs = torch.exp(
            -math.log(max_period)
            * torch.arange(start=0, end=half, dtype=torch.float32, device=t.device)
            / half
        )
        
        args = t[:, None].float() * freqs[None]
        embedding = torch.cat([torch.cos(args), torch.sin(args)], dim=-1)
        
        if dim % 2:
            embedding = torch.cat(
                [embedding, torch.zeros_like(embedding[:, :1])], dim=-1
            )
        
        return embedding
    
    def forward(self, t: torch.Tensor, dtype: torch.dtype = None) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            t: Timestep tensor of shape (N,)
            dtype: Output dtype
            
        Returns:
            Timestep embeddings of shape (N, hidden_size)
        """
        t_freq = self.timestep_embedding(t, self.frequency_embedding_size)
        if dtype is not None:
            t_freq = t_freq.to(dtype)
        t_emb = self.mlp(t_freq)
        return t_emb


class EmbedND(nn.Module):
    """
    N-dimensional rotary positional embedding (RoPE).
    
    This provides 3D positional encoding for image patches:
    - Dimension 0: Token position (text vs image)
    - Dimension 1: Height position
    - Dimension 2: Width position
    
    Args:
        dim: Head dimension for RoPE
        theta: Base frequency
        axes_dim: Dimensions for each axis
    """
    
    def __init__(
        self,
        dim: int,
        theta: int = 10000,
        axes_dim: List[int] = None,
    ):
        super().__init__()
        self.dim = dim
        self.theta = theta
        self.axes_dim = axes_dim if axes_dim is not None else [16, 56, 56]
    
    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        """
        Compute RoPE embeddings for position IDs.
        
        Args:
            ids: Position IDs of shape (batch, seq_len, 3)
                 ids[..., 0]: token type
                 ids[..., 1]: height position  
                 ids[..., 2]: width position
        
        Returns:
            RoPE embeddings of shape (batch, 1, seq_len, dim, 2, 2)
            where dim = sum(axes_dim)
        """
        n_axes = ids.shape[-1]
        emb = torch.cat(
            [
                rope_impl(ids[..., i], self.axes_dim[i], self.theta)
                for i in range(n_axes)
            ],
            dim=-3,  # Concatenate along the dim axis
        )
        # emb shape: (batch, seq_len, dim, 2, 2)
        # Add dimension for heads broadcast: (batch, 1, seq_len, dim, 2, 2)
        return emb.unsqueeze(1)


def rope_impl(
    pos: torch.Tensor,
    dim: int,
    theta: int,
) -> torch.Tensor:
    """
    Compute rotary positional embeddings.
    
    Args:
        pos: Position tensor of shape (batch, seq_len)
        dim: Embedding dimension (must be even)
        theta: Base frequency
        
    Returns:
        Complex exponential embeddings of shape (batch, seq_len, dim/2)
    """
    assert dim % 2 == 0, "Dimension must be divisible by 2"
    
    scale = torch.arange(0, dim, 2, dtype=torch.float64, device=pos.device) / dim
    omega = 1.0 / (theta**scale)
    
    out = torch.einsum("...n,d->...nd", pos.to(torch.float64), omega)
    out = torch.stack(
        [torch.cos(out), -torch.sin(out), torch.sin(out), torch.cos(out)], dim=-1
    )
    out = out.view(*out.shape[:-1], 2, 2)
    
    return out.to(torch.float32)


def apply_rope(
    xq: torch.Tensor,
    xk: torch.Tensor,
    freqs_cis: torch.Tensor,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Apply rotary positional embeddings to query and key tensors.
    
    Args:
        xq: Query tensor of shape (batch, seq_len, heads, head_dim)
        xk: Key tensor of shape (batch, seq_len, heads, head_dim)
        freqs_cis: RoPE frequencies of shape (batch, seq_len, 1, head_dim, 2, 2)
        
    Returns:
        Tuple of (rotated_query, rotated_key) with same shapes as inputs
    """
    return _apply_rope_single(xq, freqs_cis), _apply_rope_single(xk, freqs_cis)


def _apply_rope_single(x: torch.Tensor, freqs_cis: torch.Tensor) -> torch.Tensor:
    """
    Apply RoPE to a single tensor.
    
    Args:
        x: Input tensor of shape (batch, seq_len, heads, head_dim)
        freqs_cis: RoPE frequencies of shape (batch, seq_len, 1, head_dim//2, 2, 2)
        
    Returns:
        Rotated tensor with same shape as input
    """
    original_shape = x.shape
    
    # Reshape x to match freqs_cis structure
    # x: (batch, seq_len, heads, head_dim) -> (batch, seq_len, heads, head_dim//2, 1, 2)
    x_ = x.to(dtype=freqs_cis.dtype).reshape(*x.shape[:-1], -1, 1, 2)
    
    # Debug: check shapes
    # print(f"DEBUG apply_rope: x.shape={original_shape}, x_.shape={x_.shape}, freqs_cis.shape={freqs_cis.shape}")
    
    # Apply rotation matrix
    # freqs_cis[..., 0] is the first row of 2x2 rotation matrix: (batch, seq, 1, dim//2, 2)
    # x_[..., 0] is the first element of pair: (batch, seq, heads, dim//2, 1)
    x_out = freqs_cis[..., 0] * x_[..., 0]
    x_out = x_out + freqs_cis[..., 1] * x_[..., 1]
    
    # x_out shape: (batch, seq, heads, dim//2, 2)
    # Reshape back to original shape: (batch, seq, heads, head_dim)
    result = x_out.reshape(*original_shape).type_as(x)
    
    # Verify shape preservation
    assert result.shape == original_shape, f"Shape mismatch: {result.shape} vs {original_shape}"
    
    return result


class Timestep(nn.Module):
    """
    Simple timestep embedding for conditioning.
    
    Used for auxiliary conditioning like FPS, motion bucket, etc.
    
    Args:
        dim: Embedding dimension
    """
    
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim
    
    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """
        Create timestep embedding.
        
        Args:
            t: Input tensor
            
        Returns:
            Sinusoidal embedding
        """
        return TimestepEmbedder.timestep_embedding(
            t.flatten(), self.dim
        )
