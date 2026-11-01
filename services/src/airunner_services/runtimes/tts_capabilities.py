"""Release capability gates for service TTS backends."""

from __future__ import annotations

from typing import Any


TTS_BACKEND_UNAVAILABLE_CODE = "tts_backend_unavailable"
OPENVOICE_DEFERRED_DETAILS = "OpenVoice is unavailable in this release"


def normalize_tts_model_type(value: Any) -> str:
    """Normalize an enum or string TTS backend name for comparisons."""
    resolved = getattr(value, "value", value)
    if resolved is None:
        return ""
    return str(resolved).strip().split(".")[-1].casefold()


def is_deferred_tts_model_type(value: Any) -> bool:
    """Return whether a TTS backend is deferred from this release."""
    return normalize_tts_model_type(value) == "openvoice"


def deferred_tts_metadata(model_type: Any) -> dict[str, str]:
    """Describe an unavailable backend without claiming runtime state."""
    normalized = normalize_tts_model_type(model_type)
    return {
        "model_type": normalized,
        "capability_status": "deferred",
    }


__all__ = [
    "OPENVOICE_DEFERRED_DETAILS",
    "TTS_BACKEND_UNAVAILABLE_CODE",
    "deferred_tts_metadata",
    "is_deferred_tts_model_type",
    "normalize_tts_model_type",
]
