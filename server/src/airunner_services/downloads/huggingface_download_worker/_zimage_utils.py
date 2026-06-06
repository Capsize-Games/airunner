"""Z-Image file pruning utilities.

Delegates to ``zimage_bundle_requirements`` for checkpoint scanning
and mode detection.  The import is deferred so that the download
worker package can be loaded without the art runtime available.
"""

import logging
from pathlib import Path


def find_active_checkpoint(model_path: Path):
    """Find the active Z-Image checkpoint in *model_path*."""
    from airunner_services.art.managers.zimage.zimage_bundle_requirements import (  # noqa: E501
        find_active_checkpoint as _find,
    )

    return _find(model_path)


def get_active_zimage_load_mode(model_path: Path) -> str:
    """Get the active Z-Image load mode for *model_path*."""
    from airunner_services.art.managers.zimage.zimage_bundle_requirements import (  # noqa: E501
        get_active_zimage_load_mode as _mode,
    )

    return _mode(model_path)


def get_downloadable_files_for_mode(
    model_path: Path,
    mode: str | None = None,
) -> list[str]:
    """Get the list of downloadable files for a given load mode."""
    from airunner_services.art.managers.zimage.zimage_bundle_requirements import (  # noqa: E501
        get_downloadable_files_for_mode as _files,
    )

    return _files(model_path, mode)


def prune_zimage_bootstrap_files(
    output_dir: Path,
    bootstrap_files: dict | None,
    logger: logging.Logger,
) -> dict | None:
    """Return a lean bootstrap subset when an FP8 checkpoint already exists."""
    if not bootstrap_files:
        return bootstrap_files
    checkpoint = find_active_checkpoint(output_dir)
    if checkpoint is None:
        return bootstrap_files
    load_mode = get_active_zimage_load_mode(checkpoint)
    downloadable = set(get_downloadable_files_for_mode(checkpoint, load_mode))
    pruned = {
        filename: size
        for filename, size in bootstrap_files.items()
        if filename in downloadable
    }
    logger.info(
        "Pruned Z-Image bootstrap file set for %s from %d files to %d files",
        load_mode,
        len(bootstrap_files),
        len(pruned),
    )
    return pruned


def prune_zimage_missing_files(
    output_dir: Path,
    missing_files: list | None,
    logger: logging.Logger,
) -> list | None:
    """Drop Z-Image missing files that are not needed for the active load mode."""
    if not missing_files:
        return missing_files
    checkpoint = find_active_checkpoint(output_dir)
    if checkpoint is None:
        return missing_files
    load_mode = get_active_zimage_load_mode(checkpoint)
    downloadable = set(get_downloadable_files_for_mode(checkpoint, load_mode))
    pruned = [
        file_name for file_name in missing_files if file_name in downloadable
    ]
    dropped = sorted(set(missing_files) - set(pruned))
    if dropped:
        logger.info(
            "Dropped %d unneeded Z-Image download files for %s: %s",
            len(dropped),
            load_mode,
            dropped,
        )
    return pruned
