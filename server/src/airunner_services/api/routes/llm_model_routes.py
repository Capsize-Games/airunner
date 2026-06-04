"""Model management routes for runtime-backed LLM endpoints."""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException, Request

from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.llm.provider_config import LLMProviderConfig
from airunner_services.model_management.model_registry import ModelRegistry
from airunner_services.runtimes.contracts import RuntimeAction
from airunner_services.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .llm_contracts import ModelInfo, ModelLoadRequest
from .llm_runtime import require_runtime_registry, resolve_llm_client, run_runtime_action

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def selected_model_id(settings: Any) -> str:
    """Return the configured local model id when one can be resolved."""
    if settings is None:
        return ""
    for value in (
        getattr(settings, "model_id", None),
        getattr(settings, "model_version", None),
        getattr(settings, "model_path", None),
    ):
        if not value:
            continue
        resolved = LLMProviderConfig.resolve_model_id("local", str(value))
        if resolved:
            return resolved
    return ""


def persist_model_selection(model_id: str) -> str:
    """Persist the selected local model in the existing settings tables."""
    settings = LLMGeneratorSettings.objects.first()
    if settings is None:
        raise HTTPException(status_code=503, detail="LLM settings unavailable")
    resolved_id = LLMProviderConfig.resolve_model_id("local", model_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="LLM model not found")
    path_settings = PathSettings.objects.first()
    base_path = getattr(path_settings, "base_path", AIRUNNER_BASE_PATH)
    model_path = LLMProviderConfig.get_expected_local_artifact_path(
        base_path,
        "local",
        model_id=resolved_id,
    )
    saved = LLMGeneratorSettings.objects.update(
        pk=getattr(settings, "id", None),
        model_id=resolved_id,
        model_version=resolved_id,
        model_path=model_path,
    )
    if not saved:
        raise HTTPException(
            status_code=503,
            detail="Unable to persist LLM model selection",
        )
    return resolved_id


@router.get("/models", response_model=List[ModelInfo])
async def list_models(_req: Request):
    """List available local LLM models."""
    settings = LLMGeneratorSettings.objects.first()
    current_model_id = selected_model_id(settings)
    try:
        registry = ModelRegistry()
        models = []
        for model_id, model_spec in registry.models.items():
            if model_spec.model_type.value != "llm":
                continue
            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_spec.name,
                    loaded=(model_id == current_model_id),
                    size_mb=model_spec.size_mb,
                )
            )
        return models
    except Exception as exc:
        logger.error(f"Error listing models: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(exc)}",
        ) from exc


@router.post("/load")
async def load_model(request: ModelLoadRequest, req: Request):
    """Persist the selected model and load it through the runtime boundary."""
    resolved_id = persist_model_selection(request.model_id)
    client = resolve_llm_client(require_runtime_registry(req))
    await run_runtime_action(client, RuntimeAction.LOAD_MODEL)
    return {"status": "success", "model": resolved_id}


@router.post("/unload")
async def unload_model(req: Request):
    """Unload the active local LLM through the runtime boundary."""
    client = resolve_llm_client(require_runtime_registry(req))
    await run_runtime_action(client, RuntimeAction.UNLOAD_MODEL)
    return {"status": "success"}