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

# Variant versions whose models are physically stored as subdirectories
# under SDXL 1.0 rather than under their own top-level version directory.
# Maps variant display name → subdirectory name inside SDXL 1.0.
# Z-Image Turbo is NOT included here — it has its own top-level directory
# at art/models/Z-Image Turbo/ (bootstrap downloads land there).
_VARIANT_TO_SUBDIR: Dict[str, str] = {
    StableDiffusionVersion.SDXL_LIGHTNING.value: "lightning",
    StableDiffusionVersion.SDXL_HYPER.value: "sdxlhyper",
}

# Directories that are NOT pipeline-action folders and should be skipped
# when scanning for models.
_SKIP_DIRS = {"lora", "embedding", "controlnet_processors"}


def _variant_scan_dir(version: str) -> Path | None:
    """Return the physical directory to scan for a variant version.

    Variant models are stored inside ``SDXL 1.0/<variant_subdir>/``,
    so we scan the variant's subdirectory under the parent version.
    Returns ``None`` when the version is not a recognised variant.
    """
    sub_dir = _VARIANT_TO_SUBDIR.get(version)
    if sub_dir is None:
        return None
    return Path(AIRUNNER_BASE_PATH) / "art" / "models" / "SDXL 1.0" / sub_dir


def _find_models_in_dir(scan_dir: Path) -> List[Dict[str, str]]:
    """Find one model file per pipeline-action subdirectory."""
    models: List[Dict[str, str]] = []
    for action_dir in sorted(scan_dir.iterdir()):
        if not action_dir.is_dir():
            continue
        if action_dir.name.lower() in _SKIP_DIRS:
            continue
        for ext in (".safetensors", ".ckpt", ".gguf"):
            for fpath in sorted(action_dir.glob(f"*{ext}")):
                models.append({
                    "label": fpath.name,
                    "value": str(fpath),
                })
                break  # one model per action dir
    return models


def _find_local_models(version: str) -> List[Dict[str, str]]:
    """Scan local filesystem for model files under a given version.

    For variant versions (SDXL Lightning, SDXL Hyper, Z-Image Turbo)
    the models are stored under ``SDXL 1.0/<subdir>/`` so we redirect
    the scan to that location.
    """
    variant_scan = _variant_scan_dir(version)
    if variant_scan is not None:
        if not variant_scan.is_dir():
            return []
        return _find_models_in_dir(variant_scan)

    version_dir = Path(AIRUNNER_BASE_PATH) / "art" / "models" / version
    if not version_dir.is_dir():
        return []
    return _find_models_in_dir(version_dir)


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
