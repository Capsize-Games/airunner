"""Model discovery routes for art API endpoints."""

from pathlib import Path
from typing import List

from fastapi import APIRouter

from airunner_services.model_management.model_registry import (
    ModelProvider,
    ModelRegistry,
    ModelType as RegistryModelType,
)

from .art_contracts import LocalArtModel, LocalArtModelsResponse, ModelInfo
from .art_model_paths import resolve_art_model_path, resolve_zimage_txt2img_dir

router = APIRouter()


# Local checkpoint discovery and registry-backed model discovery stay separate
# so the API can keep serving filesystem paths and registry IDs side by side.


def local_art_models(base_dir: str) -> list[LocalArtModel]:
    """Return local txt2img checkpoint files from one base dir."""
    models: list[LocalArtModel] = []
    if not base_dir:
        return models
    for model_path in sorted(Path(base_dir).glob("*.safetensors")):
        try:
            stats = model_path.stat()
        except Exception:
            continue
        models.append(
            LocalArtModel(
                id=str(model_path),
                name=model_path.name,
                path=str(model_path),
                size_bytes=int(stats.st_size),
            )
        )
    return models


def registry_model_info(configured: str, model) -> ModelInfo:
    """Return one registry-backed art model response entry."""
    return ModelInfo(
        id=model.huggingface_id,
        name=model.name,
        loaded=bool(configured) and configured == model.huggingface_id,
        type=model.model_type.value,
    )


@router.get("/models", response_model=LocalArtModelsResponse)
async def list_models():
    """List local checkpoint files suitable for txt2img."""
    base_dir = resolve_zimage_txt2img_dir()
    return LocalArtModelsResponse(
        base_dir=base_dir,
        models=local_art_models(base_dir),
    )


@router.get("/models/registry", response_model=List[ModelInfo])
async def list_registry_models():
    """List models from AIRunner's internal art model registry."""
    registry = ModelRegistry()
    candidates = registry.list_models(
        provider=ModelProvider.STABLE_DIFFUSION,
        model_type=RegistryModelType.TEXT_TO_IMAGE,
    )
    configured = resolve_art_model_path()
    return [registry_model_info(configured, model) for model in candidates]