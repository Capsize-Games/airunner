"""Bootstrap file resolution for HuggingFace model downloads.

Resolves which files to download based on model type, version, and
pipeline action, using the bootstrap manifest and HuggingFace API.
"""

import logging
from pathlib import Path
from typing import Any

from airunner_services.bootstrap.unified_model_files import (
    get_required_files_for_model,
)


def get_bootstrap_data_for_model(
    model_type: str,
    resolved_version: str | None,
    pipeline_action: str,
    repo_id: str,
    logger: logging.Logger,
) -> dict | list | None:
    """Fetch the full bootstrap data appropriate for *model_type*.

    Returns ``None`` when no bootstrap data is found.
    """
    if model_type in ("stt", "tts_openvoice"):
        data = get_required_files_for_model(model_type, repo_id)
        if data:
            logger.info(
                "Found bootstrap data for %s/%s with %d files",
                model_type,
                repo_id,
                len(data),
            )
        return data

    if model_type == "rmbg":
        data = get_required_files_for_model("rmbg", repo_id)
        if data:
            logger.info(
                "Found bootstrap data for rmbg/%s with %d files",
                repo_id,
                len(data),
            )
        return data

    if model_type == "art":
        if resolved_version is None:
            logger.error(
                "Cannot resolve bootstrap data for art model "
                "with version=None (repo=%s)",
                repo_id,
            )
            return None
        data = get_required_files_for_model(
            model_type,
            resolved_version,
            resolved_version,
            pipeline_action,
        )
        if data:
            logger.info(
                "Found bootstrap data for %s with %d files",
                resolved_version,
                len(data),
            )
        return data

    if model_type in ("llm", "gguf"):
        data = get_required_files_for_model("llm", repo_id)
        if data:
            logger.info(
                "Found bootstrap data for llm/%s with %d files",
                repo_id,
                len(data),
            )
        else:
            logger.warning(
                "No bootstrap data found for llm/%s - "
                "file sizes will be fetched from API",
                repo_id,
            )
        return data

    return None


def resolve_file_list_from_api(
    downloader: Any,
    repo_id: str,
    model_type: str,
    logger: logging.Logger,
    emit_signal_fn,
    signal_code,
    failed_signal,
) -> list[dict] | None:
    """Fetch the remote file list from the HuggingFace API.

    Returns a list of ``{"filename": …, "size": …}`` dicts, or ``None``
    on failure.
    """
    logger.info("Fetching file list from HuggingFace API for %s...", repo_id)
    emit_signal_fn(
        signal_code,
        {"message": "Fetching file list from HuggingFace..."},
    )
    try:
        all_files = downloader.get_model_files(repo_id)
        logger.info("Got %d files from HuggingFace API", len(all_files))
    except Exception as exc:
        logger.error("Failed to get file list: %s", exc)
        emit_signal_fn(failed_signal, {"error": str(exc)})
        return None

    required_files = downloader.REQUIRED_FILES.get(
        model_type, downloader.REQUIRED_FILES["llm"]
    )

    files_to_download = []
    for file_info in all_files:
        filename = file_info.get("path", "")
        size = file_info.get("size", 0)

        if file_info.get("type") == "directory":
            continue
        if filename in required_files:
            files_to_download.append({"filename": filename, "size": size})
            continue
        if filename == "consolidated.safetensors":
            continue
        if filename.endswith(
            (".safetensors", ".json", ".txt", ".model", ".jinja")
        ):
            files_to_download.append({"filename": filename, "size": size})

    return files_to_download


def resolve_bootstrap_files(
    model_type: str,
    full_bootstrap_data: Any,
    model_path: Path,
    missing_files: list | None,
    logger: logging.Logger,
) -> dict | None:
    """Convert bootstrap data into a ``{filename: size}`` dict.

    Handles art, STT/TTS, and RMBG model bootstrap formats, applying
    Z-Image pruning and missing-file filtering where applicable.
    """
    # When explicit missing_files are provided, look up sizes from
    # full bootstrap data.
    if missing_files is not None:
        result = _build_missing_files_dict(
            missing_files, full_bootstrap_data, logger
        )
        return result if result else None

    # Art models: use full bootstrap data directly.
    if model_type == "art":
        return _as_dict(full_bootstrap_data)

    # STT/TTS/RMBG: bootstrap is a list of filenames -> dict with size 0.
    if model_type in ("stt", "tts_openvoice", "rmbg"):
        if not full_bootstrap_data:
            return None
        return {f: 0 for f in full_bootstrap_data}

    return None


def _build_missing_files_dict(
    missing_files: list,
    full_bootstrap_data: Any,
    logger: logging.Logger,
) -> dict:
    """Map a list of missing filenames to expected sizes."""
    result = {}
    for f in missing_files:
        expected_size = 0
        if (
            full_bootstrap_data
            and isinstance(full_bootstrap_data, dict)
            and f in full_bootstrap_data
        ):
            expected_size = full_bootstrap_data[f]
            logger.info(
                "Missing file %s: expected size %d (from bootstrap)",
                f,
                expected_size,
            )
        else:
            logger.warning(
                "Missing file %s: no expected size found in bootstrap data",
                f,
            )
        result[f] = expected_size
    return result


def _as_dict(data: Any) -> dict | None:
    """Return *data* as a dict when it is truthy, otherwise ``None``."""
    if data:
        return dict(data) if not isinstance(data, dict) else data
    return None
