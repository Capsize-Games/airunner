"""
NextDiT Transformer Model for Z-Image.

This module provides the complete NextDiT transformer architecture
used in Z-Image/Lumina2 for image generation.

Based on ComfyUI's comfy/ldm/lumina/model.py implementation.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Union

import torch
import torch.nn as nn

from airunner.components.art.managers.zimage.native.attention import RMSNorm
from airunner.components.art.managers.zimage.native.embedders import (
    EmbedND,
    TimestepEmbedder,
)
from airunner.components.art.managers.zimage.native.transformer_block import (
    FinalLayer,
    JointTransformerBlock,
)

logger = logging.getLogger(__name__)


def pad_to_patch_size(
    x: torch.Tensor,
    patch_size: Tuple[int, int],
) -> torch.Tensor:
    """
    Pad input to be divisible by patch size.
    
    Args:
        x: Input tensor of shape (B, C, H, W)
        patch_size: (patch_height, patch_width)
        
    Returns:
        Padded tensor
    """
    _, _, h, w = x.shape
    ph, pw = patch_size
    
    pad_h = (ph - h % ph) % ph
    pad_w = (pw - w % pw) % pw
    
    if pad_h > 0 or pad_w > 0:
        x = nn.functional.pad(x, (0, pad_w, 0, pad_h), mode='constant', value=0)
    
    return x


class NextDiT(nn.Module):
    """
    NextDiT: Diffusion Transformer for Z-Image/Lumina2.
    
    This is the main transformer architecture that processes:
    1. Noisy latent patches (image embeddings)
    2. Text conditioning (caption features)
    3. Timestep information
    
    And outputs predicted velocity/noise for denoising.
    
    Args:
        patch_size: Patch size for latent patchification
        in_channels: Input latent channels (16 for SD3 VAE)
        dim: Model dimension (3840 for Z-Image)
        n_layers: Number of main transformer layers
        n_refiner_layers: Number of noise/context refiner layers
        n_heads: Number of attention heads
        n_kv_heads: Number of key/value heads (for GQA)
        multiple_of: FFN hidden dim multiple
        ffn_dim_multiplier: FFN dimension multiplier
        norm_eps: Epsilon for normalization
        qk_norm: Whether to normalize Q/K in attention
        cap_feat_dim: Caption feature dimension
        axes_dims: RoPE dimensions for each axis
        axes_lens: Maximum sequence lengths for each axis
        rope_theta: RoPE base frequency
        z_image_modulation: Use Z-Image specific modulation
        time_scale: Timestep scaling factor
        pad_tokens_multiple: Pad tokens to this multiple
        image_model: Model type identifier
        device: Target device
        dtype: Data type
    """
    
    def __init__(
        self,
        patch_size: int = 2,
        in_channels: int = 16,
        dim: int = 3840,
        n_layers: int = 32,
        n_refiner_layers: int = 2,
        n_heads: int = 30,
        n_kv_heads: Optional[int] = None,
        multiple_of: int = 256,
        ffn_dim_multiplier: float = 4.0,
        norm_eps: float = 1e-5,
        qk_norm: bool = False,
        cap_feat_dim: int = 2560,  # Qwen hidden size
        axes_dims: List[int] = None,
        axes_lens: List[int] = None,
        rope_theta: int = 10000,
        z_image_modulation: bool = True,
        time_scale: float = 1.0,
        pad_tokens_multiple: Optional[int] = None,
        image_model: Optional[str] = None,
        device=None,
        dtype=None,
    ):
        super().__init__()
        
        # Default axes dimensions for Z-Image
        if axes_dims is None:
            axes_dims = [16, 56, 56]  # Total = 128 = dim // n_heads
        if axes_lens is None:
            axes_lens = [1, 512, 512]
        
        self.dtype = dtype
        self.in_channels = in_channels
        self.out_channels = in_channels
        self.patch_size = patch_size
        self.time_scale = time_scale
        self.pad_tokens_multiple = pad_tokens_multiple
        self.dim = dim
        self.n_heads = n_heads
        
        # Patch embedding
        self.x_embedder = nn.Linear(
            patch_size * patch_size * in_channels,
            dim,
            bias=True,
            device=device,
            dtype=dtype,
        )
        
        # Noise refiner (processes noisy latents)
        self.noise_refiner = nn.ModuleList([
            JointTransformerBlock(
                layer_id=i,
                dim=dim,
                n_heads=n_heads,
                n_kv_heads=n_kv_heads,
                multiple_of=multiple_of,
                ffn_dim_multiplier=ffn_dim_multiplier,
                norm_eps=norm_eps,
                qk_norm=qk_norm,
                modulation=True,
                z_image_modulation=z_image_modulation,
                device=device,
                dtype=dtype,
            )
            for i in range(n_refiner_layers)
        ])
        
        # Context refiner (processes text embeddings)
        self.context_refiner = nn.ModuleList([
            JointTransformerBlock(
                layer_id=i,
                dim=dim,
                n_heads=n_heads,
                n_kv_heads=n_kv_heads,
                multiple_of=multiple_of,
                ffn_dim_multiplier=ffn_dim_multiplier,
                norm_eps=norm_eps,
                qk_norm=qk_norm,
                modulation=False,  # No timestep modulation for context
                device=device,
                dtype=dtype,
            )
            for i in range(n_refiner_layers)
        ])
        
        # Timestep embedder
        self.t_embedder = TimestepEmbedder(
            min(dim, 1024),
            output_size=256 if z_image_modulation else None,
            device=device,
            dtype=dtype,
        )
        
        # Caption embedder
        self.cap_embedder = nn.Sequential(
            RMSNorm(cap_feat_dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype),
            nn.Linear(cap_feat_dim, dim, bias=True, device=device, dtype=dtype),
        )
        
        # Main transformer layers
        self.layers = nn.ModuleList([
            JointTransformerBlock(
                layer_id=i,
                dim=dim,
                n_heads=n_heads,
                n_kv_heads=n_kv_heads,
                multiple_of=multiple_of,
                ffn_dim_multiplier=ffn_dim_multiplier,
                norm_eps=norm_eps,
                qk_norm=qk_norm,
                modulation=True,
                z_image_modulation=z_image_modulation,
                attn_out_bias=False,
                device=device,
                dtype=dtype,
            )
            for i in range(n_layers)
        ])
        
        # Final norm and projection
        self.norm_final = RMSNorm(
            dim, eps=norm_eps, elementwise_affine=True, device=device, dtype=dtype
        )
        self.final_layer = FinalLayer(
            dim, patch_size, self.out_channels,
            z_image_modulation=z_image_modulation,
            device=device,
            dtype=dtype,
        )
        
        # Padding tokens (optional)
        if self.pad_tokens_multiple is not None:
            self.x_pad_token = nn.Parameter(
                torch.empty((1, dim), device=device, dtype=dtype)
            )
            self.cap_pad_token = nn.Parameter(
                torch.empty((1, dim), device=device, dtype=dtype)
            )
        
        # RoPE embedder
        assert (dim // n_heads) == sum(axes_dims), f"head_dim {dim//n_heads} != sum(axes_dims) {sum(axes_dims)}"
        self.axes_dims = axes_dims
        self.axes_lens = axes_lens
        self.rope_embedder = EmbedND(dim=dim // n_heads, theta=rope_theta, axes_dim=axes_dims)
    
    def unpatchify(
        self,
        x: torch.Tensor,
        img_size: List[Tuple[int, int]],
        cap_size: List[int],
        return_tensor: bool = False,
    ) -> Union[List[torch.Tensor], torch.Tensor]:
        """
        Convert patches back to image tensor.
        
        Args:
            x: Patch tensor of shape (B, S, patch_size^2 * C)
            img_size: List of (H, W) for each batch element
            cap_size: List of caption lengths for each batch element
            return_tensor: Whether to stack results
            
        Returns:
            List of image tensors or stacked tensor
        """
        pH = pW = self.patch_size
        imgs = []
        
        for i in range(x.size(0)):
            H, W = img_size[i]
            begin = cap_size[i]
            end = begin + (H // pH) * (W // pW)
            
            img = (
                x[i][begin:end]
                .view(H // pH, W // pW, pH, pW, self.out_channels)
                .permute(4, 0, 2, 1, 3)
                .flatten(3, 4)
                .flatten(1, 2)
            )
            imgs.append(img)
        
        if return_tensor:
            imgs = torch.stack(imgs, dim=0)
        return imgs
    
    def patchify_and_embed(
        self,
        x: torch.Tensor,
        cap_feats: torch.Tensor,
        cap_mask: Optional[torch.Tensor],
        t: torch.Tensor,
        num_tokens: int,
        transformer_options: dict = None,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], List[Tuple[int, int]], List[int], torch.Tensor]:
        """
        Patchify image and embed with positional encoding.
        
        Args:
            x: Image latent of shape (B, C, H, W)
            cap_feats: Caption features of shape (B, L, D_cap)
            cap_mask: Caption attention mask
            t: Timestep embedding
            num_tokens: Number of text tokens
            transformer_options: Additional options
            
        Returns:
            Tuple of:
            - padded_full_embed: Combined caption + image embeddings
            - mask: Attention mask (or None)
            - img_sizes: List of (H, W) for each batch element
            - l_effective_cap_len: List of caption lengths
            - freqs_cis: RoPE frequencies
        """
        if transformer_options is None:
            transformer_options = {}
        
        bsz = x.shape[0]
        pH = pW = self.patch_size
        device = x.device
        
        # Pad caption features if needed
        if self.pad_tokens_multiple is not None:
            pad_extra = (-cap_feats.shape[1]) % self.pad_tokens_multiple
            if pad_extra > 0:
                cap_feats = torch.cat((
                    cap_feats,
                    self.cap_pad_token.to(device=cap_feats.device, dtype=cap_feats.dtype).unsqueeze(0).repeat(
                        cap_feats.shape[0], pad_extra, 1
                    )
                ), dim=1)
                # Also pad the attention mask if provided
                if cap_mask is not None:
                    # Pad mask with False (don't attend to padding tokens)
                    if cap_mask.dtype == torch.bool:
                        cap_mask = torch.nn.functional.pad(cap_mask, (0, pad_extra), value=False)
                    else:
                        cap_mask = torch.nn.functional.pad(cap_mask, (0, pad_extra), value=0)
        
        # Caption position IDs
        cap_pos_ids = torch.zeros(bsz, cap_feats.shape[1], 3, dtype=torch.float32, device=device)
        cap_pos_ids[:, :, 0] = torch.arange(cap_feats.shape[1], dtype=torch.float32, device=device) + 1.0
        
        # Patchify and embed image
        B, C, H, W = x.shape
        x = self.x_embedder(
            x.view(B, C, H // pH, pH, W // pW, pW)
            .permute(0, 2, 4, 3, 5, 1)
            .flatten(3)
            .flatten(1, 2)
        )
        
        # Get RoPE scaling from transformer_options
        rope_options = transformer_options.get("rope_options", None)
        h_scale = 1.0
        w_scale = 1.0
        h_start = 0
        w_start = 0
        
        if rope_options is not None:
            h_scale = rope_options.get("scale_y", 1.0)
            w_scale = rope_options.get("scale_x", 1.0)
            h_start = rope_options.get("shift_y", 0.0)
            w_start = rope_options.get("shift_x", 0.0)
        
        # Image position IDs
        H_tokens, W_tokens = H // pH, W // pW
        x_pos_ids = torch.zeros((bsz, x.shape[1], 3), dtype=torch.float32, device=device)
        x_pos_ids[:, :, 0] = cap_feats.shape[1] + 1
        x_pos_ids[:, :, 1] = (
            torch.arange(H_tokens, dtype=torch.float32, device=device) * h_scale + h_start
        ).view(-1, 1).repeat(1, W_tokens).flatten()
        x_pos_ids[:, :, 2] = (
            torch.arange(W_tokens, dtype=torch.float32, device=device) * w_scale + w_start
        ).view(1, -1).repeat(H_tokens, 1).flatten()
        
        # Pad image embeddings if needed
        if self.pad_tokens_multiple is not None:
            pad_extra = (-x.shape[1]) % self.pad_tokens_multiple
            x = torch.cat((
                x,
                self.x_pad_token.to(device=x.device, dtype=x.dtype).unsqueeze(0).repeat(
                    x.shape[0], pad_extra, 1
                )
            ), dim=1)
            x_pos_ids = nn.functional.pad(x_pos_ids, (0, 0, 0, pad_extra))
        
        # Compute RoPE frequencies
        freqs_cis = self.rope_embedder(torch.cat((cap_pos_ids, x_pos_ids), dim=1)).movedim(1, 2)
        
        # Refine context (text embeddings)
        for layer in self.context_refiner:
            cap_feats = layer(
                cap_feats,
                cap_mask,
                freqs_cis[:, :cap_pos_ids.shape[1]],
                transformer_options=transformer_options,
            )
        
        # Refine noise (image embeddings)
        padded_img_mask = None
        for layer in self.noise_refiner:
            x = layer(
                x,
                padded_img_mask,
                freqs_cis[:, cap_pos_ids.shape[1]:],
                t,
                transformer_options=transformer_options,
            )
        
        # Combine caption and image embeddings
        padded_full_embed = torch.cat((cap_feats, x), dim=1)
        mask = None
        img_sizes = [(H, W)] * bsz
        l_effective_cap_len = [cap_feats.shape[1]] * bsz
        
        return padded_full_embed, mask, img_sizes, l_effective_cap_len, freqs_cis
    
    def forward(
        self,
        x: torch.Tensor,
        timesteps: torch.Tensor,
        context: torch.Tensor,
        num_tokens: int = 0,
        attention_mask: Optional[torch.Tensor] = None,
        transformer_options: dict = None,
        **kwargs,
    ) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Noisy latent of shape (B, C, H, W)
            timesteps: Diffusion timesteps of shape (B,)
            context: Text embeddings of shape (B, L, D_cap)
            num_tokens: Number of text tokens
            attention_mask: Optional attention mask for text
            transformer_options: Additional options
            
        Returns:
            Predicted velocity/noise of shape (B, C, H, W)
        """
        if transformer_options is None:
            transformer_options = {}
        
        # Official Z-Image timestep handling:
        # Pipeline passes: t_normalized = (1000 - t_scheduler) / 1000
        # Transformer does: t_scaled = t_normalized * t_scale (1000.0)
        # So effective input to embedder is: 1000 - t_scheduler
        #
        # If timesteps come from scheduler in [1, 1000] range:
        # t_normalized = (1000 - timesteps) / 1000
        # Then multiply by time_scale (1000) to get: 1000 - timesteps
        if timesteps.max() > 1.0:
            # Timesteps are in [1, 1000] range from scheduler
            # Apply official transformation: (1000 - t) / 1000
            t = (1000.0 - timesteps) / 1000.0
        else:
            # Already normalized to [0, 1] range
            t = timesteps
        
        cap_feats = context
        cap_mask = attention_mask
        bs, c, h, w = x.shape
        
        # Pad to patch size
        x = pad_to_patch_size(x, (self.patch_size, self.patch_size))
        
        # Embed timestep - multiply by time_scale as official implementation does
        t = self.t_embedder(t * self.time_scale, dtype=x.dtype)
        adaln_input = t
        
        # Embed caption
        cap_feats = self.cap_embedder(cap_feats)
        
        # Patchify and embed everything
        patches = transformer_options.get("patches", {})
        img, mask, img_size, cap_size, freqs_cis = self.patchify_and_embed(
            x, cap_feats, cap_mask, t, num_tokens, transformer_options=transformer_options
        )
        freqs_cis = freqs_cis.to(img.device)
        
        # Main transformer layers
        for i, layer in enumerate(self.layers):
            img = layer(
                img, mask, freqs_cis, adaln_input,
                transformer_options=transformer_options,
            )
            
            # Handle patches (for ControlNet, etc.)
            if "double_block" in patches:
                for p in patches["double_block"]:
                    out = p({
                        "img": img[:, cap_size[0]:],
                        "txt": img[:, :cap_size[0]],
                        "pe": freqs_cis[:, cap_size[0]:],
                        "vec": adaln_input,
                        "x": x,
                        "block_index": i,
                        "transformer_options": transformer_options,
                    })
                    if "img" in out:
                        img[:, cap_size[0]:] = out["img"]
                    if "txt" in out:
                        img[:, :cap_size[0]] = out["txt"]
        
        # Final layer
        img = self.final_layer(img, adaln_input)
        
        # Unpatchify
        img = self.unpatchify(img, img_size, cap_size, return_tensor=True)[:, :, :h, :w]
        
        # Return model output - negation is handled in the pipeline
        return img
    
    @property
    def device(self) -> torch.device:
        """Get model device."""
        return next(self.parameters()).device


