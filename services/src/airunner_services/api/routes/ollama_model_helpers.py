"""Truthful Ollama metadata and download targets for catalog LLMs."""

from __future__ import annotations

from dataclasses import dataclass

from airunner_services.model_management.model_registry import ModelRegistry
from airunner_services.model_management.model_registry import ModelType
from airunner_services.llm.provider_config import LLMProviderConfig


@dataclass(frozen=True)
class OllamaModelTarget:
    """Catalog-backed Ollama identifier and its supported download target."""

    model_id: str
    repo_id: str
    download_type: str
    gguf_filename: str | None
    context_length: int | None
    function_calling: bool
    vision_capable: bool


def _base_model_name(model_name: str) -> str:
    """Remove Ollama's `:latest` tag while preserving other identifiers."""
    name = model_name.strip()
    if name.lower().endswith(":latest"):
        return name[:-len(":latest")]
    return name


def resolve_ollama_model(model_name: object) -> OllamaModelTarget | None:
    """Resolve a supported local LLM name or alias from the model registry."""
    if not isinstance(model_name, str) or not model_name.strip():
        return None

    model = ModelRegistry().get_model(_base_model_name(model_name))
    if model is None or model.model_type is not ModelType.LLM:
        return None

    model_id = model.model_id
    if not model_id:
        return None
    provider_info = LLMProviderConfig.get_model_info("local", model_id)
    repo_id = model.preferred_download_repo_id or model.huggingface_id
    if not repo_id:
        return None

    context_length_value = provider_info.get("context_length")
    try:
        context_length = int(context_length_value)
    except (TypeError, ValueError):
        context_length = None
    if context_length is not None and context_length < 1:
        context_length = None

    download_type = (
        "gguf" if model.preferred_runtime_format == "gguf" else "llm"
    )
    return OllamaModelTarget(
        model_id=model_id,
        repo_id=repo_id,
        download_type=download_type,
        gguf_filename=model.preferred_download_filename,
        context_length=context_length,
        function_calling=bool(provider_info.get("function_calling")),
        vision_capable=bool(provider_info.get("vision_capable")),
    )


def ollama_show_metadata(model: OllamaModelTarget) -> dict[str, object]:
    """Return only catalog facts supported by the model configuration."""
    model_info: dict[str, object] = {}
    if model.context_length is not None:
        model_info["context_length"] = model.context_length

    capabilities = ["completion"]
    if model.function_calling:
        capabilities.append("tools")
    if model.vision_capable:
        capabilities.append("vision")

    return {"model_info": model_info, "capabilities": capabilities}


def ollama_show_unknown_metadata() -> dict[str, object]:
    """Return the minimum valid shape for a configured but unknown model."""
    return {"model_info": {}, "capabilities": []}


__all__ = [
    "OllamaModelTarget",
    "ollama_show_metadata",
    "ollama_show_unknown_metadata",
    "resolve_ollama_model",
]
