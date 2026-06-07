"""Service-owned facade for model download policy and coordination."""

from __future__ import annotations

from typing import Any

from airunner_services.downloads.civitai import (
    fetch_browser_model_info,
    fetch_model_info_for_url,
    search_models,
)
from airunner_services.downloads.civitai_download import (
    download_file as civitai_download_file,
)
from airunner_services.downloads.huggingface import (
    prepare_huggingface_download_request,
)
from airunner_services.downloads.policy import (
    is_civitai_allowed,
    is_huggingface_allowed,
)

_PROVIDER_CHECKS = {
    "civitai": is_civitai_allowed,
    "huggingface": is_huggingface_allowed,
}

_PROVIDER_LABELS = {
    "civitai": "CivitAI",
    "huggingface": "HuggingFace",
}


def is_provider_download_allowed(provider: str) -> bool:
    """Return whether one download provider is enabled by policy."""
    return _provider_check(provider)()


def provider_disabled_message(provider: str) -> str:
    """Return the shared GUI warning text for one disabled provider."""
    provider_name = _provider_label(provider)
    return (
        f"{provider_name} downloads are disabled in privacy settings.\n\n"
        "You can enable them in Preferences > Privacy & Security > "
        "External Services."
    )


def prepare_huggingface_download_payload(
    repo_id: str,
    model_type: str = "llm",
    output_dir: str | None = None,
    version: str | None = None,
    pipeline_action: str | None = None,
    missing_files: list[str] | None = None,
    gguf_filename: str | None = None,
    prefer_pre_quantized: bool = True,
) -> dict[str, Any]:
    """Return one normalized worker payload for HuggingFace downloads."""
    request = prepare_huggingface_download_request(
        repo_id=repo_id,
        model_type=model_type,
        output_dir=output_dir,
        version=version,
        pipeline_action=pipeline_action,
        missing_files=missing_files,
        gguf_filename=gguf_filename,
        prefer_pre_quantized=prefer_pre_quantized,
    )
    return request.as_payload()


def fetch_civitai_model_info(url: str, api_key: str = "") -> dict[str, Any]:
    """Return one selected-version-aware CivitAI metadata payload."""
    return fetch_model_info_for_url(url, api_key)


def search_civitai_models(
    query: str = "",
    *,
    base_models: list[str] | None = None,
    model_types: list[str] | None = None,
    limit: int = 20,
    cursor: str | None = None,
    api_key: str = "",
) -> dict[str, Any]:
    """Return one filtered CivitAI model-search payload."""
    return search_models(
        query,
        base_models=base_models,
        model_types=model_types,
        limit=limit,
        cursor=cursor,
        api_key=api_key,
    )


def fetch_civitai_browser_model_info(
    model_id: str,
    *,
    base_models: list[str] | None = None,
    model_types: list[str] | None = None,
    api_key: str = "",
) -> dict[str, Any]:
    """Return one filtered CivitAI model payload for the browser."""
    return fetch_browser_model_info(
        model_id,
        base_models=base_models,
        model_types=model_types,
        api_key=api_key,
    )


def download_civitai_file(*args: Any, **kwargs: Any) -> bool:
    """Download one CivitAI file using the shared service implementation."""
    return civitai_download_file(*args, **kwargs)


def _provider_check(provider: str):
    """Return the policy checker for one known provider."""
    provider_key = provider.lower()
    if provider_key not in _PROVIDER_CHECKS:
        raise ValueError(f"Unsupported download provider: {provider}")
    return _PROVIDER_CHECKS[provider_key]


def _provider_label(provider: str) -> str:
    """Return the display label for one known download provider."""
    provider_key = provider.lower()
    if provider_key not in _PROVIDER_LABELS:
        raise ValueError(f"Unsupported download provider: {provider}")
    return _PROVIDER_LABELS[provider_key]
