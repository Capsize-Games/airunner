"""Wire-frame helpers for the #2230 desktop chat prototype.

These mirror the *real* UwUChat client frames, taken from
``airunnerweb``:

* ``client/src/features/api/WsApiClient.ts`` — ``/api/v1/events``
  carries ``rpc`` / ``rpc_response`` / ``bootstrap`` / ``subscribe``.
* ``client/src/features/llm/useLLMWebSocket.ts`` and
  ``wsMessageHandler.ts`` — ``/api/v1/llm/stream`` carries ``chat``
  in, and ``chunk`` / ``thinking`` / ``mood`` / ``tool_status`` /
  ``error`` out.

This module builds the server-side frames only. It contains no
transport and no UI, so it can be reused by the phase-3 daemon work.
"""

from __future__ import annotations

from typing import Any, Dict

EVENTS_PATH = "/api/v1/events"
STREAM_PATH = "/api/v1/llm/stream"


def bootstrap(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build the server-pushed bootstrap frame.

    The client reads the roster from ``body.chatbots`` (see
    ``waitForBootstrap`` in ``WsApiClient.ts``).
    """
    return {"type": "bootstrap", "body": payload}


def rpc_response(
    request_id: str,
    status: int,
    body: Any,
) -> Dict[str, Any]:
    """Build one ``rpc_response`` frame for the events socket."""
    return {
        "type": "rpc_response",
        "id": request_id,
        "status": status,
        "body": body,
    }


def chunk(
    content: str,
    done: bool = False,
    call_chain_id: str | None = None,
) -> Dict[str, Any]:
    """Build one streamed ``chunk`` frame."""
    frame: Dict[str, Any] = {"type": "chunk", "content": content}
    if done:
        frame["done"] = True
        if call_chain_id is not None:
            frame["call_chain_id"] = call_chain_id
    return frame


def thinking(content: str, status: str) -> Dict[str, Any]:
    """Build one ``thinking`` frame (``status`` is ``started``/``stopped``)."""
    return {"type": "thinking", "content": content, "status": status}


def mood(mood_name: str, emoji: str, kaomoji: str) -> Dict[str, Any]:
    """Build one ``mood`` frame."""
    return {
        "type": "mood",
        "mood": mood_name,
        "emoji": emoji,
        "kaomoji": kaomoji,
    }
