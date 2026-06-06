"""Thumbnail-streaming helpers for CivitAI RPC handlers.

Provides cancel-event infrastructure and thumbnail-streaming functions
that run thumbnail fetches in background threads and broadcast results
over the WebSocket event bus.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading

from airunner_services.api.routes.events_bus import WsEventBus
from airunner_services.api.routes.events_rpc import EVENT_CIVITAI_THUMBNAIL
from airunner_services.downloads.civitai_thumbnails import (
    _fetch_thumbnail_b64,
    _first_image_url,
    embed_single_version_streaming,
)

logger = logging.getLogger("airunner_services.api.routes.rpc_downloads")

# Per-model cancel events.  Set the event to stop an in-progress thumbnail
# stream for that model_id.  Keyed by int model_id.
_thumbnail_cancel_events: dict[int, threading.Event] = {}
_thumbnail_cancel_lock = threading.Lock()


def _acquire_cancel_event(model_id: int) -> threading.Event:
    """Create (or replace) a cancel event for model_id.

    Cancels any previously registered stream for the same model
    before returning.
    """
    event = threading.Event()
    with _thumbnail_cancel_lock:
        old = _thumbnail_cancel_events.get(model_id)
        if old:
            old.set()
        _thumbnail_cancel_events[model_id] = event
    return event


def _release_cancel_event(model_id: int, event: threading.Event) -> None:
    """Remove the cancel event if it still belongs to this stream."""
    with _thumbnail_cancel_lock:
        if _thumbnail_cancel_events.get(model_id) is event:
            _thumbnail_cancel_events.pop(model_id, None)


def _stream_one_thumbnail(item: dict) -> None:
    """Fetch and broadcast a thumbnail for one search result."""
    dl_logger = logger
    bus = WsEventBus()
    versions = item.get("modelVersions") or []
    if not versions:
        return
    url = _first_image_url(versions[0].get("images") or [])
    if not url:
        return
    model_id = item.get("id")
    try:
        b64 = _fetch_thumbnail_b64(url)
    except Exception as exc:
        dl_logger.warning(
            "STREAM model=%s FAILED: %s",
            model_id,
            exc,
        )
        return
    dl_logger.info("STREAM model=%s OK", model_id)
    bus.broadcast(
        EVENT_CIVITAI_THUMBNAIL,
        {"model_id": model_id, "thumbnails": {"small": b64}},
    )


def _stream_thumbnails_sync(items: list) -> None:
    """Synchronous thumbnail streaming with concurrent fetches."""
    dl_logger = logger
    total = len(items)
    dl_logger.info("STREAM starting: %d items (concurrent)", total)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(_stream_one_thumbnail, items))
    dl_logger.info("STREAM finished: %d items", total)


def _stream_one_version_sync(
    model_data: dict,
    version_index: int,
    cancel_event: threading.Event | None = None,
) -> None:
    """Embed thumbnails on one version's images, broadcasting each."""
    model_id = model_data.get("id")
    bus = WsEventBus()

    def _on_image_done(img: dict) -> None:
        if cancel_event is not None and cancel_event.is_set():
            return
        url = str(img.get("url") or img.get("thumbnailUrl") or "")
        b64 = img.get("images_base64") or {}
        if url and b64:
            bus.broadcast(
                EVENT_CIVITAI_THUMBNAIL,
                {
                    "model_id": model_id,
                    "version_index": version_index,
                    "image_url": url,
                    "images_base64": b64,
                },
            )

    embed_single_version_streaming(
        model_data,
        version_index,
        _on_image_done,
        cancel_event,
    )


async def _stream_one_version_bg(
    model_data: dict,
    version_index: int,
) -> None:
    """Run ``_stream_one_version_sync`` in a thread with cancel support."""
    model_id = int(model_data.get("id") or 0)
    cancel_event = _acquire_cancel_event(model_id)
    try:
        await asyncio.to_thread(
            _stream_one_version_sync,
            model_data,
            version_index,
            cancel_event,
        )
    finally:
        _release_cancel_event(model_id, cancel_event)


def _stream_version_thumbnails_sync(
    model_data: dict,
    cancel_event: threading.Event | None = None,
) -> None:
    """Embed thumbnails for the initial version (index 0)."""
    _stream_one_version_sync(model_data, 0, cancel_event)


async def _stream_version_thumbnails_bg(model_data: dict) -> None:
    """Run ``_stream_version_thumbnails_sync`` in a thread with cancel."""
    model_id = int(model_data.get("id") or 0)
    cancel_event = _acquire_cancel_event(model_id)
    try:
        await asyncio.to_thread(
            _stream_version_thumbnails_sync,
            model_data,
            cancel_event,
        )
    finally:
        _release_cancel_event(model_id, cancel_event)


async def _stream_civitai_thumbnails(items: list) -> None:
    """Run thumbnail streaming in a thread to avoid blocking the event loop."""
    await asyncio.to_thread(_stream_thumbnails_sync, items)
