"""Local model resolution for art generation requests.

A version-only request resolves to an installed checkpoint of that
version (issue #2229). A request naming a model that is not available
locally is rejected outright. Either way a bad request fails before
any side effect instead of occupying the worker until the timeout.
"""

from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from airunner_services.runtimes.file_policy import (
    PathPolicyError,
    normalize_local_path,
)

from .art_contracts import GenerationRequest
from .art_model_base import art_model_base_dir, generator_settings_record
from .art_model_scan import pipeline_action, version_model_path


def _request_text(value: Optional[str]) -> str:
    """Return one stripped request string, defaulting to empty."""
    return (value or "").strip()


def _validate_explicit_model(model: str) -> str:
    """Return one caller-provided model after a local existence check."""
    try:
        normalized = normalize_local_path(model, label="Art model")
    except PathPolicyError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    if not Path(normalized).exists():
        raise HTTPException(
            status_code=400,
            detail=f"Art model '{model}' is not available locally",
        )
    return model


def _resolve_version_checkpoint(version: str, pipeline: str) -> str:
    """Return one installed checkpoint for an art version."""
    action = pipeline or pipeline_action(generator_settings_record())
    resolved = version_model_path(art_model_base_dir(), version, action)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No installed checkpoint for art version '{version}'"
            ),
        )
    return resolved


def resolve_generation_model(request: GenerationRequest) -> Optional[str]:
    """Return the local model for one generation request.

    An explicit model must exist locally; a version with no model
    resolves to an installed checkpoint of that version. A request
    with neither keeps the existing server-default behavior (None).

    Raises:
        HTTPException: 400 when the model is not available locally,
            404 when the version has no installed checkpoint.
    """
    model = _request_text(request.model)
    if model:
        return _validate_explicit_model(model)
    version = _request_text(request.version)
    if version:
        return _resolve_version_checkpoint(
            version, _request_text(request.pipeline)
        )
    return None


__all__ = ["resolve_generation_model"]
