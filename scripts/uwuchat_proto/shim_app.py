"""Loopback shim daemon for the #2230 prototype.

Implements the two sockets the UwUChat client needs, in the client's
own frame shapes:

* ``/api/v1/events``      -- bootstrap push + ``rpc`` dispatch
* ``/api/v1/llm/stream``  -- ``chat`` in, streamed ``chunk`` out

Auth reuses the existing loopback-token convention: the token file at
``AIRUNNER_BASE_PATH/config/loopback_token`` is required as ``?token=``
or the ``x-airunner-token`` header. If no token file exists the socket
is allowed (standalone prototype run only).

No database, no model, no network egress. Replies are canned.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import protocol, shim_data

HERE = Path(__file__).resolve().parent
PAGE = HERE / "page" / "index.html"
QUERY_CHATBOT = "/api/v1/settings/resources/Chatbot/query"

app = FastAPI(title="uwuchat-proto-shim")


def _bundle_dir() -> Optional[Path]:
    """Return a built client bundle dir when PROTO_BUNDLE points at one."""
    raw = os.environ.get("PROTO_BUNDLE", "")
    if not raw:
        return None
    path = Path(raw)
    return path if (path / "index.html").is_file() else None


def required_token() -> str:
    """Return the configured loopback token, or '' when unset."""
    base = os.environ.get("AIRUNNER_BASE_PATH", "")
    if not base:
        return ""
    path = Path(base) / "config" / "loopback_token"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _authorized(ws: WebSocket) -> bool:
    """Mirror the desktop loopback-token check for one socket."""
    expected = required_token()
    if not expected:
        return True
    provided = ws.query_params.get("token") or ws.headers.get(
        "x-airunner-token", ""
    )
    return provided == expected


def _dispatch(method: str, path: str) -> Tuple[int, Dict[str, Any]]:
    """Resolve one logical RPC path to a prototype response."""
    route = path.split("?", 1)[0]
    if method == "GET" and route == "/api/v1/health":
        return 200, {"status": "ok"}
    if method == "GET" and route == "/api/v1/llm/conversations":
        return 200, {"conversations": shim_data.conversations()}
    if method == "GET" and route == "/api/v1/llm/thread":
        return 200, {
            "messages": shim_data.thread_messages(),
            "current_mood": shim_data.current_mood(),
        }
    if method == "POST" and route == QUERY_CHATBOT:
        return 200, {"records": [shim_data.CHATBOT]}
    return 404, {"detail": f"no prototype route: {method} {route}"}


@app.get("/")
async def index() -> FileResponse:
    """Serve the bundle index (or the prototype page) over loopback."""
    bundle = _bundle_dir()
    return FileResponse(bundle / "index.html" if bundle else PAGE)


@app.get("/assets/{asset_path:path}")
async def asset(asset_path: str) -> FileResponse:
    """Serve a built client bundle's assets over loopback."""
    bundle = _bundle_dir()
    if bundle is None:
        raise HTTPException(status_code=404, detail="no bundle")
    return FileResponse(bundle / "assets" / asset_path)


@app.websocket(protocol.EVENTS_PATH)
async def events(ws: WebSocket) -> None:
    """Bootstrap + RPC channel (UwUChat ``/api/v1/events``)."""
    if not _authorized(ws):
        await ws.close(code=1008)
        return
    await ws.accept()
    await ws.send_json(protocol.bootstrap(shim_data.bootstrap_payload()))
    while True:
        try:
            msg = await ws.receive_json()
        except WebSocketDisconnect:
            return
        except ValueError:
            continue
        await _handle_event(ws, msg)


async def _handle_event(ws: WebSocket, msg: Dict[str, Any]) -> None:
    """Answer one ``rpc`` frame with an ``rpc_response`` frame."""
    if msg.get("type") != "rpc":
        return
    status, body = _dispatch(
        str(msg.get("method", "")), str(msg.get("path", ""))
    )
    await ws.send_json(
        protocol.rpc_response(str(msg.get("id", "")), status, body)
    )


@app.websocket(protocol.STREAM_PATH)
async def stream(ws: WebSocket) -> None:
    """Chat token stream (UwUChat ``/api/v1/llm/stream``)."""
    if not _authorized(ws):
        await ws.close(code=1008)
        return
    await ws.accept()
    while True:
        try:
            msg = await ws.receive_json()
        except WebSocketDisconnect:
            return
        except ValueError:
            continue
        if msg.get("type") == "chat":
            await _emit_reply(ws)


async def _emit_reply(ws: WebSocket) -> None:
    """Stream the canned reply in the client's frame vocabulary."""
    await ws.send_json(protocol.mood("neutral", "\U0001f610", "(o_o)"))
    await ws.send_json(protocol.thinking("...", "started"))
    for token in shim_data.reply_tokens():
        await ws.send_json(protocol.chunk(token))
        await asyncio.sleep(0.05)
    await ws.send_json(protocol.thinking("", "stopped"))
    await ws.send_json(
        protocol.chunk("", done=True, call_chain_id="proto-1")
    )