# Z-Image specific configuration
# Based on ComfyUI's model_detection.py for dim=3840 Z-Image
ZIMAGE_CONFIG = {
    "patch_size": 2,
    "in_channels": 16,  # SD3 VAE
    "dim": 3840,
    "n_layers": 30,  # FP8 checkpoint has 30 layers (0-29)
    "n_refiner_layers": 2,
    "n_heads": 30,  # 3840 / 128 head_dim
    "n_kv_heads": 30,  # Z-Image uses same n_kv_heads as n_heads
    "multiple_of": 256,
    "ffn_dim_multiplier": 8.0 / 3.0,  # Z-Image specific: 2.666...
    "norm_eps": 1e-5,
    "qk_norm": True,  # FP8 checkpoints use QK normalization
    "cap_feat_dim": 2560,  # Qwen hidden size
    "axes_dims": [32, 48, 48],  # Z-Image specific, Total = 128 head_dim
    "axes_lens": [1536, 512, 512],  # Z-Image specific max positions
    "rope_theta": 256.0,  # Z-Image specific (NOT 10000)
    "z_image_modulation": True,
    "time_scale": 1000.0,  # Z-Image specific timestep scale
    "pad_tokens_multiple": 32,  # Z-Image uses pad_tokens_multiple=32
}


def create_zimage_transformer(
    device: Optional[torch.device] = None,
    dtype: Optional[torch.dtype] = None,
) -> NextDiT:
    """
    Create a Z-Image transformer with default configuration.
    
    Args:
        device: Target device
        dtype: Data type
        
    Returns:
        Configured NextDiT model
    """
    return NextDiT(
        **ZIMAGE_CONFIG,
        device=device,
        dtype=dtype,
    )
