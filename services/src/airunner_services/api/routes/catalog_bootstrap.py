"""Bootstrap data endpoint — provides model metadata to GUI clients."""

from __future__ import annotations

from fastapi import APIRouter

from airunner_services.bootstrap.model_bootstrap_data import (
    model_bootstrap_data,
)
from airunner_services.bootstrap.pipeline_bootstrap_data import (
    pipeline_bootstrap_data,
)
from airunner_services.bootstrap.unified_model_files import (
    UNIFIED_MODEL_FILES,
)

router = APIRouter()


@router.get("/bootstrap")
async def catalog_bootstrap():
    """Return bootstrap data for GUI download wizards and model checkers."""
    return {
        "models": model_bootstrap_data,
        "pipelines": pipeline_bootstrap_data,
        "unified_model_files": UNIFIED_MODEL_FILES,
    }
