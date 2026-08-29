"""VRAM estimation endpoint for GUI model selection widgets."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import torch
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from safetensors import safe_open

from airunner_common.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

#: File suffixes treated as model weights. Single model files may live
#: anywhere on disk (custom in-place models); directory recursion is only
#: permitted inside the app data root (catalog models).
_MODEL_FILE_SUFFIXES = frozenset(
    {".safetensors", ".pt", ".bin", ".pth", ".ckpt", ".gguf"}
)


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
    resolved = _validate_model_path(model_path)
    if resolved is None:
        raise HTTPException(status_code=400, detail="model_path is not valid")
    size = _get_model_file_size_gb(resolved)
    native_dtype = _detect_model_dtype(resolved)
    return VRAMEstimateResponse(
        path=resolved,
        file_size_gb=size,
        native_dtype=native_dtype,
    )


def _validate_model_path(model_path: str) -> str | None:
    """Return one validated absolute model path, or None when rejected.

    Security policy (see GitHub issue #2078 / CodeQL py/path-injection):
    - The value must be a non-empty string with no NUL bytes.
    - Relative paths, absolute ``/`` paths that resolve outside any model
      location, and ``..`` traversal segments are rejected.
    - A single model file (recognised weight suffix) is allowed anywhere on
      disk: the GUI lets the user point a custom model at a ``.safetensors``
      file that has not been imported into the app data folder.
    - A directory is only allowed inside ``AIRUNNER_BASE_PATH`` (catalog
      models), so ``rglob``/``open`` can never enumerate or read arbitrary
      host directories.
    """
    if not isinstance(model_path, str):
        return None
    value = model_path.strip()
    if not value or "\x00" in value:
        return None
    # Normalize (expandvars/expanduser) then fully resolve so ".." segments
    # and symlinks are collapsed before any filesystem access.
    candidate = Path(os.path.expandvars(value)).expanduser().resolve()
    if not candidate.is_absolute():
        return None
    if candidate.is_file():
        if candidate.suffix.lower() in _MODEL_FILE_SUFFIXES:
            return str(candidate)
        return None
    if candidate.is_dir():
        base_root = Path(os.path.abspath(AIRUNNER_BASE_PATH))
        try:
            candidate.relative_to(base_root)
        except ValueError:
            return None
        return str(candidate)
    return None


def _get_model_file_size_gb(model_path: str) -> float:
    """Calculate total size of model files at a path."""
    path = Path(model_path)
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1024**3)
    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file() and file_path.suffix in _MODEL_FILE_SUFFIXES:
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
    path = Path(model_path)
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
