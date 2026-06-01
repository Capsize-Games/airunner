"""Unified model file requirements for all AI Runner model types."""

from airunner.components.data.bootstrap_service import (
    get_llm_file_bootstrap_data,
    get_openvoice_files,
    get_rmbg_files,
    get_sd_file_bootstrap_data,
    get_whisper_files,
)


# Unified model file bootstrap data
UNIFIED_MODEL_FILES = {
    "art": get_sd_file_bootstrap_data(),
    "rmbg": get_rmbg_files(),
    "llm": get_llm_file_bootstrap_data(),
    "stt": get_whisper_files(),
    "tts_openvoice": get_openvoice_files(),
}


def get_required_files_for_model(
    model_type: str,
    model_id: str,
    version: str = None,
    pipeline_action: str = None,
):
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

    elif model_type == "llm":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")

    elif model_type in {"rmbg", "stt"}:
        return data.get(model_id)

    elif model_type == "tts_openvoice":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")

    return None
