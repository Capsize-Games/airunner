"""
FLUX Model Registry

This module defines available FLUX models from various providers
(HuggingFace, CivitAI) with metadata for the download and management system.
"""

from typing import Dict, List, NamedTuple
from enum import Enum


class ModelProvider(Enum):
    """Model provider sources."""

    LOCAL = "local"
    HUGGINGFACE = "huggingface"
    CIVITAI = "civitai"


class FluxModelInfo(NamedTuple):
    """Information about a FLUX model."""

    id: str  # Unique identifier
    display_name: str  # User-friendly name
    provider: ModelProvider  # Where to download from
    repo_id: str  # HuggingFace repo ID or CivitAI model ID
    variant: str  # dev, schnell, etc.
    size_gb: float  # Approximate size in GB
    description: str  # Brief description
    license: str  # License type
    requires_auth: bool  # Whether HF auth is required


# HuggingFace FLUX Models
HUGGINGFACE_FLUX_MODELS: List[FluxModelInfo] = [
    FluxModelInfo(
        id="flux-dev-hf",
        display_name="FLUX.1-dev (HuggingFace)",
        provider=ModelProvider.HUGGINGFACE,
        repo_id="black-forest-labs/FLUX.1-dev",
        variant="dev",
        size_gb=23.8,
        description="Highest quality FLUX model, 50 steps recommended",
        license="FluxDev Non-Commercial",
        requires_auth=True,  # Requires accepting license
    ),
    FluxModelInfo(
        id="flux-schnell-hf",
        display_name="FLUX.1-schnell (HuggingFace)",
        provider=ModelProvider.HUGGINGFACE,
        repo_id="black-forest-labs/FLUX.1-schnell",
        variant="schnell",
        size_gb=23.8,
        description="Fast FLUX model, 1-4 steps, great quality",
        license="Apache 2.0",
        requires_auth=False,
    ),
]

# CivitAI FLUX Models
# Note: CivitAI model IDs are numeric, format: {model_id}/{version_id}
CIVITAI_FLUX_MODELS: List[FluxModelInfo] = [
    FluxModelInfo(
        id="flux-dev-civit",
        display_name="FLUX.1-dev (CivitAI)",
        provider=ModelProvider.CIVITAI,
        repo_id="618692",  # CivitAI model ID
        variant="dev",
        size_gb=23.8,
        description="FLUX.1-dev from CivitAI mirror",
        license="FluxDev Non-Commercial",
        requires_auth=False,
    ),
    FluxModelInfo(
        id="flux-schnell-civit",
        display_name="FLUX.1-schnell (CivitAI)",
        provider=ModelProvider.CIVITAI,
        repo_id="618691",  # CivitAI model ID
        variant="schnell",
        size_gb=23.8,
        description="FLUX.1-schnell from CivitAI mirror",
        license="Apache 2.0",
        requires_auth=False,
    ),
]

# Combined registry
ALL_FLUX_MODELS: List[FluxModelInfo] = (
    HUGGINGFACE_FLUX_MODELS + CIVITAI_FLUX_MODELS
)


def get_models_by_provider(provider: ModelProvider) -> List[FluxModelInfo]:
    """
    Get all FLUX models for a specific provider.

    Args:
        provider: The model provider

    Returns:
        List of FluxModelInfo for that provider
    """
    return [m for m in ALL_FLUX_MODELS if m.provider == provider]


def get_model_by_id(model_id: str) -> FluxModelInfo:
    """
    Get FLUX model info by ID.

    Args:
        model_id: The model ID

    Returns:
        FluxModelInfo object

    Raises:
        KeyError: If model ID not found
    """
    for model in ALL_FLUX_MODELS:
        if model.id == model_id:
            return model
    raise KeyError(f"Model ID not found: {model_id}")


def get_huggingface_models() -> List[FluxModelInfo]:
    """Get all HuggingFace FLUX models."""
    return get_models_by_provider(ModelProvider.HUGGINGFACE)


def get_civitai_models() -> List[FluxModelInfo]:
    """Get all CivitAI FLUX models."""
    return get_models_by_provider(ModelProvider.CIVITAI)


def get_model_display_names(provider: ModelProvider = None) -> Dict[str, str]:
    """
    Get mapping of model IDs to display names.

    Args:
        provider: Optional provider to filter by

    Returns:
        Dict mapping model ID to display name
    """
    models = get_models_by_provider(provider) if provider else ALL_FLUX_MODELS
    return {m.id: m.display_name for m in models}
