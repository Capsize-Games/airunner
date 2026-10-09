"""Filesystem scan helpers for art model discovery."""

import os
from pathlib import Path
from typing import Optional

from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)

from .art_contracts import LocalArtModel
from .art_model_base import (
    art_model_base_dir,
    configured_art_model_path,
    existing_path,
    generator_settings_record,
)

_MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".gguf")
_PIPELINE_ACTIONS = ("txt2img", "img2img", "inpaint", "outpaint")


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


# Installed-model listing (issue #2228)


def dir_size_bytes(path: Path) -> int:
    """Return the recursive size of one directory, or 0 on error."""
    total = 0
    try:
        walker = os.walk(path)
    except OSError:
        return 0
    for root, _dirs, files in walker:
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return total


def model_entry_size(path: Path) -> int:
    """Return the size of one model file or bundle dir, 0 on error."""
    try:
        if path.is_dir():
            return dir_size_bytes(path)
        return int(path.stat().st_size)
    except OSError:
        return 0


def is_loadable_model(entry: Path) -> bool:
    """Return True for a checkpoint file or diffusers bundle dir."""
    if entry.is_dir():
        return (entry / "model_index.json").is_file()
    return entry.suffix.lower() in _MODEL_EXTENSIONS


def model_entry(
    path: Path, version: str, action: str
) -> LocalArtModel:
    """Return one installed-model response entry for a path."""
    return LocalArtModel(
        id=str(path),
        name=path.name,
        path=str(path),
        size_bytes=model_entry_size(path),
        version=version,
        pipeline=action,
    )


def action_dir_models(
    action_dir: Path, version: str, action: str
) -> list[LocalArtModel]:
    """Return every loadable model inside one pipeline action dir."""
    models: list[LocalArtModel] = []
    if (action_dir / "model_index.json").is_file():
        models.append(model_entry(action_dir, version, action))
    try:
        entries = sorted(action_dir.iterdir())
    except OSError:
        return models
    for entry in entries:
        if is_loadable_model(entry):
            models.append(model_entry(entry, version, action))
    return models


def version_action_models(version_dir: Path) -> list[LocalArtModel]:
    """Return every loadable model under one version directory."""
    models: list[LocalArtModel] = []
    for action in _PIPELINE_ACTIONS:
        action_dir = version_dir / action
        if action_dir.is_dir():
            models.extend(
                action_dir_models(action_dir, version_dir.name, action)
            )
    return models


def installed_art_models(model_base: Path) -> list[LocalArtModel]:
    """Return every installed model for every version on disk.

    Only version directories containing a known pipeline action are
    listed, so helper directories (Safety Checker, civitai) stay out.
    """
    try:
        version_dirs = sorted(
            entry for entry in model_base.iterdir() if entry.is_dir()
        )
    except OSError:
        return []
    models: list[LocalArtModel] = []
    for version_dir in version_dirs:
        models.extend(version_action_models(version_dir))
    return models


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