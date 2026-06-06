"""RPC handlers: art images."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image as PILImage

from airunner_services.api.routes.events import _rpc_register
from airunner_services.settings import AIRUNNER_BASE_PATH


@_rpc_register("GET", "/api/v1/art/images/dates")
async def _rpc_images_dates(body: dict, **kw: Any) -> dict[str, Any]:
    """List image date directories."""
    root = Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images"
    dates: list[dict[str, str]] = []
    if root.is_dir():
        for d in sorted(root.iterdir(), reverse=True):
            if d.is_dir() and d.name.isdigit() and len(d.name) == 8:
                label = f"{d.name[:4]}-{d.name[4:6]}-{d.name[6:8]}"
                dates.append({"value": d.name, "label": label})
    return {"status": 200, "body": {"dates": dates}}


@_rpc_register("GET", "/api/v1/art/images/{date}")
async def _rpc_images_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List images for a date."""
    from airunner_services.api.routes.images import (
        _list_image_files,
        _extract_metadata,
    )

    pp: dict = kw.get("path_params", {})
    date = pp.get("date", "")
    if not date.isdigit() or len(date) != 8:
        return {"status": 422, "body": {"error": "Invalid date"}}
    root = Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date
    if not root.is_dir():
        return {"status": 200, "body": {"total": 0, "images": []}}
    files = _list_image_files(root)
    offset = int(body.get("offset", 0))
    limit_val = int(body.get("limit", 20))
    page = files[offset : offset + limit_val]
    images = []
    for p in page:
        meta = _extract_metadata(p) if p.suffix.lower() == ".png" else None
        try:
            st = p.stat()
            fsize, ftm = st.st_size, st.st_mtime
        except OSError:
            fsize, ftm = 0, 0.0
        images.append(
            {
                "id": p.name,
                "file_path": str(p),
                "file_size": fsize,
                "file_timestamp": ftm,
                "metadata": meta,
                "image_url": f"/api/v1/art/images/{date}/full/{p.name}",
                "thumbnail_url": f"/api/v1/art/images/{date}/thumb/{p.name}",
            }
        )
    return {"status": 200, "body": {"total": len(files), "images": images}}


@_rpc_register("GET", "/api/v1/art/images/{date}/info/{filename}")
async def _rpc_images_info(body: dict, **kw: Any) -> dict[str, Any]:
    """Get image info."""
    from airunner_services.api.routes.images import _extract_metadata

    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    meta = (
        _extract_metadata(source) if source.suffix.lower() == ".png" else None
    )
    try:
        fsize = source.stat().st_size
    except OSError:
        fsize = 0
    return {
        "status": 200,
        "body": {
            "id": source.name,
            "file_path": str(source),
            "file_size": fsize,
            "metadata": meta,
            "image_url": f"/api/v1/art/images/{date}/full/{source.name}",
            "thumbnail_url": f"/api/v1/art/images/{date}/thumb/{source.name}",
        },
    }


@_rpc_register("DELETE", "/api/v1/art/images/{date}/delete/{filename}")
async def _rpc_images_delete(body: dict, **kw: Any) -> dict[str, Any]:
    """Delete an image."""
    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        source.unlink()
        return {"status": 200, "body": {"success": True, "deleted": filename}}
    except OSError as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/art/images/{date}/full/{filename}")
async def _rpc_images_full(body: dict, **kw: Any) -> dict[str, Any]:
    """Serve full image as binary."""
    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        data = source.read_bytes()
        return {
            "status": 200,
            "binary": True,
            "headers": {"Content-Type": "image/png"},
            "body": data,
        }
    except OSError as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/art/images/{date}/thumb/{filename}")
async def _rpc_images_thumb(body: dict, **kw: Any) -> dict[str, Any]:
    """Serve thumbnail as binary."""
    pp: dict = kw.get("path_params", {})
    date, filename = pp.get("date", ""), pp.get("filename", "")
    source = (
        Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images" / date / filename
    )
    if not source.is_file():
        return {"status": 404, "body": {"error": "Not found"}}
    try:
        img = PILImage.open(source)
        img.thumbnail((200, 200))
        buf = BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        return {
            "status": 200,
            "binary": True,
            "headers": {"Content-Type": "image/png"},
            "body": data,
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}
