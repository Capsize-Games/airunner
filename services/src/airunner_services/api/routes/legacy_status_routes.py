"""Status and model-list routes for legacy compatibility endpoints."""

import os
from typing import Any, Dict

from fastapi import APIRouter

from airunner_services.api.routes.health import build_health_payload
from airunner_services.model_management.model_registry import ModelRegistry

router = APIRouter()


@router.get("/health")
async def legacy_health() -> Dict[str, Any]:
    """Return the legacy health payload expected by older clients."""
    return {
        **build_health_payload("ready"),
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