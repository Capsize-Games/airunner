"""Model and workflow readiness helpers for generation."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from airunner_services.contract_enums import ModelStatus, ModelType


def invalid_model_path_response(owner) -> Optional[Dict[str, Any]]:
    """Return an error payload when the configured model path is invalid."""
    try:
        current_path = owner._current_model_path
        configured_path = owner.model_path
    except ValueError as exc:
        owner.logger.error(
            "Cannot generate - model path validation failed: %s",
            exc,
        )
        error_message = str(exc)
        if "embedding model" in error_message.lower():
            return {
                "response": (
                    "Error: Invalid model configuration. The embedding model "
                    "is set as the main LLM. Please select a proper chat "
                    "model in Settings > LLM."
                ),
                "error": str(exc),
            }
        return {
            "response": (
                "Error: No LLM model configured. Please select a model in "
                "Settings > LLM."
            ),
            "error": str(exc),
        }
    _reload_model_if_path_mismatch(owner, current_path, configured_path)
    return None


def _reload_model_if_path_mismatch(
    owner,
    current_path: str,
    configured_path: str,
) -> None:
    """Reload the model when the loaded path differs from settings."""
    if current_path == configured_path:
        return
    owner.logger.warning(
        "Model path mismatch detected: current='%s' vs settings='%s'. "
        "Reloading model...",
        current_path,
        configured_path,
    )
    owner.unload()
    owner.load()


def ensure_workflow_manager_ready(owner) -> Optional[Dict[str, Any]]:
    """Return an error payload when generation cannot reach a workflow."""
    _try_load_workflow_manager(owner)
    if owner._workflow_manager:
        return None
    load_error = _load_failure_response(owner)
    if load_error:
        return load_error
    local_model_error = _local_model_readiness_response(owner)
    if local_model_error:
        return local_model_error
    owner.logger.error("Workflow manager is not initialized")
    return {"response": "Error: workflow unavailable"}


def _try_load_workflow_manager(owner) -> None:
    """Best-effort load of the workflow manager when supported."""
    if owner._workflow_manager or not hasattr(owner, "_load_workflow_manager"):
        return
    try:
        owner._load_workflow_manager()
    except Exception:
        pass


def _load_failure_response(owner) -> Optional[Dict[str, Any]]:
    """Return one payload for a recorded model-load failure."""
    model_status = getattr(owner, "model_status", {}).get(ModelType.LLM)
    last_load_error = str(getattr(owner, "_last_load_error", "") or "").strip()
    if model_status != ModelStatus.FAILED or not last_load_error:
        return None
    owner.logger.error(
        "Workflow manager unavailable because model load failed: %s",
        last_load_error,
    )
    return {
        "response": f"Error: {last_load_error}",
        "error": last_load_error,
    }


def _local_model_readiness_response(owner) -> Optional[Dict[str, Any]]:
    """Return one payload when the local model is not yet ready."""
    try:
        model_path = owner.model_path
    except Exception:
        model_path = None
    if not owner.llm_settings.use_local_llm or not model_path:
        return None
    model_name = _model_name(owner, model_path)
    model_ready = _ensure_local_model_loaded(owner, model_path)
    if owner._workflow_manager or model_ready:
        return None
    owner.logger.error(
        "Workflow manager unavailable because model is missing; download "
        "likely in progress"
    )
    return {
        "response": (
            f"Error: model '{model_name}' is not ready yet (download in "
            "progress). Please wait for the download to finish and try again."
        ),
        "retry_after_download": True,
    }


def _model_name(owner, model_path: str) -> str:
    """Return one display name for the configured model path."""
    try:
        return owner.model_name
    except Exception:
        return os.path.basename(model_path.rstrip("/")) or "(unknown)"


def _ensure_local_model_loaded(owner, model_path: str) -> bool:
    """Load the local model when the configured model files are present."""
    expected_gguf_path = _expected_gguf_path(owner)
    is_gguf = _is_gguf_selected(owner)
    model_ready = _model_ready(model_path, expected_gguf_path, is_gguf)
    if not model_ready or not hasattr(owner, "load"):
        return model_ready
    try:
        owner.load()
    except Exception:
        owner.logger.exception("Failed to load local model before generation")
    _try_load_workflow_manager(owner)
    return model_ready


def _expected_gguf_path(owner) -> Optional[str]:
    """Return the expected GGUF path when the owner exposes one."""
    try:
        if hasattr(owner, "_get_expected_gguf_path"):
            return owner._get_expected_gguf_path()
    except Exception:
        return None
    return None


def _is_gguf_selected(owner) -> bool:
    """Return whether the selected model configuration uses GGUF."""
    try:
        if hasattr(owner, "_is_gguf_quantization_selected"):
            return bool(owner._is_gguf_quantization_selected())
    except Exception:
        return False
    return False


def _model_ready(
    model_path: str,
    expected_gguf_path: Optional[str],
    is_gguf: bool,
) -> bool:
    """Return whether the configured local model files are present."""
    gguf_present = _gguf_present(model_path, expected_gguf_path, is_gguf)
    model_ready = os.path.exists(model_path)
    if expected_gguf_path:
        return gguf_present
    if is_gguf:
        return model_ready and gguf_present
    return model_ready


def _gguf_present(
    model_path: str,
    expected_gguf_path: Optional[str],
    is_gguf: bool,
) -> bool:
    """Return whether one GGUF payload exists for the configured model."""
    if expected_gguf_path:
        return os.path.exists(expected_gguf_path)
    if not is_gguf:
        return False
    try:
        if os.path.isdir(model_path):
            return any(
                name.lower().endswith(".gguf")
                for name in os.listdir(model_path)
            )
        return model_path.lower().endswith(".gguf") and os.path.exists(
            model_path
        )
    except Exception:
        return False
