from airunner.enums import ImageGenerator
from airunner.components.application.workers.model_scanner.model_scanner_constants import (
    VERSION_TO_CATEGORY,
    SUPPORTED_ZIMAGE_VERSIONS,
)

def get_category_for_version(version: str) -> str:
    """Get the ImageGenerator category for a given version name.

    Args:
        version: The version folder name (e.g., 'Z-Image Turbo', 'SDXL 1.0')

    Returns:
        The category string (e.g., 'zimage', 'stablediffusion').
        Defaults to 'stablediffusion' for unknown versions.
    """
    return VERSION_TO_CATEGORY.get(version, ImageGenerator.STABLEDIFFUSION.value)


def is_supported_model_version(version: str) -> bool:
    """Return whether one scanned art version is still supported."""
    if version.startswith("Z-Image"):
        return version in SUPPORTED_ZIMAGE_VERSIONS
    return True