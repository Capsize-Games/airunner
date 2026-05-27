"""Model-loading helpers for the native Z-Image text encoder."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Optional

import torch
import transformers
from safetensors import safe_open
from transformers import AutoConfig, AutoModel, BitsAndBytesConfig

from airunner_services.art.managers.zimage.native.zimage_tokenizer import (
    ZImageTokenizer,
)
from airunner_services.settings import AIRUNNER_BASE_PATH

logger = logging.getLogger(__name__)

_SAFE_TENSORS_FORMATS = {"pt", "tf", "flax", "mlx"}


def _quantized_cache_root() -> Path:
    """Return the app-managed cache root for quantized text encoders."""
    return (
        Path(AIRUNNER_BASE_PATH).expanduser()
        / "art"
        / "cache"
        / "text_encoder_quantized"
    )


def _quantized_cache_path(
    model_path: str,
    quantization: str,
    dtype_name: str,
) -> Path:
    """Return the cache path for one quantized text encoder source."""
    source = os.path.abspath(model_path)
    fingerprint = "|".join(
        [
            source,
            quantization,
            dtype_name,
            str(torch.__version__),
            str(transformers.__version__),
        ]
    )
    cache_key = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    return _quantized_cache_root() / f"{cache_key}-{quantization}"


def _quantized_cache_is_ready(cache_path: Path) -> bool:
    """Return True when one quantized cache directory looks complete."""
    if not cache_path.is_dir() or not (cache_path / "config.json").is_file():
        return False
    patterns = (
        "*.safetensors",
        "*.safetensors.index.json",
        "*.bin",
        "*.bin.index.json",
    )
    return any(any(cache_path.glob(pattern)) for pattern in patterns)


def _remove_cache_dir(path: Path) -> None:
    """Delete one cache directory or best-effort partial cache."""
    shutil.rmtree(path, ignore_errors=True)


def _resolve_transformers_weights_override(model_path: str) -> Optional[str]:
    """Prefer the sharded index when a merged safetensors file is nonstandard."""
    if not os.path.isdir(model_path):
        return None
    index_name = "model.safetensors.index.json"
    index_path = os.path.join(model_path, index_name)
    merged_path = os.path.join(model_path, "model.safetensors")
    if not os.path.isfile(index_path) or not os.path.isfile(merged_path):
        return None
    try:
        with safe_open(merged_path, framework="pt") as handle:
            metadata = handle.metadata() or {}
    except Exception as exc:
        logger.warning(
            "Failed to inspect merged text encoder safetensors at %s: %s. "
            "Falling back to sharded index.",
            merged_path,
            exc,
        )
        return index_name
    file_format = metadata.get("format")
    if file_format in _SAFE_TENSORS_FORMATS:
        return None
    logger.info(
        "Detected nonstandard safetensors metadata for %s (format=%s). "
        "Using sharded text encoder weights via %s instead.",
        merged_path,
        file_format,
        index_name,
    )
    return index_name


class ZImageTextEncoderLoaderHelper:
    """Load and cache the underlying transformer model for one encoder."""

    def __init__(self, owner) -> None:
        """Store the owning text encoder instance."""
        self._owner = owner

    def load_model(self, model_path: str):
        """Load the text encoder model and tokenizer."""
        try:
            load_path = model_path
            cache_path = self.quantized_cache_path(model_path)
            use_quantized_cache = self.should_use_quantized_cache()
            cache_hit = use_quantized_cache and _quantized_cache_is_ready(cache_path)
            if cache_hit:
                load_path = str(cache_path)
                logger.info(
                    "Loading cached %s text encoder weights",
                    self._owner.quantization,
                )
            config = AutoConfig.from_pretrained(load_path, trust_remote_code=True)
            transformers_weights = _resolve_transformers_weights_override(load_path)
            if transformers_weights is not None:
                config.transformers_weights = transformers_weights
            quantization_config = self._quantization_config(cache_hit)
            device_map = self._device_map(cache_hit, quantization_config)
            load_kwargs = {
                "config": config,
                "quantization_config": quantization_config,
                "dtype": self._owner.dtype,
                "device_map": device_map,
                "trust_remote_code": True,
            }
            if device_map is not None and self._owner._max_memory is not None:
                load_kwargs["max_memory"] = self._owner._max_memory
            self._owner.model = AutoModel.from_pretrained(load_path, **load_kwargs)
            self._move_model_to_device(cache_hit, quantization_config)
            self._owner.model.eval()
            if use_quantized_cache and not cache_hit:
                self.save_quantized_cache(cache_path)
            tokenizer_path = self._owner.tokenizer_path or model_path
            self._owner.tokenizer = ZImageTokenizer(tokenizer_path)
            logger.info("Loaded text encoder from %s", model_path)
        except Exception as exc:
            logger.error("Failed to load text encoder: %s", exc)
            raise

    def quantized_cache_path(self, model_path: str) -> Path:
        """Return the app-managed cache directory for this model."""
        quantization = self._owner.quantization or "none"
        dtype_name = str(self._owner.dtype).replace("torch.", "")
        return _quantized_cache_path(model_path, quantization, dtype_name)

    def should_use_quantized_cache(self) -> bool:
        """Return True when this load should persist pre-quantized weights."""
        return self._owner.quantization in {"4bit", "8bit"}

    def save_quantized_cache(self, cache_path: Path) -> None:
        """Persist one pre-quantized text encoder for future cold loads."""
        if self._owner.model is None or _quantized_cache_is_ready(cache_path):
            return
        cache_root = cache_path.parent
        cache_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(dir=cache_root))
        try:
            self._owner.model.save_pretrained(temp_dir)
            _remove_cache_dir(cache_path)
            temp_dir.rename(cache_path)
            logger.info(
                "Saved cached %s text encoder weights",
                self._owner.quantization,
            )
        except Exception as exc:
            logger.warning(
                "Failed to save cached %s text encoder weights: %s",
                self._owner.quantization,
                exc,
            )
            _remove_cache_dir(cache_path)
            _remove_cache_dir(temp_dir)

    def _quantization_config(self, cache_hit: bool) -> Optional[BitsAndBytesConfig]:
        """Build the quantization config for one model load."""
        if cache_hit:
            return None
        if self._owner.quantization == "4bit":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=self._owner.dtype,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        if self._owner.quantization != "8bit":
            return None
        quantization_kwargs = {"load_in_8bit": True}
        if self._owner._enable_cpu_offload:
            quantization_kwargs["llm_int8_enable_fp32_cpu_offload"] = True
        return BitsAndBytesConfig(**quantization_kwargs)

    def _device_map(
        self,
        cache_hit: bool,
        quantization_config: Optional[BitsAndBytesConfig],
    ) -> Optional[str]:
        """Choose the device_map for one model load."""
        device_map = self._owner._device_map
        if device_map is None and (
            quantization_config is not None or cache_hit or self._owner._device is None
        ):
            return "auto"
        return device_map

    def _move_model_to_device(
        self,
        cache_hit: bool,
        quantization_config: Optional[BitsAndBytesConfig],
    ) -> None:
        """Move the loaded model to the requested device when needed."""
        if (
            self._owner._device is None
            or quantization_config is not None
            or cache_hit
            or self._owner.model is None
        ):
            return
        self._owner.model = self._owner.model.to(self._owner._device)