"""Bootstrap data service — fetches model/pipeline/settings metadata
from the daemon.  All data comes from ``GET /api/v1/art/bootstrap``.
"""

from __future__ import annotations

from typing import Any, Dict, List

_cache: dict[str, Any] | None = None


def _fetch_bootstrap() -> dict[str, Any]:
    """Query the daemon for bootstrap data."""
    from airunner.daemon_client.gui_daemon_client import (
        GuiDaemonClient,
    )

    client = GuiDaemonClient()
    return client.get_bootstrap_data()


def get_bootstrap_data() -> dict[str, Any]:
    """Return the cached bootstrap data, fetching on first access."""
    global _cache
    if _cache is None:
        _cache = _fetch_bootstrap()
    return _cache


def get_model_bootstrap_data() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("models", [])


def get_pipeline_bootstrap_data() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("pipelines", [])


def get_required_files_for_model(
    model_type: str,
    model_id: str,
    version: str | None = None,
    pipeline_action: str | None = None,
) -> dict[str, Any]:
    unified = get_bootstrap_data().get("unified_model_files", {})
    model_files = unified.get(model_type, {})
    if not isinstance(model_files, dict):
        return {}
    result = model_files.get(model_id)
    if result is not None:
        return result
    if version:
        result = model_files.get(f"{model_id}__{version}")
        if result is not None:
            return result
    if pipeline_action:
        result = model_files.get(f"{model_id}__{pipeline_action}")
        if result is not None:
            return result
    return {}


def get_controlnet_bootstrap_data() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("controlnet_bootstrap_data", [])


def get_espeak_settings_data() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("espeak_settings_data", [])


def get_llm_file_bootstrap_data() -> Dict[str, Any]:
    return get_bootstrap_data().get("llm_file_bootstrap_data", {})


def get_openvoice_files() -> Dict[str, Any]:
    return get_bootstrap_data().get("openvoice_files", {})


def get_openvoice_core_models() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("openvoice_core_models", [])


def get_openvoice_language_models() -> Dict[str, Any]:
    return get_bootstrap_data().get("openvoice_language_models", {})


def get_path_settings_data() -> List[dict[str, Any]]:
    return get_bootstrap_data().get("path_settings_data", [])


def get_rmbg_files() -> Dict[str, Any]:
    return get_bootstrap_data().get("rmbg_files", {})


def get_sd_file_bootstrap_data() -> Dict[str, Any]:
    return get_bootstrap_data().get("sd_file_bootstrap_data", {})


def get_whisper_files() -> Dict[str, Any]:
    return get_bootstrap_data().get("whisper_files", {})


__all__ = [
    "get_bootstrap_data",
    "get_controlnet_bootstrap_data",
    "get_espeak_settings_data",
    "get_llm_file_bootstrap_data",
    "get_model_bootstrap_data",
    "get_openvoice_core_models",
    "get_openvoice_files",
    "get_openvoice_language_models",
    "get_path_settings_data",
    "get_pipeline_bootstrap_data",
    "get_required_files_for_model",
    "get_rmbg_files",
    "get_sd_file_bootstrap_data",
    "get_whisper_files",
]
