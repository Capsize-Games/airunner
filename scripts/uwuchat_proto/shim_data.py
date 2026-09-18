"""Deterministic stub data for the #2230 prototype.

This prototype deliberately touches **no** database and **no** model.
All roster/thread/reply content is canned so the run is safe and
reproducible. The point being demonstrated is the transport contract
(QtWebEngine -> loopback -> events RPC + stream socket), not inference.

Phase 3 replaces every function here with the real desktop daemon
adapters described in the #2230 design note.
"""

from __future__ import annotations

from typing import Any, Dict, List

CHATBOT: Dict[str, Any] = {
    "id": 1,
    "name": "Prototype UwU",
    "botname": "Prototype",
    "is_system_bot": False,
    "deleted": False,
}


def bootstrap_payload() -> Dict[str, Any]:
    """Return the bootstrap body pushed on events-socket connect."""
    return {"chatbots": [CHATBOT], "settings": {}, "immersions": []}


def thread_messages() -> List[Dict[str, Any]]:
    """Return a canned thread for ``GET /api/v1/llm/thread``."""
    return [
        {"id": 1, "role": "user", "content": "Hello from earlier."},
        {"id": 2, "role": "assistant", "content": "Hi! (canned thread)"},
    ]


def current_mood() -> Dict[str, str]:
    """Return a canned mood block."""
    return {
        "mood": "neutral",
        "emoji": "\U0001f610",
        "kaomoji": "(\u3057\u25d5\u25b5\u25d5\u3057)",
    }


def reply_tokens() -> List[str]:
    """Return the canned reply as token-sized pieces."""
    return [
        "This ",
        "reply ",
        "is ",
        "streamed ",
        "from ",
        "the ",
        "prototype ",
        "daemon ",
        "over ",
        "the ",
        "/api/v1/llm/stream ",
        "socket, ",
        "then ",
        "rendered ",
        "inside ",
        "QtWebEngine.",
    ]


def conversations() -> List[Dict[str, Any]]:
    """Return a canned conversation list."""
    return [{"id": 1, "title": "Prototype conversation"}]
