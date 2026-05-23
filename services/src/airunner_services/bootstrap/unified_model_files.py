"""Service-owned unified model file requirements for all model families."""

from __future__ import annotations

from airunner_services.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner_services.bootstrap.openvoice_bootstrap_data import OPENVOICE_FILES
from airunner_services.bootstrap.rmbg_bootstrap_data import RMBG_FILES
from airunner_services.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner_services.bootstrap.whisper import WHISPER_FILES


UNIFIED_MODEL_FILES = {
    "art": SD_FILE_BOOTSTRAP_DATA,
    "rmbg": RMBG_FILES,
    "llm": LLM_FILE_BOOTSTRAP_DATA,
    "stt": WHISPER_FILES,
    "tts_openvoice": OPENVOICE_FILES,
}


def get_required_files_for_model(
    model_type: str,
    model_id: str,
    version: str | None = None,
    pipeline_action: str | None = None,
):
    """Return required files for the requested model entry."""
    if model_type not in UNIFIED_MODEL_FILES:
        return None

    data = UNIFIED_MODEL_FILES[model_type]
    if model_type == "art":
        if not version or not pipeline_action:
            return None
        version_data = data.get(version)
        if not version_data:
            return None
        return version_data.get(pipeline_action)
    if model_type == "llm":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")
    if model_type == "tts_openvoice":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")
    return data.get(model_id)


__all__ = ["UNIFIED_MODEL_FILES", "get_required_files_for_model"]