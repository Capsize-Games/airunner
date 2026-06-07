"""Thumbnail fetching, resizing, caching, and base64-embedding helpers
for CivitAI model images."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import requests
from PIL import Image

logger = logging.getLogger(__name__)

_THUMB_SIZE = 40

# CivitAI sometimes returns video URLs for animated previews — skip them.
_VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi")


def _is_video_url(url: str) -> bool:
    """Return ``True`` when *url* looks like a video file."""
    clean = url.lower().rstrip(")").split("?")[0]
    return clean.endswith(_VIDEO_EXTENSIONS)


def _is_nsfw(img: dict) -> bool:
    """Return ``True`` if the image is marked as hard NSFW (civitai.red)."""
    nsfw = str(img.get("nsfw", "")).upper()
    return nsfw == "X" or nsfw == "EXPLICIT"


def _first_image_url(images: list) -> str:
    """Return the URL of the first non-video, non-NSFW image."""
    for img in images:
        url = str(img.get("url") or img.get("thumbnailUrl") or "")
        if url and not _is_video_url(url) and not _is_nsfw(img):
            return url
    return ""


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


def _check_cache(image_url, size):
    cache_dir = _civitai_cache_dir()
    key = hashlib.md5(f"{image_url}_{size}".encode()).hexdigest()
    path = cache_dir / key
    if not path.exists():
        logger.info("CACHE MISS image=%s size=%d", image_url[:80], size)
        return None
    logger.info("CACHE HIT  image=%s size=%d", image_url[:80], size)
    ct = "image/png" if size > 0 else "image/jpeg"
    return path.read_bytes(), ct


def _headers():
    return {
        "User-Agent": "AIRunner/1.0",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }


def _do_fetch(image_url, timeout=15):
    """Fetch with retry-on-reset.  Pre-checks the URL extension
    to skip obvious video URLs, and falls back to streaming a small
    HEAD to check the content-type when the extension is ambiguous."""
    # Skip obvious video URLs by extension
    clean = image_url.lower().rstrip(")").split("?")[0]
    is_video = clean.endswith((".mp4", ".webm", ".mov", ".avi"))
    if is_video:
        logger.info("SKIP video url=%s", image_url[:80])
        raise ValueError("Not an image URL (video)")
    last_exc = None
    for attempt in range(2):
        try:
            return requests.get(
                image_url,
                headers=_headers(),
                timeout=timeout,
            )
        except (requests.exceptions.ConnectionError, OSError) as exc:
            last_exc = exc
            logger.warning(
                "RETRY url=%s attempt=%d: %s",
                image_url[:80],
                attempt,
                exc,
            )
    raise last_exc  # type: ignore[arg-type]


def _download_and_resize(image_url, size):
    logger.info("FETCH url=%s size=%d", image_url[:80], size)
    resp = _do_fetch(image_url)
    resp.raise_for_status()
    data = resp.content
    if size > 0:
        img = Image.open(BytesIO(data))
        img.thumbnail((size, size))
        buf = BytesIO()
        img.save(buf, format="PNG")
        logger.info(
            "RESIZE url=%s size=%d original=%d -> %d",
            image_url[:80],
            size,
            len(data),
            buf.tell(),
        )
        return buf.getvalue(), "image/png"
    return data, resp.headers.get("content-type", "image/jpeg")


def _fetch_cached_image(image_url, size=0):
    cached = _check_cache(image_url, size)
    if cached is not None:
        return cached
    data, ct = _download_and_resize(image_url, size)
    cache_dir = _civitai_cache_dir()
    key = hashlib.md5(f"{image_url}_{size}".encode()).hexdigest()
    (cache_dir / key).write_bytes(data)
    return data, ct


_MAX_WORKERS = 4


def _fetch_thumbnail_b64(image_url: str) -> str:
    logger.info("THUMBNAIL requested url=%s", image_url[:80])
    img_data, _ct = _fetch_cached_image(image_url, _THUMB_SIZE)
    return base64.b64encode(img_data).decode("ascii")


def _embed_one_search_thumbnail(item: dict) -> None:
    versions = item.get("modelVersions") or []
    if not versions:
        return
    url = _first_image_url(versions[0].get("images") or [])
    if not url:
        return
    try:
        item["thumbnails"] = {"small": _fetch_thumbnail_b64(url)}
    except Exception:
        logger.warning("Failed to fetch thumbnail: %s", url[:80])


def embed_search_thumbnails(items: List[Dict[str, Any]]) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        list(ex.map(_embed_one_search_thumbnail, items))


def _embed_one_version_image(args: tuple) -> None:
    """Embed thumbnails on a single version image.  *args* is
    ``(img, is_first_version)``."""
    img, is_first_version = args
    url = str(img.get("url") or img.get("thumbnailUrl") or "")
    if not url or _is_video_url(url) or _is_nsfw(img):
        return
    base64_map = img.get("images_base64") or {}
    try:
        base64_map["small"] = _fetch_thumbnail_b64(url)
    except Exception:
        logger.warning("Failed to fetch version thumbnail: %s", url[:80])
    if is_first_version:
        try:
            full_data, _ = _fetch_cached_image(url, 500)
            base64_map["full"] = base64.b64encode(full_data).decode("ascii")
        except Exception:
            logger.warning("Failed to fetch full preview: %s", url[:80])
    img["images_base64"] = base64_map


def embed_version_thumbnails(model_info: Dict[str, Any]) -> None:
    """Embed thumbnails on the first version's images only (sync, blocks).
    Other versions are loaded on demand via version-thumbnails RPC."""
    versions = model_info.get("modelVersions") or []
    if not versions:
        return
    tasks = [(img, True) for img in versions[0].get("images") or []]
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        list(ex.map(_embed_one_version_image, tasks))


def embed_single_version(
    model_info: Dict[str, Any],
    version_index: int,
) -> None:
    """Embed thumbnails on one specific version's images.
    Used when the user switches versions in the modal."""
    versions = model_info.get("modelVersions") or []
    if version_index < 0 or version_index >= len(versions):
        return
    tasks = [
        (img, True) for img in versions[version_index].get("images") or []
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        list(ex.map(_embed_one_version_image, tasks))


def embed_single_version_streaming(
    model_info: Dict[str, Any],
    version_index: int,
    on_image_done,
    cancel_event=None,
) -> None:
    """Process version images concurrently, calling on_image_done as each completes.

    If cancel_event (threading.Event) is set, stops fetching and broadcasting.
    """
    versions = model_info.get("modelVersions") or []
    if version_index < 0 or version_index >= len(versions):
        return
    images = versions[version_index].get("images") or []
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        futures = {
            ex.submit(_embed_one_version_image, (img, True)): img
            for img in images
        }
        for future in concurrent.futures.as_completed(futures):
            if cancel_event is not None and cancel_event.is_set():
                for f in futures:
                    f.cancel()
                logger.info(
                    "embed_single_version_streaming: cancelled (v%d)",
                    version_index,
                )
                break
            img = futures[future]
            try:
                future.result()
            except Exception as exc:
                logger.warning("Failed to embed version image: %s", exc)
            on_image_done(img)
