"""Internal helpers for FastAPI app setup — imported by server.py."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from airunner_services.runtimes.bootstrap import build_runtime_registry


def _attach_existing_registry(app: FastAPI, app_instance: Any) -> bool:
    """Attach an existing runtime registry if present. Returns True if done."""
    existing = (
        getattr(app_instance, "runtime_registry", None)
        if app_instance
        else None
    )
    if existing is not None:
        app.state.runtime_registry = existing
        return True
    return False


def _build_and_attach_registry(app: FastAPI, app_instance: Any) -> None:
    """Build and attach a new runtime registry."""
    from .server import logger, _resolve_runtime_registry

    try:
        app.state.runtime_registry = build_runtime_registry(
            app_instance=app_instance
        )
    except Exception:
        logger.exception("Failed to build runtime registry")
    if app_instance is None:
        app.state.runtime_registry = _resolve_runtime_registry(app_instance)
        return
    if app.state.runtime_registry is not None:
        try:
            setattr(
                app_instance, "runtime_registry", app.state.runtime_registry
            )
        except Exception:
            logger.debug("Unable to attach runtime registry to app instance")


def _setup_registry_and_lifecycle(app: FastAPI, app_instance: Any) -> None:
    """Attach runtime registry and lifecycle service to app state."""
    from .server import _resolve_lifecycle_service

    if not _attach_existing_registry(app, app_instance):
        _build_and_attach_registry(app, app_instance)
    if app_instance:
        app.state.airunner_app = app_instance
        app.state.lifecycle_service = _resolve_lifecycle_service(app_instance)


def _setup_signal_bridges(app_instance: Any) -> None:
    """Register index-progress and model-status bridges."""
    if app_instance is None:
        return
    from airunner_services.api.routes.knowledge_base_index import (
        _register_signal_handlers,
    )
    from airunner_services.api.routes.models_status import (
        _register_model_status_handlers,
    )

    _register_signal_handlers(app_instance)
    _register_model_status_handlers(app_instance)


def _register_watchers(app_instance: Any) -> None:
    """Start file-system watchers — images, loras, models."""
    if app_instance is None:
        return
    _start_all_watchers()


def _start_all_watchers() -> None:
    """Start each individual file-system watcher."""
    from airunner_services.api.routes.images import _start_watcher as _img
    from airunner_services.api.routes.lora_watch import _start_watcher as _lora
    from airunner_services.api.routes.embeddings_watch import (
        _start_watcher as _emb,
    )
    from airunner_services.api.routes.knowledge_base_watch import (
        _start_watcher as _kb,
    )
    from airunner_services.api.routes.models_watch import (
        _start_watcher as _mdl,
    )

    _img()
    _lora()
    _emb()
    _kb()
    _mdl()


def _mount_static_files(app: FastAPI) -> None:
    from .server import logger

    static_dir = (os.environ.get("AIRUNNER_STATIC_DIR") or "").strip()
    if not static_dir:
        return
    resolved = os.path.abspath(static_dir)
    if not os.path.isfile(os.path.join(resolved, "index.html")):
        logger.warning(
            "AIRUNNER_STATIC_DIR=%s does not contain index.html", resolved
        )
        return
    logger.info(
        "Bundle mode detected — serving React frontend from %s", resolved
    )
    app.mount("/", StaticFiles(directory=resolved, html=True), name="web")
