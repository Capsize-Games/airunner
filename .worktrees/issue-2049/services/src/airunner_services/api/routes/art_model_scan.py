"""Filesystem scan helpers for art model discovery."""

from pathlib import Path
from typing import Optional

from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)

from .art_model_base import (
    art_model_base_dir,
    configured_art_model_path,
    existing_path,
    generator_settings_record,
)


# Filesystem-backed model selection


def choose_from_action_dir(action_dir: Path) -> str:
    """Return the preferred model path from one pipeline action dir."""
    if (action_dir / "model_index.json").exists():
        return str(action_dir)
    for ext in (".safetensors", ".ckpt", ".gguf"):
        candidates = sorted(action_dir.glob(f"*{ext}"))
        if candidates:
            return str(candidates[0])
    return ""


def version_model_path(
    model_base: Path,
    version: str,
    action: str,
) -> str:
    """Return the preferred model path for one version/action pair."""
    if not version:
        return ""
    action_dir = model_base / version / action
    if action_dir.exists():
        chosen = choose_from_action_dir(action_dir)
        if chosen:
            return chosen
    version_dir = model_base / version
    if not version_dir.exists():
        return ""
    for maybe_action in sorted(p for p in version_dir.iterdir() if p.is_dir()):
        chosen = choose_from_action_dir(maybe_action)
        if chosen:
            return chosen
    return ""


def first_model_path(model_base: Path) -> str:
    """Return the first model path found under the art model base dir."""
    if not model_base.exists():
        return ""
    for version_dir in sorted(p for p in model_base.iterdir() if p.is_dir()):
        for action_dir in sorted(p for p in version_dir.iterdir() if p.is_dir()):
            chosen = choose_from_action_dir(action_dir)
            if chosen:
                return chosen
    return ""


def pipeline_action(settings: Optional[GeneratorSettings]) -> str:
    """Return the configured pipeline action name."""
    if settings is None:
        return "txt2img"
    action = (getattr(settings, "pipeline_action", "") or "").strip()
    return action or "txt2img"


def resolve_art_model_path(model_version: Optional[str] = None) -> str:
    """Resolve the local art model identifier/path."""
    configured = configured_art_model_path()
    if configured:
        return configured
    settings = generator_settings_record()
    custom_path = existing_path(getattr(settings, "custom_path", "") or "")
    if custom_path:
        return custom_path
    model_base = art_model_base_dir()
    version = (model_version or "").strip()
    action = pipeline_action(settings)
    return version_model_path(model_base, version, action) or first_model_path(
        model_base
    )