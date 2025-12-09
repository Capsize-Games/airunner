"""
Native LoRA implementation for FP8 Z-Image models.

This module provides LoRA support for FP8Linear layers without PEFT dependency.
LoRA weights are stored separately and applied additively during forward pass,
allowing LoRAs to be enabled/disabled without reloading the base model.

Key features:
- Works with FP8Linear and UnscaledFP8Linear layers directly
- Non-destructive: LoRA weights stored separately, applied during forward
- Enable/disable LoRAs without model reload
- Adjust LoRA scale dynamically
- Low memory overhead (LoRA matrices are small)
"""

from __future__ import annotations

import gc
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from safetensors import safe_open
from safetensors.torch import load_file as load_safetensors
from airunner.components.art.managers.zimage.native.fp8_ops import (
    FP8Linear,
    QuantizedTensor,
    UnscaledFP8Linear,
)

logger = logging.getLogger(__name__)


def load_lora_state_dict(
    path: Union[str, Path, Dict[str, torch.Tensor]],
    device: Optional[torch.device] = None,
) -> Tuple[Dict[str, torch.Tensor], Optional[Dict[str, Any]]]:
    """
    Load LoRA state dict from file or dict.
    
    Args:
        path: Path to LoRA file or state dict
        device: Target device for tensors
        
    Returns:
        Tuple of (state_dict, metadata)
    """
    if isinstance(path, dict):
        return path, None
    
    path = Path(path)
    metadata = None
    
    if path.suffix == '.safetensors':
        state_dict = load_safetensors(str(path), device=str(device) if device else 'cpu')
        # Try to get metadata
        try:
            with safe_open(str(path), framework='pt') as f:
                metadata = dict(f.metadata()) if f.metadata() else None
        except Exception:
            pass
    elif path.suffix in ('.pt', '.pth', '.bin'):
        state_dict = torch.load(str(path), map_location=device or 'cpu', weights_only=True)
    else:
        raise ValueError(f"Unsupported LoRA file format: {path.suffix}")
    
    return state_dict, metadata


