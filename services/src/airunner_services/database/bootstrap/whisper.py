"""Bootstrap identity for the service's whisper.cpp GGML model."""

from __future__ import annotations

import os
from dataclasses import dataclass

from airunner_services.model_management.model_registry import (
    ModelRegistry,
    ModelType,
)


class UnsupportedWhisperModelError(ValueError):
    """Raised when a requested STT artifact does not match whisper.cpp."""


@dataclass(frozen=True)
class WhisperCppModelSpec:
    """Pinned download identity for the registered whisper.cpp runtime."""

    repo_id: str
    filename: str
    revision: str
    sha256: str
    size_bytes: int


def get_registered_whisper_cpp_model_spec() -> WhisperCppModelSpec:
    models = ModelRegistry().list_models(model_type=ModelType.SPEECH_TO_TEXT)
    model = next(
        (
            item
            for item in models
            if item.runtime_backend == "whisper.cpp"
            and item.preferred_runtime_format == "ggml"
        ),
        None,
    )
    if model is None:
        raise RuntimeError("No whisper.cpp GGML model is registered")

    values = (
        model.preferred_download_repo_id,
        model.preferred_download_filename,
        model.preferred_download_revision,
        model.preferred_download_sha256,
        model.preferred_download_size_bytes,
    )
    if not all(values):
        raise RuntimeError("Registered whisper.cpp model is missing pinned artifact metadata")
    return WhisperCppModelSpec(
        repo_id=str(model.preferred_download_repo_id),
        filename=str(model.preferred_download_filename),
        revision=str(model.preferred_download_revision),
        sha256=str(model.preferred_download_sha256),
        size_bytes=int(model.preferred_download_size_bytes),
    )


def get_whisper_cpp_model_spec(
    repo_id: str | None = None,
    filenames: list[str] | None = None,
) -> WhisperCppModelSpec:
    """Resolve and validate one GGML request before any network activity.

    The old generic STT setting may name a Transformers/CTranslate2 model.
    That format cannot be loaded by the registered whisper.cpp sidecar, so
    an explicit incompatible override is rejected instead of being silently
    replaced with a different repository.
    """
    spec = get_registered_whisper_cpp_model_spec()
    configured_repo = os.environ.get("AIRUNNER_DEFAULT_STT_HF_PATH")
    configured_filename = os.environ.get("AIRUNNER_DEFAULT_STT_MODEL_FILENAME")

    if configured_repo and configured_repo != spec.repo_id:
        raise UnsupportedWhisperModelError(
            f"Configured STT repository {configured_repo!r} is not supported by the "
            f"whisper.cpp GGML runtime; expected {spec.repo_id!r}. "
            "Use a compatible local GGML model path or select a supported "
            "whisper.cpp artifact explicitly."
        )
    if repo_id and repo_id != spec.repo_id:
        raise UnsupportedWhisperModelError(
            f"STT repository {repo_id!r} is not supported by the "
            f"whisper.cpp GGML runtime; expected {spec.repo_id!r}. "
            "Use a compatible local GGML model path or select a supported "
            "whisper.cpp artifact explicitly."
        )
    if configured_filename and configured_filename != spec.filename:
        raise UnsupportedWhisperModelError(
            f"Configured STT filename {configured_filename!r} is not supported by the "
            f"registered whisper.cpp model; expected {spec.filename!r}."
        )
    if filenames:
        unsupported = sorted(set(filenames) - {spec.filename})
        if unsupported:
            raise UnsupportedWhisperModelError(
                "STT download requested files outside the pinned GGML model: "
                + ", ".join(unsupported)
            )
    return spec


_DEFAULT_SPEC = get_registered_whisper_cpp_model_spec()
WHISPER_FILES = {_DEFAULT_SPEC.repo_id: [_DEFAULT_SPEC.filename]}


__all__ = [
    "UnsupportedWhisperModelError",
    "WHISPER_FILES",
    "WhisperCppModelSpec",
    "get_registered_whisper_cpp_model_spec",
    "get_whisper_cpp_model_spec",
]
