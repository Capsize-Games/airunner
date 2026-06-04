"""Model path resolution for HuggingFace model downloads.

Determines the correct filesystem path where a model's files should be
placed, based on model type and repository ID.
"""

from pathlib import Path


_MODEL_TYPES_WITH_FLAT_DIR = frozenset({"art", "stt", "tts_openvoice", "rmbg"})


def resolve_model_path(
    output_dir: str,
    repo_id: str,
    model_type: str,
) -> Path:
    """Return the final model directory for a given *model_type*.

    Art, STT, TTS, and RMBG models store their files directly in the
    provided *output_dir*.  All other model types (LLM, GGUF) create a
    subdirectory named after the last component of the repository ID.
    """
    if model_type in _MODEL_TYPES_WITH_FLAT_DIR:
        return Path(output_dir)
    repo_name = repo_id.split("/")[-1]
    return Path(output_dir) / repo_name
