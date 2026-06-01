"""VRAM estimation endpoint for GUI model selection widgets."""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
from fastapi import APIRouter, Query
from pydantic import BaseModel
from safetensors import safe_open

router = APIRouter()
logger = logging.getLogger(__name__)


class VRAMEstimateResponse(BaseModel):
    """VRAM estimate for one model path."""

    path: str
    file_size_gb: float
    native_dtype: str | None = None


@router.get("/vram-estimate", response_model=VRAMEstimateResponse)
async def vram_estimate(
    model_path: str = Query(...),
):
    """Estimate VRAM usage for a model at the given path."""
    size = _get_model_file_size_gb(model_path)
    native_dtype = _detect_model_dtype(model_path)
    return VRAMEstimateResponse(
        path=model_path,
        file_size_gb=size,
        native_dtype=native_dtype,
    )


def _get_model_file_size_gb(model_path: str) -> float:
    """Calculate total size of model files at a path."""
    path = Path(model_path).expanduser()
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1024**3)
    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file() and file_path.suffix in {
            ".safetensors",
            ".pt",
            ".bin",
            ".pth",
            ".ckpt",
            ".gguf",
        }:
            total += file_path.stat().st_size
    return total / (1024**3)


def _detect_model_dtype_from_config(model_path: str) -> str | None:
    """Detect dtype from config.json in a directory."""
    import json
    config_path = Path(model_path) / "config.json"
    if not config_path.exists():
        return None
    try:
        with open(config_path) as fh:
            config = json.load(fh)
        for key in ("torch_dtype", "dtype"):
            value = config.get(key)
            if value:
                return str(value).replace("torch.", "")
    except Exception:
        pass
    return None


def _detect_model_dtype_from_safetensors(file_path: str) -> str | None:
    """Detect dtype from safetensors metadata."""
    try:
        with safe_open(file_path, framework="pt") as sf:
            for key in sf.keys():
                tensor = sf.get_tensor(key)
                return str(tensor.dtype).replace("torch.", "")
    except Exception:
        pass
    return None


def _detect_model_dtype(model_path: str) -> str | None:
    """Detect the native dtype of a model."""
    path = Path(model_path).expanduser()
    if not path.exists():
        return None
    if path.is_dir():
        dtype = _detect_model_dtype_from_config(model_path)
        if dtype:
            return dtype
        for sf in path.rglob("*.safetensors"):
            dtype = _detect_model_dtype_from_safetensors(str(sf))
            if dtype:
                return dtype
    elif path.suffix == ".safetensors":
        return _detect_model_dtype_from_safetensors(model_path)
    return None
