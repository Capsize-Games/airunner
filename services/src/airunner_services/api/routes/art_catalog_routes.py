"""Model discovery routes for art API endpoints."""

from typing import List

from fastapi import APIRouter

from airunner_services.model_management.model_registry import (
    ModelProvider,
    ModelRegistry,
    ModelType as RegistryModelType,
)

from .art_contracts import (
    ArtModelsVersion,
    LocalArtModel,
    LocalArtModelsResponse,
    ModelInfo,
)
from .art_model_base import art_model_base_dir
from .art_model_resolution import resolve_art_model_path
from .art_model_scan import installed_art_models
from .art_schedulers import list_scheduler_names

router = APIRouter()


# Local checkpoint discovery and registry-backed model discovery stay separate
# so the API can keep serving filesystem paths and registry IDs side by side.


def group_models_by_version(
    models: list[LocalArtModel],
) -> list[ArtModelsVersion]:
    """Group one flat model list by version name."""
    groups: dict[str, list[LocalArtModel]] = {}
    for model in models:
        groups.setdefault(model.version, []).append(model)
    return [
        ArtModelsVersion(version=version, models=grouped)
        for version, grouped in sorted(groups.items())
    ]


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
    """List installed models per version plus valid schedulers."""
    model_base = art_model_base_dir()
    models = installed_art_models(model_base)
    return LocalArtModelsResponse(
        base_dir=str(model_base),
        models=models,
        versions=group_models_by_version(models),
        schedulers=list_scheduler_names(),
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
