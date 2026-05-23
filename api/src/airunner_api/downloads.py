"""Transitional API-facing download helpers for GUI callers."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "DownloadJobService": (
        "airunner_services.downloads.job_service",
        "DownloadJobService",
    ),
    "JobState": (
        "airunner_services.utils.job_tracker",
        "JobState",
    ),
    "JobStatus": (
        "airunner_services.utils.job_tracker",
        "JobStatus",
    ),
    "ServiceDownloadWorker": (
        "airunner_services.downloads.service_download_worker",
        "ServiceDownloadWorker",
    ),
    "download_civitai_file": (
        "airunner_services.downloads.service",
        "download_civitai_file",
    ),
    "fetch_civitai_model_info": (
        "airunner_services.downloads.service",
        "fetch_civitai_model_info",
    ),
    "is_provider_download_allowed": (
        "airunner_services.downloads.service",
        "is_provider_download_allowed",
    ),
    "prepare_huggingface_download_payload": (
        "airunner_services.downloads.service",
        "prepare_huggingface_download_payload",
    ),
    "provider_disabled_message": (
        "airunner_services.downloads.service",
        "provider_disabled_message",
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve one API-facing download helper lazily from services."""
    if name not in _EXPORTS:
        raise AttributeError(name)
    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return module attributes for interactive callers and tooling."""
    return sorted(set(globals()) | set(_EXPORTS))


__all__ = sorted(_EXPORTS)