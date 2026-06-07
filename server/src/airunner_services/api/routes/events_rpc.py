"""RPC dispatch system for the unified WebSocket endpoint."""

from __future__ import annotations

import re
import threading
from typing import Any, Callable

from fastapi import WebSocket

# ── Supported event types ────────────────────────────────────────────────

EVENT_IMAGES = "images"
EVENT_LORAS = "loras"
EVENT_EMBEDDINGS = "embeddings"
EVENT_DOCUMENTS = "documents"
EVENT_MODEL_STATUS = "model_status"
EVENT_INDEX_PROGRESS = "index_progress"
EVENT_DOWNLOADS = "downloads"
EVENT_CIVITAI_THUMBNAIL = "civitai_thumbnail"

ALL_EVENTS = frozenset(
    {
        EVENT_IMAGES,
        EVENT_LORAS,
        EVENT_EMBEDDINGS,
        EVENT_DOCUMENTS,
        EVENT_MODEL_STATUS,
        EVENT_INDEX_PROGRESS,
        EVENT_DOWNLOADS,
        EVENT_CIVITAI_THUMBNAIL,
    }
)

# ── RPC dispatcher ───────────────────────────────────────────────────────

_rpc_routes: list[tuple[str, re.Pattern, list[str], Callable]] = []
_rpc_lock = threading.Lock()


def _path_to_regex(pattern: str) -> tuple[re.Pattern, list[str]]:
    """Convert a path pattern like ``/resources/{name}/singleton``
    to a compiled regex and list of parameter names."""
    param_names: list[str] = []
    parts: list[str] = []
    for segment in pattern.split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            name = segment[1:-1]
            param_names.append(name)
            parts.append(r"([^/]+)")
        else:
            parts.append(re.escape(segment))
    regex_str = "^" + "/".join(parts) + "$"
    return re.compile(regex_str), param_names


def _rpc_register(
    method: str,
    path: str,
) -> Callable:
    """Decorator that registers a handler for a (method, path) pair."""
    pattern, param_names = _path_to_regex(path)

    def decorator(func: Callable) -> Callable:
        with _rpc_lock:
            _rpc_routes.append((method.upper(), pattern, param_names, func))
        return func

    return decorator


async def _dispatch_rpc(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    websocket: WebSocket,
) -> dict[str, Any]:
    """Dispatch an RPC message to the registered handler."""
    clean_path = path.split("?")[0]
    handler_entry, path_params = _find_rpc_handler(method.upper(), clean_path)
    if handler_entry is None:
        return {
            "status": 404,
            "body": {"error": f"Not found: {method} {path}"},
        }
    try:
        kw: dict[str, Any] = {"body": body or {}, "ws": websocket}
        if path_params:
            kw["path_params"] = path_params
        result = await handler_entry(**kw)
        return result
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception(
            "RPC handler error: %s %s", method, path
        )
        return {"status": 500, "body": {"error": str(exc)}}


def _find_rpc_handler(
    method_upper: str,
    clean_path: str,
) -> tuple[Callable | None, dict[str, str]]:
    """Find the matching RPC handler for a method and path."""
    with _rpc_lock:
        for rpc_method, pattern, param_names, func in _rpc_routes:
            if rpc_method == method_upper:
                match = pattern.match(clean_path)
                if match:
                    return func, dict(zip(param_names, match.groups()))
    return None, {}


@_rpc_register("GET", "/health")
@_rpc_register("GET", "/api/v1/health")
async def _rpc_health(body: dict, **kwargs: Any) -> dict[str, Any]:
    """Return server health status."""
    return {
        "status": 200,
        "body": {"status": "healthy", "service": "airunner"},
    }
