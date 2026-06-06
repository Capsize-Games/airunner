"""8-bit BitsAndBytes quantization for SDXL model components.

Quantizes the two CLIP text encoders and the UNet independently, caches
the results on disk so subsequent runs skip the quantization pass entirely.

Cache layout (under AIRUNNER_BASE_PATH/art/cache/sdxl_quantized/):
    <sha256-fingerprint>-text_encoder/
    <sha256-fingerprint>-text_encoder_2/
    <sha256-fingerprint>-unet/

The fingerprint covers: model_dir path + component name + torch version +
transformers/diffusers versions so a cache entry is invalidated whenever
any of those change.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

_QUANTIZED_MODELS = ("text_encoder", "text_encoder_2", "unet")


def _cache_root() -> Path:
    from airunner_services.settings import AIRUNNER_BASE_PATH

    return (
        Path(AIRUNNER_BASE_PATH).expanduser()
        / "art"
        / "cache"
        / "sdxl_quantized"
    )


def _cache_path(model_dir: str, component: str) -> Path:
    import transformers
    import diffusers

    source = os.path.abspath(model_dir)
    fingerprint = "|".join(
        [
            source,
            component,
            str(torch.__version__),
            str(transformers.__version__),
            str(diffusers.__version__),
        ]
    )
    key = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    return _cache_root() / f"{key}-{component}"


def _cache_ready(path: Path) -> bool:
    if not path.is_dir() or not (path / "config.json").is_file():
        return False
    patterns = (
        "*.safetensors",
        "*.safetensors.index.json",
        "*.bin",
        "*.bin.index.json",
    )
    return any(any(path.glob(p)) for p in patterns)


def _save_to_cache(model, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=cache_path.parent))
    try:
        model.save_pretrained(tmp)
        if cache_path.exists():
            shutil.rmtree(cache_path, ignore_errors=True)
        tmp.rename(cache_path)
        logger.info("Cached quantized %s at %s", cache_path.name, cache_path)
    except Exception as exc:
        logger.warning(
            "Failed to cache quantized model at %s: %s", cache_path, exc
        )
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(cache_path, ignore_errors=True)


def _bnb_config_8bit(compute_dtype: torch.dtype):
    from transformers import BitsAndBytesConfig

    return BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_enable_fp32_cpu_offload=False,
    )


# ── Public API ────────────────────────────────────────────────────────────────


def load_quantized_text_encoder(
    model_dir: str,
    compute_dtype: torch.dtype = torch.bfloat16,
) -> Optional[object]:
    """Load (or cache-hit) the SDXL text_encoder with 8-bit quantization."""
    try:
        from transformers import CLIPTextModel

        cache = _cache_path(model_dir, "text_encoder")
        if _cache_ready(cache):
            logger.info("Loading cached quantized text_encoder from %s", cache)
            return CLIPTextModel.from_pretrained(str(cache), device_map="auto")

        logger.info("Quantizing text_encoder (8-bit) from %s", model_dir)
        model = CLIPTextModel.from_pretrained(
            model_dir,
            subfolder="text_encoder",
            quantization_config=_bnb_config_8bit(compute_dtype),
            device_map="auto",
        )
        _save_to_cache(model, cache)
        return model
    except Exception as exc:
        logger.warning(
            "SDXL text_encoder quantization failed, falling back: %s", exc
        )
        return None


def load_quantized_text_encoder_2(
    model_dir: str,
    compute_dtype: torch.dtype = torch.bfloat16,
) -> Optional[object]:
    """Load (or cache-hit) the SDXL text_encoder_2 with 8-bit quantization."""
    try:
        from transformers import CLIPTextModelWithProjection

        cache = _cache_path(model_dir, "text_encoder_2")
        if _cache_ready(cache):
            logger.info(
                "Loading cached quantized text_encoder_2 from %s", cache
            )
            return CLIPTextModelWithProjection.from_pretrained(
                str(cache), device_map="auto"
            )

        logger.info("Quantizing text_encoder_2 (8-bit) from %s", model_dir)
        model = CLIPTextModelWithProjection.from_pretrained(
            model_dir,
            subfolder="text_encoder_2",
            quantization_config=_bnb_config_8bit(compute_dtype),
            device_map="auto",
        )
        _save_to_cache(model, cache)
        return model
    except Exception as exc:
        logger.warning(
            "SDXL text_encoder_2 quantization failed, falling back: %s", exc
        )
        return None


def load_quantized_unet(
    model_dir: str,
    compute_dtype: torch.dtype = torch.bfloat16,
) -> Optional[object]:
    """Load (or cache-hit) the SDXL UNet with 8-bit quantization.

    The UNet contains many nn.Linear layers (cross-attention, feed-forward)
    that benefit from 8-bit quantization.  The VAE and scheduler are left at
    full precision for output quality reasons.
    """
    try:
        from diffusers import UNet2DConditionModel
        from transformers import BitsAndBytesConfig

        cache = _cache_path(model_dir, "unet")
        if _cache_ready(cache):
            logger.info("Loading cached quantized unet from %s", cache)
            return UNet2DConditionModel.from_pretrained(
                str(cache), device_map="auto", torch_dtype=compute_dtype
            )

        logger.info("Quantizing unet (8-bit) from %s", model_dir)
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
        model = UNet2DConditionModel.from_pretrained(
            model_dir,
            subfolder="unet",
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=compute_dtype,
        )
        _save_to_cache(model, cache)
        return model
    except Exception as exc:
        logger.warning("SDXL unet quantization failed, falling back: %s", exc)
        return None
