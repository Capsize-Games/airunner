"""Bootstrap data endpoint — provides model/settings metadata to GUI."""

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
from airunner_services.database.bootstrap.controlnet_bootstrap_data import (
    controlnet_bootstrap_data,
)
from airunner_services.database.bootstrap.espeak_settings_data import (
    ESPEAK_SETTINGS_DATA,
)
from airunner_services.database.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner_services.database.bootstrap.openvoice_bootstrap_data import (
    OPENVOICE_FILES,
)
from airunner_services.database.bootstrap.openvoice_languages import (
    OPENVOICE_CORE_MODELS,
    OPENVOICE_LANGUAGE_MODELS,
)
from airunner_services.database.bootstrap.path_settings_data import (
    PATH_SETTINGS_DATA,
)
from airunner_services.database.bootstrap.rmbg_bootstrap_data import (
    RMBG_FILES,
)
from airunner_services.database.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner_services.database.bootstrap.whisper import WHISPER_FILES
from airunner_services.bootstrap.imagefilter_bootstrap_data import (
    imagefilter_bootstrap_data,
)
from airunner_services.bootstrap.prompt_templates_bootstrap_data import (
    prompt_templates_bootstrap_data,
)

router = APIRouter()


@router.get("/bootstrap")
async def catalog_bootstrap():
    """Return all bootstrap data for GUI clients."""
    return {
        "models": model_bootstrap_data,
        "pipelines": pipeline_bootstrap_data,
        "unified_model_files": UNIFIED_MODEL_FILES,
        "controlnet_bootstrap_data": controlnet_bootstrap_data,
        "espeak_settings_data": ESPEAK_SETTINGS_DATA,
        "llm_file_bootstrap_data": LLM_FILE_BOOTSTRAP_DATA,
        "openvoice_files": OPENVOICE_FILES,
        "openvoice_core_models": OPENVOICE_CORE_MODELS,
        "openvoice_language_models": OPENVOICE_LANGUAGE_MODELS,
        "path_settings_data": PATH_SETTINGS_DATA,
        "rmbg_files": RMBG_FILES,
        "sd_file_bootstrap_data": SD_FILE_BOOTSTRAP_DATA,
        "whisper_files": WHISPER_FILES,
        "imagefilter_bootstrap_data": imagefilter_bootstrap_data,
        "prompt_templates_bootstrap_data": prompt_templates_bootstrap_data,
    }
