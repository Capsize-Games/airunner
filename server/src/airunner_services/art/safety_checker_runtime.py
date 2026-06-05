"""Runtime access helpers for art safety-checker resources."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)


def get_loaded_safety_checker_worker(api: Any = None):
    """Return loaded safety resources from the service-owned art manager."""
    api_ref = api or peek_registered_api()
    worker_manager = getattr(api_ref, "_worker_manager", None)
    if worker_manager is None:
        return None

    worker = getattr(worker_manager, "_sd_worker", None)
    if worker is None:
        return None

    model_manager = getattr(worker, "model_manager", None)
    if model_manager is None:
        return None

    safety_checker = getattr(model_manager, "_safety_checker", None)
    feature_extractor = getattr(model_manager, "_feature_extractor", None)
    if safety_checker is None or feature_extractor is None:
        return None

    return SimpleNamespace(
        safety_checker=safety_checker,
        feature_extractor=feature_extractor,
    )


__all__ = ["get_loaded_safety_checker_worker"]
