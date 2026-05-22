"""Tests for incremental conversation updates."""

from types import SimpleNamespace
from unittest.mock import Mock, call

from airunner.components.chat.gui.widgets import conversation_widget as module
from airunner.components.chat.gui.widgets.conversation_widget import (
    ConversationWidget,
)
from airunner.components.llm.managers.llm_response import LLMResponse


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


def test_add_message_to_conversation_preserves_leading_space(monkeypatch):
    """Visible chat rendering should not trim the message body."""
    captured = {}

    def capture_strip_names(message, *_args):
        captured["message"] = message
        return message

    monkeypatch.setattr(module, "strip_names_from_message", capture_strip_names)

    widget = SimpleNamespace(
        user=SimpleNamespace(username="User"),
        chatbot=SimpleNamespace(botname="Assistant"),
        conversation=None,
        conversation_id=1,
        _streamed_messages=[],
        logger=Mock(),
        _dispatch_chat_bridge_call=Mock(),
        _format_message_for_webview=lambda **kwargs: kwargs,
    )

    ConversationWidget.add_message_to_conversation(
        widget,
        name="Assistant",
        message=" Hello",
        is_bot=True,
        first_message=True,
    )

    assert captured["message"] == " Hello"


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
        "",
    )
    assert conversation.user_data["tool_statuses"][0]["request_id"] == "req-1"


def test_tool_status_updates_forward_metadata_json(monkeypatch):
    """Tool status bridge updates should forward debug metadata to JS."""
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
            "tool_id": "tool-2",
            "tool_name": "rag_search",
            "query": "what is this about",
            "status": "completed",
            "details": "example.com",
            "conversation_id": 7,
            "request_id": "req-2",
            "metadata": {
                "title": "Request Settings",
                "settings": {"max_new_tokens": 500},
            },
            "timestamp": "2026-04-30T00:00:00",
        },
    )

    update.assert_called_once_with(
        "req-2",
        "tool-2",
        "rag_search",
        "what is this about",
        "completed",
        "example.com",
        '{"title": "Request Settings", "settings": {"max_new_tokens": 500}}',
    )
    assert conversation.user_data["tool_statuses"][0]["metadata"] == {
        "title": "Request Settings",
        "settings": {"max_new_tokens": 500},
    }


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
        "",
    )


def test_thinking_updates_forward_metadata_json():
    """Thinking bridge updates should forward debug metadata to JS."""
    widget = SimpleNamespace(_dispatch_chat_bridge_call=Mock())

    ConversationWidget.on_thinking_update(
        widget,
        {
            "request_id": "req-3",
            "status": "completed",
            "content": "done",
            "metadata": {
                "stage": "document_synthesis",
                "settings": {"max_new_tokens": 1024},
            },
        },
    )

    widget._dispatch_chat_bridge_call.assert_called_once_with(
        "updateThinkingStatus",
        "req-3",
        "completed",
        "done",
        '{"stage": "document_synthesis", "settings": {"max_new_tokens": 1024}}',
    )


def test_set_conversation_preserves_thinking_metadata():
    """Reloaded assistant messages should keep thinking metadata for JS."""
    set_messages = Mock()
    widget = SimpleNamespace(
        _clear_conversation_widgets=Mock(),
        _pending_chat_bridge_calls=[],
        _chat_bridge=SimpleNamespace(set_messages=set_messages),
        _conversation_id=None,
        _conversation=None,
        logger=Mock(),
        wait_for_js_ready=lambda callback: callback(),
    )

    ConversationWidget.set_conversation(
        widget,
        [
            {
                "id": 5,
                "name": "Assistant",
                "is_bot": True,
                "content": "Hello!",
                "thinking_content": "Plan first.",
                "thinking_metadata": {
                    "stage": "document_verification",
                    "settings": {"max_new_tokens": 1024},
                },
            }
        ],
    )

    sent_messages = set_messages.call_args.args[0]
    assert sent_messages[0]["thinking_metadata"]["stage"] == (
        "document_verification"
    )


def test_model_loading_updates_include_request_id():
    """Model-loading bridge updates stay scoped to the active request."""
    widget = SimpleNamespace(_dispatch_chat_bridge_call=Mock())

    ConversationWidget.show_model_loading_status(
        widget,
        "req-4",
        "Loading model",
    )
    ConversationWidget.clear_model_loading_status(widget, "req-4")

    assert widget._dispatch_chat_bridge_call.call_args_list == [
        call(
            "updateModelLoadStatus",
            "req-4",
            "started",
            "Loading model",
        ),
        call(
            "updateModelLoadStatus",
            "req-4",
            "completed",
            "",
        ),
    ]


def test_process_sequential_tokens_updates_message_with_request_id(
    monkeypatch,
):
    """Incremental assistant updates should target the active request."""
    dispatch = Mock()
    monkeypatch.setattr(
        module.FormatterExtended,
        "format_content",
        Mock(return_value={"content": "Hello world", "type": "plaintext"}),
    )
    widget = SimpleNamespace(
        _expected_sequence=1,
        _sequence_buffer={
            1: LLMResponse(
                message=" world",
                sequence_number=1,
                request_id="req-3",
            )
        },
        _current_stream_tokens=["Hello"],
        _streamed_messages=[
            {
                "id": 0,
                "name": "Assistant",
                "content": "Hello",
                "role": "assistant",
                "is_bot": True,
                "request_id": "req-3",
            }
        ],
        _active_stream_message_index=0,
        _conversation=None,
        _assign_message_ids=lambda messages: messages,
        _dispatch_chat_bridge_call=dispatch,
    )

    ConversationWidget._process_sequential_tokens(widget)

    dispatch.assert_called_once_with(
        "update_last_message_content",
        "req-3",
        "Hello world",
        "plaintext",
    )
    assert widget._streamed_messages[0]["content"] == "Hello world"


def test_process_sequential_tokens_concatenates_normalized_markdown_chunks(
    monkeypatch,
):
    """Streaming updates should trust upstream-normalized markdown chunks."""
    dispatch = Mock()
    monkeypatch.setattr(
        module.FormatterExtended,
        "format_content",
        Mock(side_effect=lambda content: {"content": content, "type": "markdown"}),
    )
    widget = SimpleNamespace(
        _expected_sequence=1,
        _sequence_buffer={
            1: LLMResponse(
                message=" to",
                sequence_number=1,
                request_id="req-4",
            ),
            2: LLMResponse(
                message=" *The",
                sequence_number=2,
                request_id="req-4",
            ),
            3: LLMResponse(
                message=" Satanic",
                sequence_number=3,
                request_id="req-4",
            ),
            4: LLMResponse(
                message=" Bible*",
                sequence_number=4,
                request_id="req-4",
            ),
        },
        _current_stream_tokens=["According"],
        _streamed_messages=[
            {
                "id": 0,
                "name": "Assistant",
                "content": "According",
                "role": "assistant",
                "is_bot": True,
                "request_id": "req-4",
            }
        ],
        _active_stream_message_index=0,
        _conversation=None,
        _assign_message_ids=lambda messages: messages,
        _dispatch_chat_bridge_call=dispatch,
    )

    ConversationWidget._process_sequential_tokens(widget)

    dispatch.assert_called_once_with(
        "update_last_message_content",
        "req-4",
        "According to *The Satanic Bible*",
        "markdown",
    )
    assert widget._streamed_messages[0]["content"] == (
        "According to *The Satanic Bible*"
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


def test_conversation_asset_version_tracks_static_assets():
    """Conversation asset version should change with source asset mtimes."""
    asset_version = module.get_conversation_asset_version()

    assert asset_version.isdigit()
    assert int(asset_version) > 0