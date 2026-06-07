"""RPC handler registrations for the unified /api/v1/events WebSocket.

Each function is decorated with ``@_rpc_register(method, path)`` which
registers it in the dispatch table.  The handler receives a ``body``
dict and returns a dict with ``status`` and ``body`` (and optionally
``headers``, ``binary``, ``error``).

These replace the existing FastAPI HTTP route functions — callers
(React client) now call ``rpcRequest()`` instead of ``fetch()``.
"""

from __future__ import annotations

import importlib
import logging
import re
from typing import Any

from airunner_services.api.routes.events import _rpc_register

logger = logging.getLogger(__name__)


def resource_store_table(resource_name: str):
    """Return the SQLAlchemy model class for a resource name."""
    snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", resource_name)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
    snake = snake.lower()
    module_path = f"airunner_services.database.models.{snake}"
    module = importlib.import_module(module_path)
    return getattr(module, resource_name)


# ── Health ────────────────────────────────────────────────────────────────


# ── Models (active + unload) ─────────────────────────────────────────────
# ── Conversations ────────────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/llm/conversations")
async def _rpc_conversations_list(body: dict, **kw: Any) -> dict[str, Any]:
    """List conversations."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        convs = manager.list_conversations(limit=int(body.get("limit", 50)))
        return {"status": 200, "body": {"conversations": convs}}
    except Exception:
        return {"status": 200, "body": {"conversations": []}}


@_rpc_register("POST", "/api/v1/llm/conversations")
async def _rpc_conversations_create(body: dict, **kw: Any) -> dict[str, Any]:
    """Create a new conversation."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        session = manager.create_conversation(
            max_messages=body.get("max_messages"),
        )
        return {"status": 200, "body": session}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("DELETE", "/api/v1/llm/conversations/{conv_id}")
async def _rpc_conversations_delete(body: dict, **kw: Any) -> dict[str, Any]:
    """Delete a conversation."""
    pp: dict = kw.get("path_params", {})
    raw_id = pp.get("conv_id", "")
    if not raw_id.isdigit():
        return {"status": 400, "body": {"error": "Invalid ID"}}
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        manager.delete_conversation(int(raw_id))
        return {"status": 200, "body": {"status": "deleted"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("GET", "/api/v1/llm/conversations/session")
async def _rpc_conversations_session(body: dict, **kw: Any) -> dict[str, Any]:
    """Get a conversation session."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        conv_id = body.get("conversation_id")
        session = manager.get_conversation_session(
            conversation_id=int(conv_id) if conv_id else None,
            max_messages=int(body.get("max_messages", 50)),
        )
        return {"status": 200, "body": session}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/llm/conversations/select")
async def _rpc_conversations_select(body: dict, **kw: Any) -> dict[str, Any]:
    """Select a conversation."""
    try:
        from airunner_services.conversations.conversation_history_manager import (
            ConversationHistoryManager,
        )

        manager = ConversationHistoryManager()
        conv_id = body.get("conversation_id")
        if conv_id:
            session = manager.get_conversation_session(
                conversation_id=int(conv_id),
            )
            return {"status": 200, "body": session}
        return {"status": 400, "body": {"error": "Missing conversation_id"}}
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


@_rpc_register("POST", "/api/v1/llm/conversations/truncate")
async def _rpc_conversations_truncate(body: dict, **kw: Any) -> dict[str, Any]:
    """Truncate a conversation to keep only the first N messages.

    Request body::

        {"conversation_id": 42, "keep_count": 3}

    This keeps messages[0:keep_count] and discards the rest.

    Operates on the raw ``value`` list stored on the Conversation model
    so that the ``is_bot`` / ``role`` fields are preserved correctly.
    """
    try:
        from airunner_services.database.models.conversation import (
            Conversation,
        )

        conv_id = body.get("conversation_id")
        keep_count = int(body.get("keep_count", 0))
        if not conv_id or keep_count < 0:
            return {
                "status": 400,
                "body": {
                    "error": "conversation_id and keep_count are required",
                },
            }

        conversation = Conversation.objects.filter_by_first(id=int(conv_id))
        if conversation is None:
            return {
                "status": 404,
                "body": {"error": f"Conversation {conv_id} not found"},
            }

        raw = list(getattr(conversation, "value", None) or [])
        truncated = raw[:keep_count]
        Conversation.objects.update(pk=int(conv_id), value=list(truncated))
        return {
            "status": 200,
            "body": {
                "truncated": True,
                "kept": keep_count,
                "original_count": len(raw),
            },
        }
    except Exception as exc:
        return {"status": 500, "body": {"error": str(exc)}}


# ── LLM settings presets ─────────────────────────────────────────────────


@_rpc_register("GET", "/api/v1/llm/settings-presets")
async def _rpc_llm_presets(body: dict, **kw: Any) -> dict[str, Any]:
    """List LLM settings presets."""
    try:
        from airunner_services.api.routes.llm_settings_presets import (
            load_presets,
        )

        presets = load_presets()
        return {"status": 200, "body": {"presets": presets}}
    except Exception:
        return {"status": 200, "body": {"presets": []}}
