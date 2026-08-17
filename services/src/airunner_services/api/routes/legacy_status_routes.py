"""Status and model-list routes for legacy compatibility endpoints."""

import os
from typing import Any, Dict

from fastapi import APIRouter, Request

from airunner_common.contract_enums import ModelStatus
from airunner_services.api.routes.health import build_health_payload
from airunner_services.model_management.model_registry import ModelRegistry

router = APIRouter()


def current_art_model_status(request: Request) -> str:
    """Return the live art model status from the sidecar art pipeline.

    Values match the model-status strings understood by
    ``SidecarArtClient`` (loaded / unloaded / loading / failed).  The state
    is read without side effects: workers and model managers are only
    inspected when they already exist, and an unconfigured/unloaded pipeline
    truthfully reports ``unloaded`` instead of ``loading``.
    """
    app_instance = getattr(request.app.state, "airunner_app", None)
    worker_manager = getattr(app_instance, "_worker_manager", None)
    worker = getattr(worker_manager, "_sd_worker", None)
    manager = getattr(worker, "_model_manager", None)
    if manager is None:
        return "unloaded"
    try:
        status = manager.model_status.get(manager.model_type)
    except Exception:
        status = None
    if status in (ModelStatus.LOADED, ModelStatus.READY):
        return "loaded"
    if status is ModelStatus.LOADING:
        return "loading"
    if status is ModelStatus.FAILED:
        return "failed"
    if getattr(manager, "model_is_loaded", False):
        return "loaded"
    return "unloaded"


@router.get("/health")
async def legacy_health(request: Request) -> Dict[str, Any]:
    """Return the legacy health payload expected by older clients."""
    return {
        **build_health_payload("ready"),
        "art_model_status": current_art_model_status(request),
        "services": {
            "llm": os.environ.get("AIRUNNER_LLM_ON", "1") == "1",
            "art": os.environ.get("AIRUNNER_SD_ON", "0") == "1",
            "tts": os.environ.get("AIRUNNER_TTS_ON", "0") == "1",
            "stt": os.environ.get("AIRUNNER_STT_ON", "0") == "1",
        },
    }


@router.get("/llm/models")
def legacy_llm_models() -> Dict[str, Any]:
    """Return the legacy model list payload for LLM clients."""
    try:
        registry = ModelRegistry()
        models = []
        for model_id, model_spec in registry.models.items():
            model_type = getattr(getattr(model_spec, "model_type", None), "value", None)
            if model_type != "llm":
                continue
            models.append(
                {
                    "id": model_id,
                    "name": getattr(model_spec, "name", model_id),
                    "loaded": False,
                    "size_mb": getattr(model_spec, "size_mb", None),
                }
            )
        return {"models": models}
    except Exception:
        return {"models": []}