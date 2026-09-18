"""Logical-path handlers for the ``/api/v1/events`` RPC socket (#2230).

Kept separate from :mod:`events` (the transport) so each file stays
small. Every handler answers one logical path in the UwUChat client's
vocabulary, backed by the desktop data layer — never a translation of
the wire format, which is shared verbatim with the web client.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import parse_qs, urlsplit

from airunner_services.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.conversation import Conversation

Handler = Callable[[str, Dict[str, Any]], Tuple[int, Any]]
_MESSAGE_DELETE = re.compile(
    r"^/api/v1/llm/chatbot/(?P<chatbot>\d+)/messages/(?P<index>\d+)$"
)
_CONVERSATION_ITEM = re.compile(
    r"^/api/v1/llm/conversations/(?P<conversation>\d+)$"
)


def _route(path: str) -> str:
    return urlsplit(path).path


def _query(path: str) -> Dict[str, List[str]]:
    return parse_qs(urlsplit(path).query)


def roster() -> List[Dict[str, Any]]:
    """Return the persisted chatbots as a client-shaped roster."""
    try:
        bot = Chatbot.objects.first()
    except Exception:
        bot = None
    if bot is None:
        return []
    return [
        {
            "id": int(getattr(bot, "id", 0) or 0),
            "name": str(getattr(bot, "name", "Chatbot")),
            "botname": str(getattr(bot, "botname", "Computer")),
            "is_system_bot": False,
        }
    ]


def bootstrap_payload() -> Dict[str, Any]:
    """Return the bootstrap body pushed on connect."""
    return {"chatbots": roster()}


def _raw_messages(conversation_id: int) -> List[Dict[str, Any]]:
    """Return one conversation's raw message list without formatting."""
    conversation = Conversation.objects.filter_by_first(id=conversation_id)
    value = getattr(conversation, "value", None) if conversation else None
    return list(value) if isinstance(value, list) else []


def _health(_path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    return 200, {"status": "ok"}


def _conversations(_path: str, body: Dict[str, Any]) -> Tuple[int, Any]:
    limit = int(body.get("limit", 50))
    rows = ConversationHistoryManager().list_conversations(limit=limit)
    return 200, {"conversations": rows}


def _create_conversation(_path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    session = ConversationHistoryManager().create_conversation()
    conversation_id = session.get("conversation_id")
    if conversation_id is None:
        return 500, {"detail": "could not create conversation"}
    return 200, {"conversation_id": int(conversation_id)}


def _delete_conversation(path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    match = _CONVERSATION_ITEM.match(_route(path))
    if match is None:
        return 404, {"detail": "bad conversation path"}
    deleted = ConversationHistoryManager().delete_conversation(
        int(match.group("conversation"))
    )
    if not deleted:
        return 404, {"detail": "no such conversation"}
    return 200, {"deleted": True}


def _chatbot_query(_path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    return 200, {"records": roster()}


def _thread(path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    limit = int((_query(path).get("limit") or [200])[0])
    messages = ConversationHistoryManager().load_conversation_history(
        max_messages=limit
    )
    return 200, {"messages": messages, "current_mood": {}}


def _chatbot_session(_path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    manager = ConversationHistoryManager()
    return 200, {
        "conversation_id": manager.get_most_recent_conversation_id(),
        "session_id": None,
    }


def _truncate(_path: str, body: Dict[str, Any]) -> Tuple[int, Any]:
    conversation_id = body.get("conversation_id")
    if conversation_id is None:
        return 400, {"detail": "conversation_id required"}
    keep = int(body.get("keep_count", 0))
    messages = _raw_messages(int(conversation_id))
    kept = messages[-keep:] if keep > 0 else []
    Conversation.objects.update(pk=int(conversation_id), value=kept)
    return 200, {"truncated": True, "kept": len(kept)}


def _previews(_path: str, body: Dict[str, Any]) -> Tuple[int, Any]:
    wanted = {int(i) for i in (body.get("chatbot_ids") or [])}
    previews: Dict[str, Any] = {}
    for row in ConversationHistoryManager().list_conversations(limit=0):
        chatbot_id = row.get("chatbot_id")
        if chatbot_id in wanted:
            previews[str(chatbot_id)] = {
                "preview": row.get("summary") or None,
                "updated_at": row.get("timestamp") or None,
            }
    return 200, {"previews": previews}


def _delete_message(path: str, _body: Dict[str, Any]) -> Tuple[int, Any]:
    match = _MESSAGE_DELETE.match(_route(path))
    if match is None:
        return 404, {"detail": "bad message path"}
    conversation_id = (
        ConversationHistoryManager().get_most_recent_conversation_id()
    )
    if conversation_id is None:
        return 404, {"detail": "no conversation"}
    messages = _raw_messages(int(conversation_id))
    index = int(match.group("index"))
    if 0 <= index < len(messages):
        del messages[index]
    Conversation.objects.update(pk=int(conversation_id), value=messages)
    return 200, {"kept": len(messages)}


EXACT: Dict[Tuple[str, str], Handler] = {
    ("GET", "/api/v1/health"): _health,
    ("GET", "/api/v1/llm/conversations"): _conversations,
    ("POST", "/api/v1/llm/conversations"): _create_conversation,
    ("GET", "/api/v1/llm/thread"): _thread,
    ("GET", "/api/v1/llm/chatbot-session"): _chatbot_session,
    ("POST", "/api/v1/llm/conversations/truncate"): _truncate,
    ("POST", "/api/v1/llm/conversations/previews"): _previews,
    ("POST", "/api/v1/settings/resources/Chatbot/query"): _chatbot_query,
}

PATTERNS: List[Tuple[str, "re.Pattern[str]", Handler]] = [
    ("DELETE", _MESSAGE_DELETE, _delete_message),
    ("DELETE", _CONVERSATION_ITEM, _delete_conversation),
]


def dispatch(method: str, path: str, body: Dict[str, Any]) -> Tuple[int, Any]:
    """Resolve one logical RPC path against the allowlist."""
    route = _route(path)
    handler = EXACT.get((method, route))
    if handler is not None:
        return handler(path, body)
    for verb, pattern, func in PATTERNS:
        if verb == method and pattern.match(route):
            return func(path, body)
    return 404, {"detail": f"unhandled rpc path: {method} {route}"}
