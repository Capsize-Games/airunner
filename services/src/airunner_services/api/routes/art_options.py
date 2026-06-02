"""Comprehensive art model options endpoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter

from airunner_services.contract_enums import (
    Scheduler,
    StableDiffusionVersion,
)
from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()

# ── Scheduler assignment per version ──
_SCHEDULERS_BY_VERSION: Dict[str, List[str]] = {
    StableDiffusionVersion.Z_IMAGE_TURBO.value: [
        Scheduler.FLOW_MATCH_EULER.value,
        Scheduler.FLOW_MATCH_LCM.value,
    ],
    StableDiffusionVersion.X4_UPSCALER.value: [
        Scheduler.EULER.value,
        Scheduler.DDIM.value,
        Scheduler.LMS.value,
    ],
}

_DEFAULT_SCHEDULERS: List[str] = [
    Scheduler.EULER_ANCESTRAL.value,
    Scheduler.EULER.value,
    Scheduler.LMS.value,
    Scheduler.HEUN.value,
    Scheduler.DPM.value,
    Scheduler.DPM2.value,
    Scheduler.DPM_PP_2M.value,
    Scheduler.DPM2_K.value,
    Scheduler.DPM2_A_K.value,
    Scheduler.DPM_PP_2M_K.value,
    Scheduler.DPM_PP_2M_SDE_K.value,
    Scheduler.DDIM.value,
    Scheduler.UNIPC.value,
    Scheduler.DDPM.value,
    Scheduler.DEIS.value,
    Scheduler.DPM_2M_SDE_K.value,
    Scheduler.PLMS.value,
]

# ── Precision options (quantization for Z-Image text encoders) ──
_PRECISIONS: List[Dict[str, str]] = [
    {"label": "No Quantization (fp16)", "value": "fp16"},
    {"label": "INT4 (Recommended)", "value": "int4"},
    {"label": "INT8", "value": "int8"},
]

# ── Valid versions ──
_VERSIONS: List[str] = [
    StableDiffusionVersion.SDXL1_0.value,
    StableDiffusionVersion.SDXL_LIGHTNING.value,
    StableDiffusionVersion.SDXL_HYPER.value,
    StableDiffusionVersion.Z_IMAGE_TURBO.value,
]


def _find_local_models(version: str) -> List[Dict[str, str]]:
    """Scan local filesystem for model files under a given version."""
    version_dir = Path(AIRUNNER_BASE_PATH) / "art" / "models" / version
    if not version_dir.is_dir():
        return []
    models: List[Dict[str, str]] = []
    for action_dir in sorted(version_dir.iterdir()):
        if not action_dir.is_dir():
            continue
        # Skip lora directories — LoRA models are shown in the LoRA panel
        if action_dir.name.lower() == "lora":
            continue
        for ext in (".safetensors", ".ckpt", ".gguf"):
            for fpath in sorted(action_dir.glob(f"*{ext}")):
                models.append({
                    "label": fpath.name,
                    "value": str(fpath),
                })
                break  # one model per action dir
    return models


@router.get("/options")
async def art_model_options():
    """Return comprehensive art model configuration data.

    Returns versions, available models per version, schedulers per version,
    and precision options in a single response.
    """
    versions: List[Dict[str, object]] = []
    for version in _VERSIONS:
        scheds = _SCHEDULERS_BY_VERSION.get(
            version, _DEFAULT_SCHEDULERS,
        )
        models = _find_local_models(version)
        versions.append({
            "name": version,
            "models": models,
            "schedulers": [{"label": s, "value": s} for s in scheds],
        })

    return {
        "versions": versions,
        "precisions": _PRECISIONS,
    }
