"""Serve drawing pad images as raw PNG."""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image

from airunner_services.database.models.drawingpad_settings import (
    DrawingPadSettings,
)
from airunner_services.database.session import session_scope

logger = logging.getLogger(__name__)

router = APIRouter()

RAW_MAGIC = b"AIRAW1"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _raw_to_png(raw_bytes: bytes) -> Optional[bytes]:
    """Decode AIRAW1 proprietary format into PNG bytes."""
    if not raw_bytes.startswith(RAW_MAGIC) or len(raw_bytes) < 14:
        return None
    try:
        w = int.from_bytes(raw_bytes[6:10], "big")
        h = int.from_bytes(raw_bytes[10:14], "big")
        rgba = raw_bytes[14:]
        if len(rgba) != w * h * 4:
            return None
        img = Image.frombuffer("RGBA", (w, h), rgba, "raw", "RGBA", 0, 1)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _maybe_base64_decode(data: bytes) -> Optional[bytes]:
    """If data looks like base64 text, decode it."""
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return None
    # Quick heuristic: valid base64 chars only
    if not all(
        c.isalnum() or c in "+/=\n\r" for c in text[:128]
    ):
        return None
    try:
        decoded = base64.b64decode(text, validate=True)
        if len(decoded) == 0:
            return None
        return decoded
    except Exception:
        return None


def _extract_png(data: bytes) -> Optional[bytes]:
    """Extract valid PNG bytes from stored data.

    Handles three storage formats:
    1. Raw PNG bytes (starts with \\x89PNG)
    2. Base64-encoded PNG (from daemon API serialization)
    3. AIRAW1 proprietary raw format (from brush strokes)
    """
    if not data:
        return None

    # Already raw PNG
    if data.startswith(PNG_MAGIC):
        # Validate it's a complete PNG with IEND
        if b"IEND" in data:
            return data
        # Try to open and re-encode to fix truncated PNGs
        try:
            img = Image.open(io.BytesIO(data))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            pass

    # AIRAW1 proprietary format
    png = _raw_to_png(data)
    if png is not None:
        return png

    # Base64-encoded PNG (most common: daemon API serialization path)
    decoded = _maybe_base64_decode(data)
    if decoded is not None:
        if decoded.startswith(PNG_MAGIC):
            return decoded
        png = _raw_to_png(decoded)
        if png is not None:
            return png

    return None


@router.get("/image")
async def canvas_image():
    """Return the most recent drawing pad image as raw PNG."""
    with session_scope() as session:
        records = (
            session.query(DrawingPadSettings)
            .order_by(DrawingPadSettings.id.desc())
            .limit(10)
            .all()
        )
        for record in records:
            raw = getattr(record, "image", None)
            if raw is None:
                continue

            data = raw if isinstance(raw, bytes) else bytes(raw)
            if len(data) == 0:
                continue

            png = _extract_png(data)
            if png is not None and len(png) > 0:
                logger.debug(
                    "canvas_image: serving %d-byte PNG (source was %d bytes)",
                    len(png),
                    len(data),
                )
                return Response(content=png, media_type="image/png")

    return Response(status_code=404)
