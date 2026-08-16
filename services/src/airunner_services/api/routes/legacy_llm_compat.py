"""Shared LLM readiness helpers for the versioned compatibility routes.

The retired ``BaseHTTPRequestHandler`` server owned a set of private
``_ensure_llm_model_loaded`` / ``_is_llm_model_loaded`` helpers that the
Ollama and OpenAI compatibility handlers relied on.  This module re-homes
that logic against the FastAPI app state so the compatibility surfaces can
keep working without importing the deleted legacy server.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional, Tuple

from fastapi import HTTPException, Request

from airunner_services.contract_enums import ModelStatus, ModelType, SignalCode
from airunner_services.preload_settings_store import LLMPreloadSettingsStore
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_MODEL_LOAD_TIMEOUT_SECONDS = 120.0


def get_airunner_app(req: Request) -> Any:
    """Return the AIRunner app or raise when it is unavailable."""
    app = getattr(req.app.state, "airunner_app", None)
    if app is None:
        raise HTTPException(
            status_code=503, detail="AI Runner app not available"
        )
    return app


def _lifecycle_service(req: Request) -> Optional[Any]:
    """Return the lifecycle service attached to the FastAPI app state."""
    return getattr(req.app.state, "lifecycle_service", None)


def _loaded_from_lifecycle(lifecycle: Optional[Any]) -> bool:
    """Return True when the lifecycle service reports a loaded LLM."""
    if lifecycle is None:
        return False
    status_getter = getattr(lifecycle, "current_llm_model_status", None)
    if not callable(status_getter):
        return False
    try:
        current = status_getter()
    except Exception:
        return False
    return current in (ModelStatus.LOADED, ModelStatus.READY)


def _loaded_from_balancer(app: Any) -> bool:
    """Return True when the model-load balancer reports a loaded LLM."""
    balancer = getattr(app, "model_load_balancer", None)
    if balancer is None:
        balancer = getattr(app, "_model_load_balancer", None)
    if balancer is None:
        return False
    try:
        loaded_models = balancer.get_loaded_models() or []
    except Exception:
        return False
    return ModelType.LLM in loaded_models


def _loaded_from_worker(app: Any) -> bool:
    """Return True when the local worker already has an LLM ready."""
    worker_manager = getattr(app, "_worker_manager", None)
    if not worker_manager:
        return False

    worker = getattr(worker_manager, "_llm_generate_worker", None)
    if worker is None:
        worker = getattr(worker_manager, "llm_generate_worker", None)
    if worker is None:
        return False

    status_getter = getattr(worker, "current_model_status", None)
    if callable(status_getter):
        try:
            if status_getter() in (ModelStatus.LOADED, ModelStatus.READY):
                return True
        except Exception:
            pass

    manager = getattr(worker, "_model_manager", None)
    return bool(
        manager is not None and getattr(manager, "_chat_model", None) is not None
    )


def is_llm_model_loaded(
    app: Any, lifecycle: Optional[Any] = None
) -> bool:
    """Return True when any runtime state reports a loaded local LLM."""
    return _loaded_from_lifecycle(lifecycle) or _loaded_from_balancer(
        app
    ) or _loaded_from_worker(app)


def _validate_model_available() -> Tuple[bool, str]:
    """Return ``(is_valid, model_path_or_error)`` for the configured LLM."""
    try:
        model_path = LLMPreloadSettingsStore().resolve_model_path()
    except Exception as exc:
        logger.exception("Could not resolve LLM model path")
        return False, f"Could not resolve LLM model path: {exc}"

    if not model_path:
        return False, (
            "No model path configured. Please run 'airunner' (GUI) first "
            "to download and select a model."
        )
    if not os.path.exists(model_path):
        return False, (
            f"Model not found at '{model_path}'. The model needs to be "
            "downloaded."
        )
    return True, model_path


def ensure_llm_model_loaded(req: Request) -> Any:
    """Return the AIRunner app, loading the LLM model when necessary.

    Raises ``HTTPException`` with status 503 when no model is configured or
    the model cannot be loaded within the timeout.
    """
    app = get_airunner_app(req)
    lifecycle = _lifecycle_service(req)
    if is_llm_model_loaded(app, lifecycle=lifecycle):
        return app

    is_valid, model_path = _validate_model_available()
    if not is_valid:
        raise HTTPException(status_code=503, detail=model_path)

    logger.info("Auto-loading LLM model")
    app.emit_signal(SignalCode.LLM_LOAD_SIGNAL, {"model_path": model_path})

    start_time = time.time()
    while time.time() - start_time < _MODEL_LOAD_TIMEOUT_SECONDS:
        if is_llm_model_loaded(app, lifecycle=lifecycle):
            logger.info("LLM model loaded successfully")
            return app
        time.sleep(0.5)

    raise HTTPException(
        status_code=503,
        detail=(
            f"Model loading timed out after "
            f"{int(_MODEL_LOAD_TIMEOUT_SECONDS)} seconds."
        ),
    )
