"""Thumbnail fetching, resizing, caching, and base64-embedding helpers
for CivitAI model images."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import requests
from PIL import Image

logger = logging.getLogger(__name__)

# Thumbnail size for search result cards (40px).
_THUMB_SIZE = 40


def _civitai_cache_dir() -> Path:
    """Return the CivitAI thumbnail cache directory, creating it if needed."""
    base = Path(
        os.environ.get(
            "AIRUNNER_BASE_PATH",
            Path.home() / ".local" / "share" / "airunner",
        ),
    )
    cache_dir = base / "cache" / "civitai"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _check_cache(image_url: str, size: int) -> tuple[bytes, str] | None:
    """Return ``(cached_data, content_type)`` or ``None`` if not cached."""
    cache_dir = _civitai_cache_dir()
    key = hashlib.md5(f"{image_url}_{size}".encode()).hexdigest()
    path = cache_dir / key
    if not path.exists():
        return None
    ct = "image/png" if size > 0 else "image/jpeg"
    return path.read_bytes(), ct


def _download_and_resize(
    image_url: str,
    size: int,
) -> tuple[bytes, str]:
    """Download one CivitAI image, optionally resizing."""
    resp = requests.get(image_url, timeout=15)
    resp.raise_for_status()
    data = resp.content
    if size > 0:
        img = Image.open(BytesIO(data))
        img.thumbnail((size, size))
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    return data, resp.headers.get("content-type", "image/jpeg")


def _fetch_cached_image(
    image_url: str,
    size: int = 0,
) -> tuple[bytes, str]:
    """Download (or load from cache) one CivitAI image."""
    cached = _check_cache(image_url, size)
    if cached is not None:
        return cached
    data, ct = _download_and_resize(image_url, size)
    cache_dir = _civitai_cache_dir()
    key = hashlib.md5(f"{image_url}_{size}".encode()).hexdigest()
    (cache_dir / key).write_bytes(data)
    return data, ct


def _fetch_thumbnail_b64(image_url: str) -> str:
    """Download, resize to ``_THUMB_SIZE``, cache, and return base64."""
    img_data, _ct = _fetch_cached_image(image_url, _THUMB_SIZE)
    return base64.b64encode(img_data).decode("ascii")


def embed_search_thumbnails(items: List[Dict[str, Any]]) -> None:
    """Attach inline base64 ``thumbnails.small`` to each search item.

    Mutates ``items`` in-place.  Items without a version image are
    left untouched.
    """
    for item in items:
        versions = item.get("modelVersions") or []
        if not versions:
            continue
        images = versions[0].get("images") or []
        if not images:
            continue
        url = str(
            images[0].get("url") or images[0].get("thumbnailUrl") or "",
        )
        if not url:
            continue
        try:
            item["thumbnails"] = {"small": _fetch_thumbnail_b64(url)}
        except Exception:
            logger.warning("Failed to fetch thumbnail: %s", url[:80])


def embed_version_thumbnails(model_info: Dict[str, Any]) -> None:
    """Attach inline base64 ``images_base64.small`` to each version image
    in a model detail payload.

    Mutates ``model_info`` in-place.
    """
    for version in model_info.get("modelVersions") or []:
        for img in version.get("images") or []:
            url = str(img.get("url") or img.get("thumbnailUrl") or "")
            if not url:
                continue
            try:
                b64 = _fetch_thumbnail_b64(url)
                base64_map = img.get("images_base64") or {}
                base64_map["small"] = b64
                img["images_base64"] = base64_map
            except Exception:
                logger.warning(
                    "Failed to fetch version thumbnail: %s",
                    url[:80],
                )
