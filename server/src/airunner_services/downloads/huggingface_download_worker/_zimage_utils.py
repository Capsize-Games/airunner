"""Z-Image file pruning utilities."""

import logging
from pathlib import Path

from airunner_services.art.managers.zimage.native.checkpoint_scanner import (
    find_active_checkpoint as _find_active_checkpoint,
)


def find_active_checkpoint(output_dir: Path):
    """Find the active Z-Image checkpoint in the output directory."""
    return _find_active_checkpoint(output_dir)


def get_active_zimage_load_mode(checkpoint) -> str:
    """Get the active Z-Image load mode from a checkpoint."""
    return str(getattr(checkpoint, "load_mode", "fp16") or "fp16")


def get_downloadable_files_for_mode(checkpoint, load_mode: str) -> list[str]:
    """Get the list of downloadable files for a given load mode."""
    try:
        groups = getattr(checkpoint, "file_groups", {}) or {}
        return list(groups.get(load_mode, []))
    except Exception:
        return []


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
