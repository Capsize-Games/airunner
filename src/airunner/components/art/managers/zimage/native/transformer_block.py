"""
Transformer block for NextDiT.

This module provides the JointTransformerBlock used in Z-Image/Lumina2.
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn

from airunner.components.art.managers.zimage.native.attention import (
    JointAttention,
    RMSNorm,
)
from airunner.components.art.managers.zimage.native.feedforward import (
    FeedForward,
    clamp_fp16,
)


def modulate(x: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """
    Apply scale modulation.
    
    Args:
        x: Input tensor of shape (B, S, D)
        scale: Scale tensor of shape (B, D)
        
    Returns:
        Modulated tensor
    """
    return x * (1 + scale.unsqueeze(1))


class JointTransformerBlock(nn.Module):
    """
    Transformer block with AdaLN modulation.
    
    This is the main building block of Z-Image/Lumina2 with:
    - Pre-RMSNorm on attention and FFN
    - AdaLN modulation from timestep embedding
    - Tanh gating on residual connections
    
    Args:
        layer_id: Layer index (for logging)
        dim: Model dimension
        n_heads: Number of attention heads
        n_kv_heads: Number of key/value heads (for GQA)
        multiple_of: FFN hidden dimension multiple
        ffn_dim_multiplier: FFN dimension multiplier
        norm_eps: Epsilon for RMSNorm
        qk_norm: Whether to normalize Q/K in attention
        modulation: Whether to use AdaLN modulation
        z_image_modulation: Use Z-Image specific modulation (smaller dim)
        attn_out_bias: Whether attention output has bias
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        layer_id: int,
        dim: int,
        n_heads: int,
        n_kv_heads: int = None,
        multiple_of: int = 256,
        ffn_dim_multiplier: float = 4.0,
        norm_eps: float = 1e-5,
        qk_norm: bool = False,
        modulation: bool = True,
        z_image_modulation: bool = False,
        attn_out_bias: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()

        self.dim = dim
        self.head_dim = dim // n_heads
        self.layer_id = layer_id
        self.modulation = modulation

        self.attention = self._build_attention(
            dim,
            n_heads,
            n_kv_heads,
            qk_norm,
            attn_out_bias,
            device,
            dtype,
        )

        self.feed_forward = self._build_feedforward(
            dim,
            multiple_of,
            ffn_dim_multiplier,
            device,
            dtype,
        )

        (
            self.attention_norm1,
            self.ffn_norm1,
            self.attention_norm2,
            self.ffn_norm2,
        ) = self._build_norm_layers(dim, norm_eps, device, dtype)

        self.adaLN_modulation = (
            self._build_modulation_layer(dim, z_image_modulation, device, dtype)
            if modulation
            else None
        )

    @staticmethod
    def _build_attention(
        dim: int,
        n_heads: int,
        n_kv_heads: Optional[int],
        qk_norm: bool,
        attn_out_bias: bool,
        device,
        dtype,
    ) -> JointAttention:
        return JointAttention(
            dim,
            n_heads,
            n_kv_heads,
            qk_norm,
            out_bias=attn_out_bias,
            device=device,
            dtype=dtype,
        )

    @staticmethod
    def _build_feedforward(
        dim: int,
        multiple_of: int,
        ffn_dim_multiplier: float,
        device,
        dtype,
    ) -> FeedForward:
        return FeedForward(
            dim=dim,
            hidden_dim=dim,
            multiple_of=multiple_of,
            ffn_dim_multiplier=ffn_dim_multiplier,
            device=device,
            dtype=dtype,
        )

    @staticmethod
    def _build_norm_layers(dim: int, norm_eps: float, device, dtype):
        return (
            RMSNorm(dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype),
            RMSNorm(dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype),
            RMSNorm(dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype),
            RMSNorm(dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype),
        )

    @staticmethod
    def _build_modulation_layer(dim: int, z_image_modulation: bool, device, dtype):
        if z_image_modulation:
            return nn.Sequential(
                nn.Linear(
                    min(dim, 256),
                    4 * dim,
                    bias=True,
                    device=device,
                    dtype=dtype,
                ),
            )
        return nn.Sequential(
            nn.SiLU(),
            nn.Linear(
                min(dim, 1024),
                4 * dim,
                bias=True,
                device=device,
                dtype=dtype,
            ),
        )
    
    def forward(
        self,
        x: torch.Tensor,
        x_mask: Optional[torch.Tensor],
        freqs_cis: torch.Tensor,
        adaln_input: Optional[torch.Tensor] = None,
        transformer_options: dict = None,
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, S, D)
            x_mask: Optional attention mask
            freqs_cis: RoPE frequencies
            adaln_input: Timestep embedding for modulation
            transformer_options: Additional options
            
        Returns:
            Output tensor of shape (B, S, D)
        """
        if transformer_options is None:
            transformer_options = {}
        
        if self.modulation:
            assert adaln_input is not None, "adaln_input required when modulation=True"
            
            # Get modulation parameters
            scale_msa, gate_msa, scale_mlp, gate_mlp = self.adaLN_modulation(
                adaln_input
            ).chunk(4, dim=1)
            
            # Attention with modulation
            x = x + gate_msa.unsqueeze(1).tanh() * self.attention_norm2(
                clamp_fp16(
                    self.attention(
                        modulate(self.attention_norm1(x), scale_msa),
                        x_mask,
                        freqs_cis,
                        transformer_options=transformer_options,
                    )
                )
            )
            
            # FFN with modulation
            x = x + gate_mlp.unsqueeze(1).tanh() * self.ffn_norm2(
                clamp_fp16(
                    self.feed_forward(
                        modulate(self.ffn_norm1(x), scale_mlp),
                    )
                )
            )
        else:
            # Without modulation (used in context refiner)
            assert adaln_input is None, "adaln_input not used when modulation=False"
            
            x = x + self.attention_norm2(
                clamp_fp16(
                    self.attention(
                        self.attention_norm1(x),
                        x_mask,
                        freqs_cis,
                        transformer_options=transformer_options,
                    )
                )
            )
            
            x = x + self.ffn_norm2(
                self.feed_forward(
                    self.ffn_norm1(x),
                )
            )
        
        return x


class FinalLayer(nn.Module):
    """
    Final layer of NextDiT.
    
    Applies final normalization and projection to patch space.
    
    Args:
        hidden_size: Model dimension
        patch_size: Patch size
        out_channels: Output channels (latent channels)
        z_image_modulation: Use Z-Image specific modulation
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        hidden_size: int,
        patch_size: int,
        out_channels: int,
        z_image_modulation: bool = False,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        self.norm_final = nn.LayerNorm(
            hidden_size,
            elementwise_affine=False,
            eps=1e-6,
            device=device,
            dtype=dtype,
        )
        
        self.linear = nn.Linear(
            hidden_size,
            patch_size * patch_size * out_channels,
            bias=True,
            device=device,
            dtype=dtype,
        )
        
        # AdaLN modulation
        mod_dim = 256 if z_image_modulation else 1024
        self.adaLN_modulation = nn.Sequential(
            nn.SiLU(),
            nn.Linear(
                min(hidden_size, mod_dim),
                hidden_size,
                bias=True,
                device=device,
                dtype=dtype,
            ),
        )
    
    def forward(self, x: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (B, S, D)
            c: Conditioning tensor (timestep embedding)
            
        Returns:
            Output patches of shape (B, S, patch_size^2 * channels)
        """
        scale = self.adaLN_modulation(c)
        x = modulate(self.norm_final(x), scale)
        x = self.linear(x)
        return x
