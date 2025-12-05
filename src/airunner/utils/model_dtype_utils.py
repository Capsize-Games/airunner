"""Model dtype detection utilities.

This module provides utilities for detecting the native dtype/precision
of model files, including safetensors and HuggingFace model directories.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Map torch dtype strings to our precision values
TORCH_DTYPE_TO_PRECISION: Dict[str, str] = {
    "torch.float32": "float32",
    "torch.float16": "float16",
    "torch.bfloat16": "bfloat16",
    "torch.float8_e4m3fn": "float8",
    "torch.float8_e5m2": "float8",
    "float32": "float32",
    "float16": "float16",
    "bfloat16": "bfloat16",
    "F32": "float32",
    "F16": "float16",
    "BF16": "bfloat16",
}


def detect_model_dtype_from_config(model_path: str) -> Optional[str]:
    """Detect model dtype from config files in model directory.
    
    Checks for torch_dtype in model_index.json or config.json.
    
    Args:
        model_path: Path to the model directory.
        
    Returns:
        Precision string (e.g., "bfloat16") or None if not detected.
    """
    path = Path(model_path)
    
    if not path.is_dir():
        # For single files, we'll need to inspect the safetensors metadata
        return None
    
    # Check model_index.json first (HuggingFace pipeline format)
    model_index = path / "model_index.json"
    if model_index.exists():
        try:
            with open(model_index, "r") as f:
                config = json.load(f)
            
            # Look for torch_dtype in the config
            if "_torch_dtype" in config:
                dtype_str = config["_torch_dtype"]
                return TORCH_DTYPE_TO_PRECISION.get(dtype_str, dtype_str)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Failed to read model_index.json: {e}")
    
    # Check for config_index.json (FLUX format)
    config_index = path / "config_index.json"
    if config_index.exists():
        try:
            with open(config_index, "r") as f:
                config = json.load(f)
            
            if "torch_dtype" in config:
                dtype_str = config["torch_dtype"]
                return TORCH_DTYPE_TO_PRECISION.get(dtype_str, dtype_str)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Failed to read config_index.json: {e}")
    
    # Check transformer config (common in FLUX/Diffusers models)
    transformer_config = path / "transformer" / "config.json"
    if transformer_config.exists():
        try:
            with open(transformer_config, "r") as f:
                config = json.load(f)
            
            # Look for torch_dtype or default_dtype
            for key in ("torch_dtype", "default_dtype", "_torch_dtype"):
                if key in config:
                    dtype_str = config[key]
                    return TORCH_DTYPE_TO_PRECISION.get(dtype_str, dtype_str)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Failed to read transformer config: {e}")
    
    return None


def detect_model_dtype_from_safetensors(file_path: str) -> Optional[str]:
    """Detect model dtype by inspecting safetensors file metadata.
    
    Reads the first tensor's dtype from a safetensors file to determine
    the native precision.
    
    Args:
        file_path: Path to a safetensors file.
        
    Returns:
        Precision string (e.g., "bfloat16") or None if not detected.
    """
    try:
        from safetensors import safe_open
    except ImportError:
        logger.warning("safetensors not installed, cannot inspect dtype")
        return None
    
    path = Path(file_path)
    if not path.exists() or not path.suffix == ".safetensors":
        return None
    
    try:
        with safe_open(str(path), framework="pt", device="cpu") as f:
            # Check metadata first
            metadata = f.metadata()
            if metadata:
                # Some safetensors files store dtype in metadata
                for key in ("dtype", "torch_dtype", "format"):
                    if key in metadata:
                        dtype_str = metadata[key]
                        if dtype_str in TORCH_DTYPE_TO_PRECISION:
                            return TORCH_DTYPE_TO_PRECISION[dtype_str]
            
            # Fall back to inspecting first tensor
            keys = list(f.keys())
            if keys:
                # Get dtype from first tensor (usually all same dtype)
                tensor = f.get_tensor(keys[0])
                dtype_str = str(tensor.dtype)
                return TORCH_DTYPE_TO_PRECISION.get(dtype_str, None)
    except Exception as e:
        logger.debug(f"Failed to read safetensors file: {e}")
    
    return None


def detect_model_dtype(model_path: str) -> str:
    """Detect the native dtype/precision of a model.
    
    Tries multiple detection methods:
    1. Config files (model_index.json, config.json)
    2. Safetensors file inspection
    3. Default fallback to bfloat16
    
    Args:
        model_path: Path to model file or directory.
        
    Returns:
        Precision string (e.g., "bfloat16"). Defaults to "bfloat16" if not detected.
    """
    path = Path(model_path)
    
    # Try config-based detection first (most reliable)
    if path.is_dir():
        dtype = detect_model_dtype_from_config(model_path)
        if dtype:
            return dtype
        
        # Try inspecting safetensors files in the directory
        for safetensor_file in path.glob("**/*.safetensors"):
            dtype = detect_model_dtype_from_safetensors(str(safetensor_file))
            if dtype:
                return dtype
    elif path.suffix == ".safetensors":
        dtype = detect_model_dtype_from_safetensors(model_path)
        if dtype:
            return dtype
    
    # Default to bfloat16 (most common for modern models)
    logger.debug(f"Could not detect dtype for {model_path}, defaulting to bfloat16")
    return "bfloat16"


def get_model_info(model_path: str) -> Dict[str, Any]:
    """Get comprehensive model information including dtype and size.
    
    Args:
        model_path: Path to model file or directory.
        
    Returns:
        Dictionary with:
            - path: The model path
            - native_dtype: Detected native precision
            - size_gb: File size in GB
            - exists: Whether the path exists
    """
    from airunner.utils.vram_utils import get_model_file_size_gb
    
    path = Path(model_path)
    
    return {
        "path": model_path,
        "native_dtype": detect_model_dtype(model_path) if path.exists() else "bfloat16",
        "size_gb": get_model_file_size_gb(model_path),
        "exists": path.exists(),
    }
