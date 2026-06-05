"""Thread-safe runtime helpers for Melo vendor integrations."""

import os
from pathlib import Path
from typing import Optional

from airunner_services.settings import AIRUNNER_BASE_PATH
from airunner_services.utils.application import get_logger


def get_melo_logger():
    """Return the shared logger without constructing the GUI API."""
    return get_logger("AI Runner")


def _get_path_settings() -> Optional[object]:
    """Return persisted path settings when available."""
    try:
        from airunner_services.database.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def _normalize_tts_model_root(path: str) -> str:
    """Return the shared TTS root for one configured model path."""
    expanded = os.path.expanduser(path)
    candidate = Path(expanded)
    if (
        candidate.name == "openvoice"
        or (candidate / "checkpoints_v2").exists()
    ):
        return str(candidate.parent)
    return expanded


def resolve_tts_model_root() -> str:
    """Return the configured TTS model root without bootstrapping the app."""
    env_override = os.environ.get("AIRUNNER_TTS_MODEL_PATH", "").strip()
    if env_override:
        return _normalize_tts_model_root(env_override)

    path_settings = _get_path_settings()
    if path_settings is not None:
        tts_model_path = getattr(path_settings, "tts_model_path", None)
        if tts_model_path:
            return _normalize_tts_model_root(tts_model_path)

        base_path = getattr(path_settings, "base_path", None)
        if base_path:
            expanded_base_path = os.path.expanduser(base_path)
            return os.path.join(expanded_base_path, "text/models/tts")

    return os.path.join(AIRUNNER_BASE_PATH, "text/models/tts")


def resolve_tts_model_path(model_id: str) -> str:
    """Resolve one Melo model id to its local filesystem path."""
    return os.path.join(resolve_tts_model_root(), model_id)
