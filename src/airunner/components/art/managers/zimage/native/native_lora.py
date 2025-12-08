"""
Native LoRA implementation for FP8 Z-Image models.

This module provides LoRA support for FP8Linear layers without PEFT dependency.
LoRA weights are merged directly into the base weights during loading.

Key differences from PEFT-based LoRA:
- Works with FP8Linear layers directly
- Merges weights at load time (no separate A/B matrices during inference)
- Simpler implementation, lower memory overhead
- No hot-swapping - requires reload to change LoRA
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
import torch.nn as nn
from safetensors import safe_open
from safetensors.torch import load_file as load_safetensors

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
) -> bool:
    """
    Apply LoRA weights to a Linear or FP8Linear layer.
    
    For FP8Linear, we dequantize, merge, and leave as float (no re-quantization).
    
    Args:
        linear: Target linear layer
        down_weight: LoRA down/A weight
        up_weight: LoRA up/B weight
        alpha: LoRA alpha
        scale: LoRA scale factor
        
    Returns:
        True if successful, False otherwise
    """
    # Import here to avoid circular imports
    from airunner.components.art.managers.zimage.native.fp8_ops import FP8Linear, QuantizedTensor
    
    # Get base weight
    try:
        if isinstance(linear, FP8Linear):
            weight_attr = getattr(linear, 'weight', None)
            if weight_attr is None:
                logger.warning(f"FP8Linear has no weight set (weight is None)")
                return False
            # Check if it's a QuantizedTensor
            if hasattr(weight_attr, 'dequantize'):
                base_weight = weight_attr.dequantize()
            else:
                logger.warning(f"FP8Linear weight is not a QuantizedTensor: {type(weight_attr)}")
                return False
        elif isinstance(linear, nn.Linear):
            base_weight = linear.weight.data
        else:
            logger.warning(f"Unsupported layer type: {type(linear)}")
            return False
    except Exception as e:
        logger.warning(f"Failed to get base weight: {e}")
        return False
    
    # Compute LoRA delta
    device = base_weight.device
    dtype = base_weight.dtype
    
    down_weight = down_weight.to(device=device, dtype=dtype)
    up_weight = up_weight.to(device=device, dtype=dtype)
    
    delta = compute_lora_weight(down_weight, up_weight, alpha=alpha, scale=scale)
    
    # Verify shapes match
    if delta.shape != base_weight.shape:
        logger.warning(
            f"Shape mismatch: base={base_weight.shape}, delta={delta.shape}"
        )
        return False
    
    # Merge weights
    merged_weight = base_weight + delta
    
    # Update the layer
    if isinstance(linear, FP8Linear):
        # Convert FP8Linear to regular Linear after LoRA merge
        # (We lose FP8 compression but gain LoRA effects)
        linear.weight = QuantizedTensor.from_fp8_with_scale(
            merged_weight.to(torch.float8_e4m3fn),
            torch.tensor(1.0, device=device),  # Scale of 1 since already in correct range
            dtype
        )
        # Alternative: Store as regular float weight
        # This uses more memory but is more accurate
        if not hasattr(linear, '_merged_weight'):
            linear._merged_weight = None
        linear._merged_weight = merged_weight
    else:
        linear.weight.data = merged_weight
    
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
    adapter_name = adapter_name or Path(lora_path).stem if isinstance(lora_path, (str, Path)) else "lora"
    
    logger.info(f"Loading LoRA '{adapter_name}' with scale={scale}")
    
    # Load state dict
    state_dict, metadata = load_lora_state_dict(lora_path)
    
    # Extract alpha from metadata if available
    default_alpha = None
    if metadata:
        for key in ['ss_network_alpha', 'lora_alpha', 'alpha']:
            if key in metadata:
                try:
                    default_alpha = float(metadata[key])
                    logger.debug(f"Using alpha={default_alpha} from metadata")
                    break
                except (ValueError, TypeError):
                    pass
    
    # Auto-detect prefix if not provided
    if prefix is None:
        sample_key = next((k for k in state_dict.keys() if 'lora' in k.lower()), None)
        if sample_key:
            if sample_key.startswith('diffusion_model.'):
                prefix = 'diffusion_model'
            elif sample_key.startswith('transformer.'):
                prefix = 'transformer'
            elif sample_key.startswith('model.'):
                prefix = 'model'
    
    # Extract LoRA pairs
    pairs = extract_lora_pairs(state_dict, prefix=prefix)
    
    if not pairs:
        logger.warning(f"No valid LoRA pairs found in {adapter_name}")
        return {"applied": 0, "failed": 0, "skipped": len(state_dict)}
    
    # Apply LoRA to matching modules
    stats = {"applied": 0, "failed": 0, "skipped": 0}
    
    for module_path, lora_data in pairs.items():
        down_weight = lora_data['down']
        up_weight = lora_data['up']
        alpha = lora_data.get('alpha') or default_alpha
        
        # Find target module
        module = get_module_by_path(transformer, module_path)
        
        if module is None:
            logger.debug(f"Module not found: {module_path}")
            stats["skipped"] += 1
            continue
        
        # Apply LoRA
        success = apply_lora_to_linear(
            module,
            down_weight=down_weight,
            up_weight=up_weight,
            alpha=alpha,
            scale=scale,
        )
        
        if success:
            stats["applied"] += 1
            logger.debug(f"Applied LoRA to {module_path}")
        else:
            stats["failed"] += 1
            logger.warning(f"Failed to apply LoRA to {module_path}")
    
    logger.info(
        f"LoRA '{adapter_name}' loaded: "
        f"{stats['applied']} applied, {stats['failed']} failed, {stats['skipped']} skipped"
    )
    
    return stats


class NativeLoraLoader:
    """
    LoRA loader for native FP8 Z-Image pipelines.
    
    This class manages LoRA loading for models that use FP8Linear layers,
    bypassing PEFT entirely for compatibility.
    
    Usage:
        loader = NativeLoraLoader(transformer)
        loader.load_lora("/path/to/lora.safetensors", scale=1.0)
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
        }
        
        return stats["applied"] > 0
    
    @property
    def loaded_loras(self) -> Dict[str, Dict[str, Any]]:
        """Get info about loaded LoRAs."""
        return self._loaded_loras.copy()
    
    def get_loaded_lora_names(self) -> List[str]:
        """Get names of loaded LoRAs."""
        return list(self._loaded_loras.keys())