def parse_lora_key(key: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a LoRA state dict key into components.
    
    LoRA keys typically follow patterns like:
    - diffusion_model.layers.0.attention.to_q.lora_A.weight
    - transformer.layers.0.attn.to_q.lora_down.weight
    
    Args:
        key: State dict key
        
    Returns:
        Tuple of (base_module_path, lora_type, param_type) or None if not a LoRA key
    """
    # Common LoRA key patterns
    lora_indicators = ['lora_A', 'lora_B', 'lora_down', 'lora_up', 'lora.down', 'lora.up']
    
    for indicator in lora_indicators:
        if indicator in key:
            # Split at the indicator
            parts = key.split(indicator)
            if len(parts) >= 2:
                base_path = parts[0].rstrip('.')
                param_type = parts[1].lstrip('.').split('.')[0] if parts[1] else 'weight'
                
                # Normalize lora type
                if 'down' in indicator.lower() or indicator == 'lora_A':
                    lora_type = 'down'
                elif 'up' in indicator.lower() or indicator == 'lora_B':
                    lora_type = 'up'
                else:
                    continue
                    
                return base_path, lora_type, param_type
    
    return None


def get_module_by_path(model: nn.Module, path: str) -> Optional[nn.Module]:
    """
    Get a module by dot-separated path.
    
    Args:
        model: Root model
        path: Dot-separated path (e.g., "layers.0.attention.to_q")
        
    Returns:
        Module at path or None if not found
    """
    parts = path.split('.')
    current = model
    
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            # Index into ModuleList/Sequential
            idx = int(part)
            if isinstance(current, (nn.ModuleList, nn.Sequential)):
                if idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    
    return current


# Mapping for fused QKV attention layers
# LoRA expects: attention.to_q, attention.to_k, attention.to_v, attention.to_out.0
# Model has: attention.qkv (fused), attention.out
FUSED_QKV_MAPPING = {
    'to_q': ('qkv', 0),   # Q is first 1/3 of QKV
    'to_k': ('qkv', 1),   # K is second 1/3 of QKV
    'to_v': ('qkv', 2),   # V is third 1/3 of QKV
    'to_out.0': ('out', None),  # out maps directly
}


def get_fused_attention_module(
    model: nn.Module,
    base_path: str,
) -> Optional[Tuple[nn.Module, str, Optional[int]]]:
    """
    Get the fused attention module for a LoRA path that expects separate Q/K/V.
    
    For models with fused QKV (like NextDiT), maps:
    - attention.to_q -> attention.qkv (slice 0)
    - attention.to_k -> attention.qkv (slice 1)  
    - attention.to_v -> attention.qkv (slice 2)
    - attention.to_out.0 -> attention.out
    
    Args:
        model: Root model
        base_path: LoRA module path (e.g., "layers.0.attention.to_q")
        
    Returns:
        Tuple of (module, component_name, slice_idx) or None if not found
        slice_idx is 0/1/2 for Q/K/V, None for out
    """
    # Check if this is an attention path with to_q/k/v/out
    for lora_name, (model_name, slice_idx) in FUSED_QKV_MAPPING.items():
        suffix = f'.attention.{lora_name}'
        if base_path.endswith(suffix):
            # Strip the lora_name suffix to get the attention base path
            attention_base = base_path[:-len(lora_name)-1]  # Remove ".to_q" or ".to_out.0" etc.
            fused_path = f"{attention_base}.{model_name}"
            
            module = get_module_by_path(model, fused_path)
            if module is not None:
                return module, lora_name, slice_idx
    
    return None


def compute_lora_weight(
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    alpha: Optional[float] = None,
    rank: Optional[int] = None,
    scale: float = 1.0,
) -> torch.Tensor:
    """
    Compute the merged LoRA weight delta.
    
    LoRA formula: W' = W + (scale * alpha/rank) * (B @ A)
    where A is down_weight and B is up_weight.
    
    Args:
        down_weight: LoRA down/A weight [rank, in_features]
        up_weight: LoRA up/B weight [out_features, rank]
        alpha: LoRA alpha (defaults to rank if not provided)
        rank: LoRA rank (inferred from down_weight if not provided)
        scale: Additional scaling factor
        
    Returns:
        Weight delta to add to base weights [out_features, in_features]
    """
    if rank is None:
        rank = down_weight.shape[0]
    if alpha is None:
        alpha = float(rank)
    
    # Compute scaling factor
    lora_scale = scale * (alpha / rank)
    
    # Compute weight delta: B @ A
    # down_weight: [rank, in_features]
    # up_weight: [out_features, rank]
    # result: [out_features, in_features]
    delta = up_weight @ down_weight
    
    return lora_scale * delta


def _pad_up_weight_for_slice(
    up_weight: torch.Tensor, slice_idx: int, slice_size: int, total_out: int
) -> torch.Tensor:
    """Pad LoRA up_weight so it only affects the selected Q/K/V slice."""
    rank = up_weight.shape[1]
    padded_up = torch.zeros(total_out, rank, device=up_weight.device, dtype=up_weight.dtype)
    start_idx = slice_idx * slice_size
    padded_up[start_idx:start_idx + slice_size] = up_weight
    return padded_up


def _extract_qkv_base_weight(qkv_module: nn.Module) -> Optional[torch.Tensor]:
    """Get the base weight tensor from fused QKV modules."""
    if isinstance(qkv_module, FP8Linear):
        weight_attr = getattr(qkv_module, 'weight', None)
        if weight_attr is None or not hasattr(weight_attr, 'dequantize'):
            logger.warning("FP8Linear has no valid weight")
            return None
        return weight_attr.dequantize()
    if isinstance(qkv_module, nn.Linear):
        return qkv_module.weight.data
    logger.warning(f"Unsupported layer type for fused QKV: {type(qkv_module)}")
    return None


def _merge_qkv_weights(qkv_module: nn.Module, base_weight: torch.Tensor) -> None:
    """Store merged weights back on the fused QKV module."""
    if isinstance(qkv_module, FP8Linear):
        if not hasattr(qkv_module, '_merged_weight'):
            qkv_module._merged_weight = None
        qkv_module._merged_weight = base_weight
    else:
        qkv_module.weight.data = base_weight


def _apply_unscaled_fp8_qkv(
    qkv_module: UnscaledFP8Linear,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    slice_idx: int,
    alpha: Optional[float],
    scale: float,
    adapter_name: str,
) -> bool:
    total_out = qkv_module.out_features
    slice_size = total_out // 3
    padded_up = _pad_up_weight_for_slice(up_weight, slice_idx, slice_size, total_out)
    slice_name = ["q", "k", "v"][slice_idx]
    full_adapter_name = f"{adapter_name}_{slice_name}"
    qkv_module.add_lora(
        adapter_name=full_adapter_name,
        down_weight=down_weight,
        up_weight=padded_up,
        alpha=alpha,
        scale=scale,
    )
    return True


def apply_lora_to_fused_qkv(
    qkv_module: nn.Module,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    slice_idx: int,
    alpha: Optional[float] = None,
    scale: float = 1.0,
    adapter_name: str = "default",
) -> bool:
    """
    Apply LoRA weights to a slice of a fused QKV layer.
    
    For models with fused QKV (shape [3*hidden, hidden]), LoRA targets
    Q, K, or V individually. We handle this by:
    - For UnscaledFP8Linear: Store padded LoRA that only affects the target slice
    - For other types: Merge directly into the weight slice
    
    Args:
        qkv_module: The fused QKV linear layer
        down_weight: LoRA down/A weight
        up_weight: LoRA up/B weight  
        slice_idx: Which slice (0=Q, 1=K, 2=V)
        alpha: LoRA alpha
        scale: LoRA scale factor
        adapter_name: Name for the LoRA adapter
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if isinstance(qkv_module, UnscaledFP8Linear):
            return _apply_unscaled_fp8_qkv(
                qkv_module,
                down_weight,
                up_weight,
                slice_idx,
                alpha,
                scale,
                adapter_name,
            )

        base_weight = _extract_qkv_base_weight(qkv_module)
        if base_weight is None:
            return False

        total_out = base_weight.shape[0]
        hidden_dim = base_weight.shape[1]
        slice_size = total_out // 3

        down_weight = down_weight.to(device=base_weight.device, dtype=base_weight.dtype)
        up_weight = up_weight.to(device=base_weight.device, dtype=base_weight.dtype)
        delta = compute_lora_weight(down_weight, up_weight, alpha=alpha, scale=scale)

        expected_shape = (slice_size, hidden_dim)
        if delta.shape != expected_shape:
            logger.warning(
                f"Shape mismatch for QKV slice: expected {expected_shape}, got {delta.shape}"
            )
            return False

        start_idx = slice_idx * slice_size
        end_idx = start_idx + slice_size
        base_weight[start_idx:end_idx] += delta
        _merge_qkv_weights(qkv_module, base_weight)
        return True
    except Exception as e:
        logger.warning(f"Failed to apply LoRA to fused QKV: {e}")
        return False


def extract_lora_pairs(
    state_dict: Dict[str, torch.Tensor],
    prefix: Optional[str] = None,
) -> Dict[str, Dict[str, torch.Tensor]]:
    """
    Extract paired LoRA weights from state dict.
    
    Args:
        state_dict: LoRA state dict
        prefix: Optional prefix to strip from keys (e.g., "diffusion_model")
        
    Returns:
        Dict mapping base_path -> {"down": tensor, "up": tensor, "alpha": float}
    """
    pairs: Dict[str, Dict[str, Any]] = {}
    
    for key, tensor in state_dict.items():
        # Skip network alpha maps and metadata entries
        if key == "network_alphas" or key.startswith("network_alphas."):
            continue
        # Skip non-LoRA keys
        if 'lora' not in key.lower():
            continue
        
        # Handle alpha values
        if 'alpha' in key.lower():
            # Extract base path for alpha
            base_path = key.rsplit('.', 1)[0]
            if prefix and base_path.startswith(prefix):
                base_path = base_path[len(prefix):].lstrip('.')
            
            # Try to find matching pair
            for pair_path in list(pairs.keys()):
                if pair_path in base_path or base_path in pair_path:
                    pairs[pair_path]['alpha'] = tensor.item() if tensor.numel() == 1 else tensor
                    break
            continue
        
        parsed = parse_lora_key(key)
        if parsed is None:
            continue
        
        base_path, lora_type, _ = parsed
        
        # Strip prefix if provided
        if prefix and base_path.startswith(prefix):
            base_path = base_path[len(prefix):].lstrip('.')
        
        if base_path not in pairs:
            pairs[base_path] = {'down': None, 'up': None, 'alpha': None}
        
        pairs[base_path][lora_type] = tensor
    
    # Filter out incomplete pairs
    complete_pairs = {
        k: v for k, v in pairs.items()
        if v['down'] is not None and v['up'] is not None
    }
    
    logger.debug(f"Found {len(complete_pairs)} complete LoRA pairs from {len(state_dict)} keys")
    
    return complete_pairs


def apply_lora_to_linear(
    linear: nn.Module,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    alpha: Optional[float] = None,
    scale: float = 1.0,
    adapter_name: str = "default",
) -> bool:
    """
    Apply LoRA weights to a Linear, FP8Linear, or UnscaledFP8Linear layer.
    
    For UnscaledFP8Linear, uses additive LoRA (non-destructive).
    For other types, falls back to weight merging.
    
    Args:
        linear: Target linear layer
        down_weight: LoRA down/A weight
        up_weight: LoRA up/B weight
        alpha: LoRA alpha
        scale: LoRA scale factor
        adapter_name: Name for the LoRA adapter
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if isinstance(linear, UnscaledFP8Linear):
            return _apply_unscaled_fp8_linear(
                linear,
                down_weight,
                up_weight,
                alpha,
                scale,
                adapter_name,
            )
        if isinstance(linear, FP8Linear):
            return _merge_fp8_linear_weights(
                linear,
                down_weight,
                up_weight,
                alpha,
                scale,
            )
        if isinstance(linear, nn.Linear):
            return _merge_standard_linear_weights(
                linear,
                down_weight,
                up_weight,
                alpha,
                scale,
            )
        logger.warning(f"Unsupported layer type: {type(linear)}")
        return False
    except Exception as e:
        logger.warning(f"Failed to apply LoRA: {e}")
        return False


def _apply_unscaled_fp8_linear(
    linear: UnscaledFP8Linear,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    alpha: Optional[float],
    scale: float,
    adapter_name: str,
) -> bool:
    linear.add_lora(
        adapter_name=adapter_name,
        down_weight=down_weight,
        up_weight=up_weight,
        alpha=alpha,
        scale=scale,
    )
    return True


def _merge_fp8_linear_weights(
    linear: FP8Linear,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    alpha: Optional[float],
    scale: float,
) -> bool:
    weight_attr = getattr(linear, 'weight', None)
    if weight_attr is None or not hasattr(weight_attr, 'dequantize'):
        logger.warning("FP8Linear has no weight set (weight is None)")
        return False

    base_weight = weight_attr.dequantize()
    down_weight = down_weight.to(device=base_weight.device, dtype=base_weight.dtype)
    up_weight = up_weight.to(device=base_weight.device, dtype=base_weight.dtype)
    delta = compute_lora_weight(down_weight, up_weight, alpha=alpha, scale=scale)

    if delta.shape != base_weight.shape:
        logger.warning(f"Shape mismatch: base={base_weight.shape}, delta={delta.shape}")
        return False

    if not hasattr(linear, '_merged_weight'):
        linear._merged_weight = None
    linear._merged_weight = base_weight + delta
    return True


def _merge_standard_linear_weights(
    linear: nn.Linear,
    down_weight: torch.Tensor,
    up_weight: torch.Tensor,
    alpha: Optional[float],
    scale: float,
) -> bool:
    base_weight = linear.weight.data
    down_weight = down_weight.to(device=base_weight.device, dtype=base_weight.dtype)
    up_weight = up_weight.to(device=base_weight.device, dtype=base_weight.dtype)
    delta = compute_lora_weight(down_weight, up_weight, alpha=alpha, scale=scale)

    if delta.shape != base_weight.shape:
        logger.warning(f"Shape mismatch: base={base_weight.shape}, delta={delta.shape}")
        return False

    linear.weight.data = base_weight + delta
    return True


def load_lora_into_transformer(
    transformer: nn.Module,
    lora_path: Union[str, Path, Dict[str, torch.Tensor]],
    scale: float = 1.0,
    prefix: Optional[str] = None,
    adapter_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load and apply LoRA weights to a transformer model.
    
    This is the main entry point for native LoRA loading.
    
    Args:
        transformer: Target transformer model
        lora_path: Path to LoRA file or state dict
        scale: LoRA scale factor (0.0 to 1.0+)
        prefix: Prefix to strip from LoRA keys
        adapter_name: Name for this adapter (for logging)
        
    Returns:
        Dict with loading stats: {"applied": int, "failed": int, "skipped": int}
    """
    adapter_name = _resolve_adapter_name(lora_path, adapter_name)
    logger.info(f"Loading LoRA '{adapter_name}' with scale={scale}")

    state_dict, metadata = load_lora_state_dict(lora_path)
    default_alpha = _extract_default_alpha(metadata)
    network_alphas = _extract_network_alphas(state_dict, metadata)
    prefix = _infer_lora_prefix(prefix, state_dict)
    pairs = extract_lora_pairs(state_dict, prefix=prefix)

    if not pairs:
        logger.warning(f"No valid LoRA pairs found in {adapter_name}")
        return {"applied": 0, "failed": 0, "skipped": len(state_dict)}

    stats = {"applied": 0, "failed": 0, "skipped": 0}
    skipped_text_encoder = False
    for module_path, lora_data in pairs.items():
        if _is_text_encoder_path(module_path):
            skipped_text_encoder = True
            stats["skipped"] += 1
            continue
        success, skipped = _apply_lora_pair(
            transformer,
            module_path,
            lora_data,
            default_alpha,
            network_alphas,
            scale,
            adapter_name,
        )
        if skipped:
            stats["skipped"] += 1
            continue
        if success:
            stats["applied"] += 1
        else:
            stats["failed"] += 1
            logger.warning(f"Failed to apply LoRA to {module_path}")

    if skipped_text_encoder:
        logger.warning(
            "Skipped text-encoder LoRA entries (Z-Image text encoder not currently LoRA-patched)."
        )

    logger.info(
        f"LoRA '{adapter_name}' loaded: "
        f"{stats['applied']} applied, {stats['failed']} failed, {stats['skipped']} skipped"
    )
    return stats


def _resolve_adapter_name(
    lora_path: Union[str, Path, Dict[str, torch.Tensor]], adapter_name: Optional[str]
) -> str:
    if adapter_name:
        return adapter_name
    if isinstance(lora_path, (str, Path)):
        return Path(lora_path).stem
    return "lora"


def _extract_default_alpha(metadata: Optional[Dict[str, Any]]) -> Optional[float]:
    if not metadata:
        return None
    for key in ['ss_network_alpha', 'lora_alpha', 'alpha']:
        if key in metadata:
            try:
                return float(metadata[key])
            except (ValueError, TypeError):
                continue
    return None


def _extract_network_alphas(
    state_dict: Dict[str, torch.Tensor], metadata: Optional[Dict[str, Any]]
) -> Dict[str, float]:
    """Extract per-layer network_alphas if present (diffusers convention)."""
    network_alphas: Dict[str, float] = {}
    # safetensors metadata path
    if metadata and isinstance(metadata, dict):
        meta_alphas = metadata.get("network_alphas")
        if isinstance(meta_alphas, dict):
            for k, v in meta_alphas.items():
                try:
                    network_alphas[k] = float(v)
                except (TypeError, ValueError):
                    continue
    # state_dict path (diffusers saves a tensor/dict under network_alphas)
    sd_alphas = state_dict.get("network_alphas")
    if isinstance(sd_alphas, dict):
        for k, v in sd_alphas.items():
            try:
                network_alphas[k] = float(v)
            except (TypeError, ValueError):
                continue
    return network_alphas


def _infer_lora_prefix(prefix: Optional[str], state_dict: Dict[str, torch.Tensor]) -> Optional[str]:
    if prefix is not None:
        return prefix
    sample_key = next((k for k in state_dict.keys() if 'lora' in k.lower()), None)
    if sample_key is None:
        return None
    if sample_key.startswith('diffusion_model.'):
        return 'diffusion_model'
    if sample_key.startswith('transformer.'):
        return 'transformer'
    if sample_key.startswith('model.'):
        return 'model'
    return None


def _is_text_encoder_path(module_path: str) -> bool:
    """Detect text-encoder LoRA targets to warn/skip (not supported)."""
    lowered = module_path.lower()
    return lowered.startswith("text_encoder") or "/text_encoder" in lowered or "text_encoder" in lowered


def _apply_lora_pair(
    transformer: nn.Module,
    module_path: str,
    lora_data: Dict[str, Any],
    default_alpha: Optional[float],
    network_alphas: Dict[str, float],
    scale: float,
    adapter_name: str,
) -> tuple[bool, bool]:
    down_weight = lora_data['down']
    up_weight = lora_data['up']
    alpha = (
        lora_data.get('alpha')
        or network_alphas.get(module_path)
        or default_alpha
    )

    apply_kwargs = {
        "down_weight": down_weight,
        "up_weight": up_weight,
        "alpha": alpha,
        "scale": scale,
        "adapter_name": adapter_name,
    }

    module = get_module_by_path(transformer, module_path)
    if module is not None:
        return apply_lora_to_linear(module, **apply_kwargs), False

    fused_result = get_fused_attention_module(transformer, module_path)
    if fused_result is None:
        logger.debug(f"Module not found: {module_path}")
        return False, True

    fused_module, _component_name, slice_idx = fused_result
    if slice_idx is not None:
        success = apply_lora_to_fused_qkv(
            fused_module,
            down_weight=down_weight,
            up_weight=up_weight,
            slice_idx=slice_idx,
            alpha=alpha,
            scale=scale,
            adapter_name=adapter_name,
        )
        if success:
            logger.debug(f"Applied LoRA to fused QKV slice {slice_idx} for {module_path}")
        return success, False

    success = apply_lora_to_linear(fused_module, **apply_kwargs)
    if success:
        logger.debug(f"Applied LoRA to attention.out for {module_path}")
    return success, False


def _iterate_lora_layers(transformer: nn.Module):
    """Iterate over all modules that have LoRA support."""
    # UnscaledFP8Linear is imported at module level; avoid re-importing.
    
    for module in transformer.modules():
        if isinstance(module, UnscaledFP8Linear) and hasattr(module, '_lora_layers'):
            yield module


class NativeLoraLoader:
    """
    LoRA loader for native FP8 Z-Image pipelines.
    
    This class manages LoRA loading for models that use FP8Linear layers,
    bypassing PEFT entirely for compatibility.
    
    Features:
    - Non-destructive LoRA loading (additive, not merged)
    - Enable/disable LoRAs without model reload
    - Adjust LoRA scale dynamically
    - Remove LoRAs to free memory
    
    Usage:
        loader = NativeLoraLoader(transformer)
        loader.load_lora("/path/to/lora.safetensors", scale=1.0)
        loader.set_lora_enabled("lora_name", False)  # Disable
        loader.remove_lora("lora_name")  # Remove completely
    """
    
    def __init__(self, transformer: nn.Module):
        """
        Initialize the loader.
        
        Args:
            transformer: Target transformer model
        """
        self.transformer = transformer
        self._loaded_loras: Dict[str, Dict[str, Any]] = {}
    
    def load_lora(
        self,
        path: Union[str, Path, Dict[str, torch.Tensor]],
        scale: float = 1.0,
        adapter_name: Optional[str] = None,
    ) -> bool:
        """
        Load and apply a LoRA.
        
        Args:
            path: Path to LoRA file or state dict
            scale: LoRA scale (0.0-1.0+)
            adapter_name: Optional name for the adapter
            
        Returns:
            True if at least one layer was updated
        """
        if adapter_name is None and isinstance(path, (str, Path)):
            adapter_name = Path(path).stem
        adapter_name = adapter_name or "default"
        
        stats = load_lora_into_transformer(
            self.transformer,
            path,
            scale=scale,
            adapter_name=adapter_name,
        )
        
        self._loaded_loras[adapter_name] = {
            "path": str(path) if isinstance(path, (str, Path)) else "<dict>",
            "scale": scale,
            "stats": stats,
            "enabled": True,
        }
        
        return stats["applied"] > 0
    
    def set_lora_enabled(self, adapter_name: str, enabled: bool) -> bool:
        """Enable or disable a LoRA adapter.
        
        This toggles the LoRA effect without removing the weights from memory.
        
        Args:
            adapter_name: Name of the adapter to toggle
            enabled: Whether to enable or disable
            
        Returns:
            True if the adapter was found and updated
        """
        if adapter_name not in self._loaded_loras:
            logger.warning(f"LoRA '{adapter_name}' not found")
            return False
        
        # Update all layers that have this adapter
        found = False
        for module in _iterate_lora_layers(self.transformer):
            # Check for exact match and QKV slice variants
            for name in [adapter_name, f"{adapter_name}_q", f"{adapter_name}_k", f"{adapter_name}_v"]:
                if module.set_lora_enabled(name, enabled):
                    found = True
        
        if found:
            self._loaded_loras[adapter_name]["enabled"] = enabled
            logger.info(f"LoRA '{adapter_name}' {'enabled' if enabled else 'disabled'}")
        else:
            logger.warning(f"LoRA '{adapter_name}' not found in any layers")
        
        return found
    
    def set_all_loras_enabled(self, enabled: bool) -> None:
        """Enable or disable all LoRA adapters."""
        for module in _iterate_lora_layers(self.transformer):
            module.set_all_loras_enabled(enabled)
        
        for lora_data in self._loaded_loras.values():
            lora_data["enabled"] = enabled
        
        logger.info(f"All LoRAs {'enabled' if enabled else 'disabled'}")
    
    def set_lora_scale(self, adapter_name: str, scale: float) -> bool:
        """Set the scale for a LoRA adapter.
        
        Args:
            adapter_name: Name of the adapter
            scale: New scale value (0.0-1.0+)
            
        Returns:
            True if found and updated
        """
        if adapter_name not in self._loaded_loras:
            logger.warning(f"LoRA '{adapter_name}' not found")
            return False
        
        found = False
        for module in _iterate_lora_layers(self.transformer):
            for name in [adapter_name, f"{adapter_name}_q", f"{adapter_name}_k", f"{adapter_name}_v"]:
                if module.set_lora_scale(name, scale):
                    found = True
        
        if found:
            self._loaded_loras[adapter_name]["scale"] = scale
            logger.info(f"LoRA '{adapter_name}' scale set to {scale}")
        
        return found
    
    def remove_lora(self, adapter_name: str) -> bool:
        """Remove a LoRA adapter completely.
        
        This removes the LoRA weights from memory.
        
        Args:
            adapter_name: Name of the adapter to remove
            
        Returns:
            True if found and removed
        """
        if adapter_name not in self._loaded_loras:
            logger.warning(f"LoRA '{adapter_name}' not found")
            return False
        
        removed_count = 0
        for module in _iterate_lora_layers(self.transformer):
            for name in [adapter_name, f"{adapter_name}_q", f"{adapter_name}_k", f"{adapter_name}_v"]:
                if module.remove_lora(name):
                    removed_count += 1
        
        del self._loaded_loras[adapter_name]
        logger.info(f"LoRA '{adapter_name}' removed from {removed_count} layers")
        
        # Clean up memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return removed_count > 0
    
    def remove_all_loras(self) -> int:
        """Remove all LoRA adapters.
        
        Returns:
            Number of layers that had LoRAs removed
        """
        total_removed = 0
        for module in _iterate_lora_layers(self.transformer):
            total_removed += module.remove_all_loras()
        
        count = len(self._loaded_loras)
        self._loaded_loras.clear()
        logger.info(f"Removed all LoRAs ({count} adapters, {total_removed} layer instances)")
        
        # Clean up memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return total_removed
    
    @property
    def loaded_loras(self) -> Dict[str, Dict[str, Any]]:
        """Get info about loaded LoRAs."""
        return self._loaded_loras.copy()
    
    def get_loaded_lora_names(self) -> List[str]:
        """Get names of loaded LoRAs."""
        return list(self._loaded_loras.keys())
