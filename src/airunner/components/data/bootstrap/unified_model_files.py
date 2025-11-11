"""Unified model file requirements for all AI Runner model types.

This module consolidates file requirements from:
- Art models (SD, SDXL, FLUX, ControlNet)
- LLM models (Llama, Qwen, etc.)
- STT models (Whisper)
- TTS models (OpenVoice, SpeechT5)
"""

from airunner.settings import AIRUNNER_ART_ENABLED

# Import existing bootstrap data
from airunner.components.art.data.bootstrap.sd_file_bootstrap_data import (
    SD_FILE_BOOTSTRAP_DATA,
)
from airunner.components.llm.data.bootstrap.llm_file_bootstrap_data import (
    LLM_FILE_BOOTSTRAP_DATA,
)
from airunner.components.stt.data.bootstrap.whisper import WHISPER_FILES
from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import (
    OPENVOICE_FILES,
)
from airunner.components.tts.data.bootstrap.speech_t5 import SPEECH_T5_FILES


# Unified model file bootstrap data
UNIFIED_MODEL_FILES = {
    "art": SD_FILE_BOOTSTRAP_DATA,
    "llm": LLM_FILE_BOOTSTRAP_DATA,
    "stt": WHISPER_FILES,
    "tts_openvoice": OPENVOICE_FILES,
    "tts_speecht5": SPEECH_T5_FILES,
}


def get_required_files_for_model(
    model_type: str,
    model_id: str,
    version: str = None,
    pipeline_action: str = None,
):
    """Get required files for a model.

    Args:
        model_type: Type of model (art, llm, stt, tts_openvoice, tts_speecht5)
        model_id: Model identifier (repo_id or version name)
        version: Model version (for art models like "Flux.1 S", "SDXL 1.0")
        pipeline_action: Pipeline action (for art models like "txt2img", "inpaint")

    Returns:
        List of required file paths, or None if not found

    Examples:
        >>> get_required_files_for_model("art", "Flux.1 S", "SDXL 1.0", "txt2img")
        ["scheduler/scheduler_config.json", ...]
        >>> get_required_files_for_model("stt", "openai/whisper-tiny")
        ["config.json", "model.safetensors", ...]
        >>> get_required_files_for_model("llm", "meta-llama/Llama-3.1-8B-Instruct")
        ["config.json", "model-00001-of-00004.safetensors", ...]
    """
    if model_type not in UNIFIED_MODEL_FILES:
        return None

    data = UNIFIED_MODEL_FILES[model_type]

    # Art models use version + pipeline_action lookup
    if model_type == "art":
        if not version or not pipeline_action:
            return None
        version_data = data.get(version)
        if not version_data:
            return None
        return version_data.get(pipeline_action)

    # LLM models use direct repo_id lookup
    elif model_type == "llm":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")

    # STT models (Whisper) use repo_id lookup
    elif model_type == "stt":
        return data.get(model_id)

    # TTS OpenVoice models use repo_id lookup with nested structure
    elif model_type == "tts_openvoice":
        model_data = data.get(model_id)
        if not model_data:
            return None
        return model_data.get("files")

    # TTS SpeechT5 models use repo_id lookup
    elif model_type == "tts_speecht5":
        return data.get(model_id)

    return None
