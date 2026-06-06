"""Image-loading helpers for vision generation inputs."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Optional
from urllib.request import Request, urlopen

from PIL import Image as PILImage


def image_from_data_url(path_str: str) -> PILImage.Image:
    """Decode one `data:image` URL into a PIL image."""
    try:
        base64_data = path_str.split(",", 1)[1]
    except IndexError:
        base64_data = path_str
    image_bytes = base64.b64decode(base64_data)
    return PILImage.open(io.BytesIO(image_bytes)).convert("RGB")


def image_from_remote_url(
    adapter: Any,
    path_str: str,
) -> Optional[PILImage.Image]:
    """Download and decode one remote image URL."""
    try:
        request = Request(path_str, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=10) as response:
            return PILImage.open(io.BytesIO(response.read())).convert("RGB")
    except Exception as error:
        adapter.logger.error("Failed to download image: %s", error)
        return None


def image_from_file(
    adapter: Any,
    path_str: str,
) -> Optional[PILImage.Image]:
    """Load one image from a local file path when it exists."""
    fs_path = Path(path_str).expanduser()
    if not fs_path.exists():
        return None
    try:
        return PILImage.open(fs_path).convert("RGB")
    except Exception as error:
        adapter.logger.error("Failed to open image file: %s", error)
        return None


def image_from_base64_string(path_str: str) -> Optional[PILImage.Image]:
    """Decode one raw base64 string into a PIL image when possible."""
    try:
        image_bytes = base64.b64decode(path_str)
        return PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return None
