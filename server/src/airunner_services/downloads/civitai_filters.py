"""Filter helpers for CivitAI model search results."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

_ALLOWED_FILE_EXTENSIONS = (".safetensors", ".gguf")
_ALLOWED_FILE_FORMATS = {"safetensor", "gguf"}
_BASE_MODEL_ALIASES = {
    "SDXL 1.0": "SDXL 1.0",
    "SDXL Hyper": "SDXL Hyper",
    "SDXL Lightning": "SDXL Lightning",
    "Z-Image Turbo": "ZImageTurbo",
}
_MODEL_TYPE_ALIASES = {
    "CHECKPOINT": "Checkpoint",
    "MODEL": "Checkpoint",
    "LORA": "LORA",
    "EMBEDDING": "TextualInversion",
    "EMBEDDINGS": "TextualInversion",
    "TEXTUAL EMBEDDING": "TextualInversion",
    "TEXTUALINVERSION": "TextualInversion",
    "TEXTUAL INVERSION": "TextualInversion",
    "ADAPTER": "LORA",
    "CONTROLNET": "LORA",
}


def normalize_base_models(
    base_models: Optional[List[str]],
) -> set[str]:
    """Normalize one requested base-model filter set."""
    return {
        normalize_base_model(m)
        for m in (base_models or [])
        if normalize_base_model(m)
    }


def normalize_base_model(base_model: str) -> str:
    """Normalize one CivitAI base-model label for API filtering."""
    return _BASE_MODEL_ALIASES.get(base_model.strip(), base_model.strip())


def normalize_model_types(
    model_types: Optional[List[str]],
) -> set[str]:
    """Normalize one requested model-type filter set."""
    return {
        normalize_model_type(m)
        for m in (model_types or [])
        if normalize_model_type(m)
    }


def normalize_model_type(model_type: str) -> str:
    """Normalize one CivitAI model-type label for filtering."""
    raw = model_type.strip()
    if not raw:
        return ""
    return _MODEL_TYPE_ALIASES.get(raw.upper(), raw)


def supported_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return supported files for one model version."""
    return [f for f in files if _is_supported_file(f)]


def _is_supported_file(file_info: Dict[str, Any]) -> bool:
    """Return whether one CivitAI file matches the browser policy."""
    name = str(file_info.get("name", "")).lower()
    if not file_info.get("downloadUrl") or not name:
        return False
    if name.endswith(_ALLOWED_FILE_EXTENSIONS):
        return True
    metadata = file_info.get("metadata") or {}
    format_name = str(metadata.get("format", "")).lower()
    return format_name in _ALLOWED_FILE_FORMATS
