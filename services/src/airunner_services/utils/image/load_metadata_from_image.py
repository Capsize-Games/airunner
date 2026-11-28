from typing import Any, Dict


def load_metadata_from_image(image: Any) -> Dict[str, Any]:
    """Return one image's metadata dict, or empty when absent."""
    if image:
        return image.info
    return {}
