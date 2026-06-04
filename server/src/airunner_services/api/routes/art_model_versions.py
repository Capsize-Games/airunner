"""Version helpers for art model discovery routes."""

from pathlib import Path
from typing import Optional

from airunner_services.contract_enums import StableDiffusionVersion
from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)
from airunner_services.settings import AIRUNNER_ART_MODEL_VERSION

from .art_model_resolution import (
    art_model_base_dir,
    generator_settings_record,
    service_base_path,
)

_PREFERRED_VERSIONS = [
    StableDiffusionVersion.Z_IMAGE_TURBO.value,
    StableDiffusionVersion.SDXL1_0.value,
]


# Version selection helpers


def has_any_pipeline(version_dir: Path) -> bool:
    """Return True when one version dir contains any known pipeline dir."""
    return any(
        (version_dir / action).exists()
        for action in ("txt2img", "img2img", "inpaint", "outpaint")
    )


def settings_model_version(
    model_base: Path,
    settings: Optional[GeneratorSettings],
) -> str:
    """Return the configured version when it exists locally."""
    if settings is None:
        return ""
    version = (getattr(settings, "version", "") or "").strip()
    if version and (model_base / version).exists():
        return version
    return ""


def preferred_installed_version(model_base: Path) -> str:
    """Return the first preferred art version installed locally."""
    for version in _PREFERRED_VERSIONS:
        version_dir = model_base / version
        if version_dir.exists() and has_any_pipeline(version_dir):
            return version
    return ""


def known_installed_version(model_base: Path) -> str:
    """Return the first known stable-diffusion version installed locally."""
    if not model_base.exists():
        return ""
    known_values = {version.value for version in StableDiffusionVersion}
    for version_dir in sorted(p for p in model_base.iterdir() if p.is_dir()):
        if version_dir.name in known_values and has_any_pipeline(version_dir):
            return version_dir.name
    return ""


def preferred_model_version(model_base: Path) -> str:
    """Return the best locally available art model version."""
    return preferred_installed_version(model_base) or known_installed_version(
        model_base
    )


def resolve_art_model_version() -> str:
    """Return the active art model version, preferring local availability."""
    configured = (AIRUNNER_ART_MODEL_VERSION or "").strip()
    if configured:
        return configured
    model_base = art_model_base_dir()
    settings = generator_settings_record()
    return (
        settings_model_version(model_base, settings)
        or preferred_model_version(model_base)
        or StableDiffusionVersion.Z_IMAGE_TURBO.value
    )


def resolve_zimage_txt2img_dir() -> str:
    """Return the txt2img directory for Z-Image models."""
    base_path = service_base_path()
    candidates = [
        base_path / "art" / "models" / "Z-Image Turbo" / "txt2img",
        Path("/home/airunner/.local/share/airunner/art/models/Z-Image Turbo/txt2img"),
        Path("/home/joe/.local/share/airunner/art/models/Z-Image Turbo/txt2img"),
    ]
    for candidate in candidates:
        if candidate.expanduser().is_dir():
            return str(candidate.expanduser())
    return ""