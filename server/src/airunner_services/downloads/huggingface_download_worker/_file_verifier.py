"""File existence and completeness verification for model downloads.

Provides helpers to check whether a previously-downloaded file is
complete (or suspiciously small) and to safely remove incomplete files
before re-downloading.
"""

import logging
from pathlib import Path


def check_existing_file(
    path: Path,
    expected_size: int,
    logger: logging.Logger,
) -> bool:
    """Check whether the file at *path* exists and appears complete.

    Returns ``True`` when the file is usable as-is.  Returns ``False``
    when the file is missing, incomplete (actual < *expected_size*), or
    suspiciously small when no expected size is known.

    When ``False`` is returned the caller should remove the file and
    re-download it.
    """
    if not path.exists():
        return False

    actual_size = path.stat().st_size

    if expected_size > 0 and actual_size < expected_size:
        logger.warning(
            "File %s is incomplete: %d bytes vs expected %d bytes. "
            "Will re-download.",
            path.name, actual_size, expected_size,
        )
        return False

    if expected_size == 0 and actual_size < 1024:
        logger.warning(
            "File %s exists but is very small (%d bytes) with unknown "
            "expected size. Assuming incomplete and re-downloading.",
            path.name, actual_size,
        )
        return False

    logger.debug(
        "File %s exists (%d bytes), skipping",
        path.name, actual_size,
    )
    return True


def remove_file(path: Path, logger: logging.Logger) -> bool:
    """Remove a file at *path*. Returns ``True`` on success."""
    try:
        path.unlink()
        return True
    except Exception as exc:
        logger.error(
            "Failed to delete file %s: %s", path.name, exc,
        )
        return False


def should_skip_transformer_weights(
    filename: str,
    missing_files: list | None,
) -> bool:
    """Determine whether *filename* should be skipped for GGUF models.

    Transformer diffusion weights are not needed when a GGUF checkpoint
    is in use, unless the file was explicitly requested via
    *missing_files*.
    """
    if missing_files is not None:
        return False
    return (
        "transformer/diffusion_pytorch_model" in filename
        and filename.endswith(".safetensors")
    )
