"""
Attention modules for NextDiT transformer.

This module provides the JointAttention implementation used in the
Z-Image/Lumina2 architecture.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from airunner.components.art.managers.zimage.native.embedders import apply_rope


def optimized_attention(
    q: torch.Tensor,
    k: torch.Tensor,
    v: torch.Tensor,
    heads: int,
    mask: Optional[torch.Tensor] = None,
    skip_reshape: bool = False,
) -> torch.Tensor:
    """
    Optimized scaled dot-product attention.
    
    Uses PyTorch's native SDPA which automatically selects the best
    implementation (FlashAttention, Memory Efficient, or Math).
    
    Args:
        q: Query tensor
        k: Key tensor
        v: Value tensor
        heads: Number of attention heads
        mask: Optional attention mask
        skip_reshape: If True, assume q/k/v are already (B, H, S, D)
        
    Returns:
        Attention output
    """
    if not skip_reshape:
        # q, k, v shape: (B, S, H*D)
        b, seq_len, _ = q.shape
        head_dim = q.shape[-1] // heads
        
        q = q.view(b, seq_len, heads, head_dim).transpose(1, 2)
        k = k.view(b, seq_len, heads, head_dim).transpose(1, 2)
        v = v.view(b, seq_len, heads, head_dim).transpose(1, 2)
    
    # Use PyTorch's scaled_dot_product_attention
    out = F.scaled_dot_product_attention(
        q, k, v, attn_mask=mask, dropout_p=0.0, is_causal=False
    )
    
    if not skip_reshape:
        out = out.transpose(1, 2).reshape(b, seq_len, -1)
    
    return out


def optimized_attention_masked(
    q: torch.Tensor,
    k: torch.Tensor,
    v: torch.Tensor,
    heads: int,
    mask: Optional[torch.Tensor] = None,
    skip_reshape: bool = False,
    transformer_options: dict = None,
) -> torch.Tensor:
    """
    Optimized attention with optional mask support.
    
    Args:
        q: Query tensor (B, H, S, D) if skip_reshape else (B, S, H*D)
        k: Key tensor
        v: Value tensor
        heads: Number of heads
        mask: Optional boolean mask (True = attend, False = ignore)
        skip_reshape: Whether tensors are pre-reshaped
        transformer_options: Additional options (unused currently)
        
    Returns:
        Attention output
    """
    if skip_reshape:
        b, _, seq_len, head_dim = q.shape
    else:
        b, seq_len, _ = q.shape
        head_dim = q.shape[-1] // heads
        
        q = q.view(b, seq_len, heads, head_dim).transpose(1, 2)
        k = k.view(b, k.shape[1], heads, head_dim).transpose(1, 2)
        v = v.view(b, v.shape[1], heads, head_dim).transpose(1, 2)
    
    # Convert boolean mask to attention mask if provided
    attn_mask = None
    if mask is not None:
        # mask shape: (B, S) or (B, 1, S)
        # Convert to attention bias: 0 for attend, -inf for ignore
        if mask.dtype == torch.bool:
            attn_mask = mask.unsqueeze(1).unsqueeze(2)  # (B, 1, 1, S)
            attn_mask = attn_mask.expand(-1, heads, seq_len, -1)
            attn_mask = torch.where(
                attn_mask,
                torch.zeros_like(attn_mask, dtype=q.dtype),
                torch.full_like(attn_mask, float('-inf'), dtype=q.dtype)
            )
        elif mask.dtype in (torch.long, torch.int, torch.int32, torch.int64):
            # Convert long/int mask to bool first (nonzero = attend)
            bool_mask = mask.bool()
            attn_mask = bool_mask.unsqueeze(1).unsqueeze(2)  # (B, 1, 1, S)
            attn_mask = attn_mask.expand(-1, heads, seq_len, -1)
            attn_mask = torch.where(
                attn_mask,
                torch.zeros((), dtype=q.dtype, device=q.device),
                torch.tensor(float('-inf'), dtype=q.dtype, device=q.device)
            )
        else:
            # Float mask - use as-is but ensure it's the right dtype
            attn_mask = mask.to(q.dtype) if mask.dtype != q.dtype else mask
    
    out = F.scaled_dot_product_attention(
        q, k, v, attn_mask=attn_mask, dropout_p=0.0, is_causal=False
    )
    
    # Reshape back to (B, S, H*D)
    out = out.transpose(1, 2).reshape(b, seq_len, -1)
    
    return out


class RMSNorm(nn.Module):
    """
    Root Mean Square Layer Normalization.
    
    More efficient than LayerNorm as it doesn't compute mean.
    
    Args:
        dim: Input dimension
        eps: Epsilon for numerical stability
        elementwise_affine: Whether to learn scale parameter
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        dim: int,
        eps: float = 1e-6,
        elementwise_affine: bool = True,
        device=None,
        dtype=None,
    ):
        super().__init__()
        self.eps = eps
        self.dim = dim
        
        if elementwise_affine:
            self.weight = nn.Parameter(
                torch.ones(dim, device=device, dtype=dtype)
            )
        else:
            self.register_parameter('weight', None)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply RMS normalization.
        
        Args:
            x: Input tensor of shape (..., dim)
            
        Returns:
            Normalized tensor
        """
        norm = torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        x = x * norm
        
        if self.weight is not None:
            x = x * self.weight
        
        return x


class JointAttention(nn.Module):
    """
    Multi-head attention with grouped query attention support.
    
    This is the attention mechanism used in Z-Image/Lumina2 with:
    - QKV projection in a single linear layer
    - RoPE positional encoding
    - Optional RMSNorm on Q and K
    - Grouped Query Attention (GQA) support
    
    Args:
        dim: Model dimension
        n_heads: Number of query heads
        n_kv_heads: Number of key/value heads (for GQA)
        qk_norm: Whether to apply RMSNorm to Q and K
        out_bias: Whether output projection has bias
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        n_kv_heads: Optional[int] = None,
        qk_norm: bool = False,
        out_bias: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        self.n_kv_heads = n_heads if n_kv_heads is None else n_kv_heads
        self.n_local_heads = n_heads
        self.n_local_kv_heads = self.n_kv_heads
        self.n_rep = self.n_local_heads // self.n_local_kv_heads
        self.head_dim = dim // n_heads
        
        # QKV projection
        self.qkv = nn.Linear(
            dim,
            (n_heads + self.n_kv_heads + self.n_kv_heads) * self.head_dim,
            bias=False,
            device=device,
            dtype=dtype,
        )
        
        # Output projection
        self.out = nn.Linear(
            n_heads * self.head_dim,
            dim,
            bias=out_bias,
            device=device,
            dtype=dtype,
        )
        
        # QK normalization
        if qk_norm:
            self.q_norm = RMSNorm(
                self.head_dim,
                elementwise_affine=True,
                device=device,
                dtype=dtype,
            )
            self.k_norm = RMSNorm(
                self.head_dim,
                elementwise_affine=True,
                device=device,
                dtype=dtype,
            )
        else:
            self.q_norm = nn.Identity()
            self.k_norm = nn.Identity()
    
    def forward(
        self,
        x: torch.Tensor,
        x_mask: Optional[torch.Tensor],
        freqs_cis: torch.Tensor,
        transformer_options: dict = None,
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, S, D)
            x_mask: Optional attention mask
            freqs_cis: RoPE frequencies
            transformer_options: Additional options
            
        Returns:
            Attention output of shape (B, S, D)
        """
        if transformer_options is None:
            transformer_options = {}
        
        bsz, seqlen, _ = x.shape
        
        # QKV projection
        qkv = self.qkv(x)
        xq, xk, xv = torch.split(
            qkv,
            [
                self.n_local_heads * self.head_dim,
                self.n_local_kv_heads * self.head_dim,
                self.n_local_kv_heads * self.head_dim,
            ],
            dim=-1,
        )
        
        # Reshape for attention
        xq = xq.view(bsz, seqlen, self.n_local_heads, self.head_dim)
        xk = xk.view(bsz, seqlen, self.n_local_kv_heads, self.head_dim)
        xv = xv.view(bsz, seqlen, self.n_local_kv_heads, self.head_dim)
        
        # QK normalization
        xq = self.q_norm(xq)
        xk = self.k_norm(xk)
        
        # Apply RoPE
        xq, xk = apply_rope(xq, xk, freqs_cis)
        
        # Repeat K/V for GQA
        n_rep = self.n_local_heads // self.n_local_kv_heads
        if n_rep > 1:
            xk = xk.unsqueeze(3).repeat(1, 1, 1, n_rep, 1).flatten(2, 3)
            xv = xv.unsqueeze(3).repeat(1, 1, 1, n_rep, 1).flatten(2, 3)
        
        # Attention
        output = optimized_attention_masked(
            xq.movedim(1, 2),
            xk.movedim(1, 2),
            xv.movedim(1, 2),
            self.n_local_heads,
            x_mask,
            skip_reshape=True,
            transformer_options=transformer_options,
        )
        
        return self.out(output)


class SelfAttention(nn.Module):
    """
    Standard self-attention without RoPE.
    
    Simpler attention for cases where positional encoding
    is not needed.
    
    Args:
        dim: Model dimension
        n_heads: Number of attention heads
        bias: Whether to use bias in projections
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        dim: int,
        n_heads: int,
        bias: bool = True,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        
        self.q_proj = nn.Linear(dim, dim, bias=bias, device=device, dtype=dtype)
        self.k_proj = nn.Linear(dim, dim, bias=bias, device=device, dtype=dtype)
        self.v_proj = nn.Linear(dim, dim, bias=bias, device=device, dtype=dtype)
        self.out_proj = nn.Linear(dim, dim, bias=bias, device=device, dtype=dtype)
    
    def forward(
        self,
        x: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, S, D)
            mask: Optional attention mask
            
        Returns:
            Attention output
        """
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)
        
        out = optimized_attention(q, k, v, self.n_heads, mask)
        return self.out_proj(out)
