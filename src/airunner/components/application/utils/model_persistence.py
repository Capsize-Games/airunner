"""Utilities for persisting model metadata after download."""

import os
from typing import Any, Dict

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _extract_base_model_from_path(file_path: str) -> str:
    """Extract the base model directory name used as 'version' by scanners.

    Expected path contains .../art/models/<base_model>/<subfolder>/<file>.
    Returns <base_model> if present, else empty string.
    """
    try:
        norm = os.path.normpath(os.path.expanduser(file_path))
        parts = norm.split(os.sep)
        # Find 'art' then 'models' and take the next segment
        for i, p in enumerate(parts):
            if p == "art" and i + 2 < len(parts) and parts[i + 1] == "models":
                return parts[i + 2]
    except Exception:
        pass
    return ""


def persist_trigger_words(
    version_data: Dict[str, Any],
    model_type: str,
    file_info: Dict[str, Any],
    saved_file_path: str,
) -> None:
    """
    Extract and persist trigger words from CivitAI version data to the appropriate DB model.

    Args:
        version_data: The version object from CivitAI API containing trainedWords
        model_type: The model type (e.g., "LORA", "CHECKPOINT", "TEXTUAL EMBEDDING")
        file_info: File metadata from the version
        saved_file_path: Full path where the file was saved
    """
    try:
        # Extract trigger words from trainedWords field
        trained_words = version_data.get("trainedWords", [])
        if not trained_words:
            logger.debug(f"No trainedWords found for {saved_file_path}")
            return

        # Convert list to comma-separated string
        trigger_words_str = ", ".join(
            str(word).strip() for word in trained_words if str(word).strip()
        )
        if not trigger_words_str:
            logger.debug(
                f"No valid trigger words after processing for {saved_file_path}"
            )
            return

        logger.info(
            f"Persisting trigger words '{trigger_words_str}' for {saved_file_path}"
        )

        # Determine which model type to create/update based on model_type and file_info
        model_type_upper = (model_type or "").strip().upper()
        file_type = (file_info.get("type") or "").strip().upper()
        file_name = file_info.get("name", "").lower()

        if model_type_upper == "LORA":
            _persist_lora_trigger_words(
                saved_file_path,
                trigger_words_str,
                version_data,
            )
        elif (
            model_type_upper
            in ("TEXTUAL EMBEDDING", "EMBEDDING", "TEXTUALINVERSION")
            or file_type == "EMBEDDING"
            or file_name.endswith(".pt")
        ):
            _persist_embedding_trigger_words(
                saved_file_path,
                trigger_words_str,
                version_data,
            )
        else:
            _persist_model_trigger_words(
                saved_file_path,
                trigger_words_str,
                version_data,
            )

    except Exception as e:
        logger.error(
            f"Failed to persist trigger words for {saved_file_path}: {e}",
            exc_info=True,
        )


def _persist_lora_trigger_words(
    file_path: str, trigger_words: str, version_data: Dict[str, Any]
) -> None:
    """Persist trigger words for a LoRA model."""
    from airunner.models.lora import Lora

    file_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(file_name)[0]

    # Try to find existing LoRA by path or name
    existing_lora = Lora.objects.filter_by_first(path=file_path)
    if existing_lora is None:
        existing_lora = Lora.objects.filter_by_first(name=name_without_ext)

    version_str = _extract_base_model_from_path(file_path) or str(
        version_data.get("id", "")
    )

    if existing_lora:
        logger.debug(f"Updating existing LoRA: {existing_lora.name}")
        Lora.objects.update(
            existing_lora.id,
            trigger_word=trigger_words,
            path=file_path,
            version=version_str,
        )
    else:
        logger.debug(f"Creating new LoRA: {name_without_ext}")
        Lora.objects.create(
            name=name_without_ext,
            path=file_path,
            trigger_word=trigger_words,
            version=version_str,
            enabled=False,  # User can enable manually
            scale=0,
        )


def _persist_embedding_trigger_words(
    file_path: str, trigger_words: str, version_data: Dict[str, Any]
) -> None:
    """Persist trigger words for an embedding."""
    from airunner.models.embedding import Embedding

    file_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(file_name)[0]

    # Try to find existing embedding by path or name
    existing_embedding = Embedding.objects.filter_by_first(path=file_path)
    if existing_embedding is None:
        existing_embedding = Embedding.objects.filter_by_first(
            name=name_without_ext
        )

    version_str = _extract_base_model_from_path(file_path) or str(
        version_data.get("id", "")
    )

    if existing_embedding:
        logger.debug(f"Updating existing embedding: {existing_embedding.name}")
        Embedding.objects.update(
            existing_embedding.id,
            trigger_word=trigger_words,
            path=file_path,
            version=version_str,
        )
    else:
        logger.debug(f"Creating new embedding: {name_without_ext}")
        Embedding.objects.create(
            name=name_without_ext,
            path=file_path,
            trigger_word=trigger_words,
            version=version_str,
            active=False,  # User can activate manually
        )


def _persist_model_trigger_words(
    file_path: str, trigger_words: str, version_data: Dict[str, Any]
) -> None:
    """Persist trigger words for a checkpoint/model."""
    # Ensure both ends of the relationship are registered before using AIModels
    # to avoid SQLAlchemy registry resolution errors.
    from airunner.models.generator_settings import (
        GeneratorSettings,  # noqa: F401 - imported for side-effect
    )
    from airunner.models.ai_models import AIModels

    file_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(file_name)[0]

    # Try to find existing model by path or name
    existing_model = AIModels.objects.filter_by_first(path=file_path)
    if existing_model is None:
        existing_model = AIModels.objects.filter_by_first(
            name=name_without_ext
        )

    version_str = _extract_base_model_from_path(file_path) or str(
        version_data.get("id", "")
    )

    if existing_model:
        logger.debug(f"Updating existing model: {existing_model.name}")
        AIModels.objects.update(
            existing_model.id,
            trigger_words=trigger_words,
            path=file_path,
            version=version_str,
        )
    else:
        logger.debug(f"Creating new model: {name_without_ext}")
        AIModels.objects.create(
            name=name_without_ext,
            path=file_path,
            trigger_words=trigger_words,
            version=version_str,
            branch="main",  # Default branch
            category="downloaded",  # Mark as downloaded
            pipeline_action="txt2img",  # Default pipeline
            model_type="checkpoint",  # Default type
            enabled=False,  # User can enable manually
        )
