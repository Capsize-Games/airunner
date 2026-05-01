"""Tests for incremental conversation updates."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.chat.gui.widgets import conversation_widget as module
from airunner.components.chat.gui.widgets.conversation_widget import (
    ConversationWidget,
)


def test_append_user_message_for_request_uses_incremental_bridge_update():
    """User messages append without rebuilding the full conversation."""
    widget = SimpleNamespace(
        _rendered_request_ids=set(),
        _streamed_messages=[],
        _conversation=None,
        user=SimpleNamespace(username="User"),
        _assign_message_ids=lambda messages: [
            {**message, "id": index}
            for index, message in enumerate(messages)
        ],
        _dispatch_chat_bridge_call=Mock(),
        _format_message_for_webview=lambda **kwargs: kwargs,
    )

    ConversationWidget.append_user_message_for_request(
        widget,
        "Hello",
        request_id="req-1",
    )

    widget._dispatch_chat_bridge_call.assert_called_once_with(
        "append_message",
        {
            "content": "Hello",
            "message_id": 0,
            "name": "User",
            "is_bot": False,
            "request_id": "req-1",
        },
    )


def test_tool_status_updates_include_request_id(monkeypatch):
    """Tool status bridge updates stay scoped to the active request."""
    update = Mock()
    conversation = SimpleNamespace(id=7, user_data={})
    widget = SimpleNamespace(
        logger=Mock(),
        conversation=conversation,
        _chat_bridge=SimpleNamespace(updateToolStatus=update),
    )

    monkeypatch.setattr(module.Conversation.objects, "update", Mock())

    ConversationWidget.on_tool_status_update(
        widget,
        {
            "tool_id": "tool_classification_req-1",
            "tool_name": "tool_analyzer",
            "query": "hello",
            "status": "completed",
            "details": "Selected: none",
            "conversation_id": 7,
            "request_id": "req-1",
            "timestamp": "2026-04-30T00:00:00",
        },
    )

    update.assert_called_once_with(
        "req-1",
        "tool_classification_req-1",
        "tool_analyzer",
        "hello",
        "completed",
        "Selected: none",
    )
    assert conversation.user_data["tool_statuses"][0]["request_id"] == "req-1"


def test_thinking_updates_include_request_id():
    """Thinking bridge updates stay scoped to the active request."""
    widget = SimpleNamespace(_dispatch_chat_bridge_call=Mock())

    ConversationWidget.on_thinking_update(
        widget,
        {
            "request_id": "req-2",
            "status": "streaming",
            "content": "plan",
        },
    )

    widget._dispatch_chat_bridge_call.assert_called_once_with(
        "updateThinkingStatus",
        "req-2",
        "streaming",
        "plan",
    )


def test_dispatch_chat_bridge_call_flushes_when_js_is_ready():
    """Bridge events queue until the conversation web view is ready."""
    bridge = SimpleNamespace(append_message=Mock())
    callbacks = []
    widget = SimpleNamespace(
        _js_ready=False,
        _chat_bridge=bridge,
        _pending_chat_bridge_calls=[],
        _chat_bridge_flush_pending=False,
        wait_for_js_ready=lambda callback: callbacks.append(callback),
    )
    widget._schedule_chat_bridge_flush = (
        lambda: ConversationWidget._schedule_chat_bridge_flush(widget)
    )
    widget._flush_pending_chat_bridge_calls = (
        lambda: ConversationWidget._flush_pending_chat_bridge_calls(widget)
    )

    ConversationWidget._dispatch_chat_bridge_call(
        widget,
        "append_message",
        {"content": "Hello"},
    )

    assert widget._pending_chat_bridge_calls == [
        ("append_message", ({"content": "Hello"},))
    ]
    assert len(callbacks) == 1

    widget._js_ready = True
    callbacks[0]()

    bridge.append_message.assert_called_once_with({"content": "Hello"})


def test_render_initial_template_primes_chat_bridge_readiness():
    """Initial template render starts the JS-ready handshake."""
    widget = SimpleNamespace(
        _template_rendered=False,
        logger=Mock(),
        render_template=Mock(),
        _schedule_chat_bridge_flush=Mock(),
    )

    ConversationWidget._render_initial_template(widget)

    widget.render_template.assert_called_once_with()
    widget._schedule_chat_bridge_flush.assert_called_once_with()