"""Tests for chat prompt show-event startup helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt

from airunner.components.chat.gui.widgets import chat_prompt_widget as module
from airunner.components.chat.gui.widgets.chat_prompt_widget import (
    ChatPromptWidget,
)
from airunner.enums import LLMActionType


def test_chat_prompt_splitter_restore_is_deferred(monkeypatch):
    """The chat splitter restore is queued once after showEvent."""
    scheduled = []
    widget = SimpleNamespace(
        _default_splitter_settings_applied=False,
        _apply_default_splitter_settings=Mock(),
        isVisible=Mock(return_value=True),
    )

    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    ChatPromptWidget._schedule_default_splitter_settings(widget)
    ChatPromptWidget._schedule_default_splitter_settings(widget)

    assert widget._default_splitter_settings_applied is True
    assert scheduled == [(0, widget._apply_default_splitter_settings)]


def test_chat_prompt_splitter_restore_does_not_process_events(monkeypatch):
    """The splitter restore avoids re-entering Qt from showEvent."""
    process_events = Mock(side_effect=AssertionError("re-entered Qt"))
    logger = Mock()
    ui = Mock()
    widget = SimpleNamespace(
        load_splitter_settings=Mock(),
        logger=logger,
        ui=ui,
    )

    monkeypatch.setattr(module.QApplication, "processEvents", process_events)

    ChatPromptWidget._apply_default_splitter_settings(widget)

    widget.load_splitter_settings.assert_called_once_with(
        orientations={"chat_prompt_splitter": Qt.Orientation.Vertical},
        default_maximize_config={
            "chat_prompt_splitter": {
                "index_to_maximize": 0,
                "min_other_size": 50,
            }
        },
    )
    process_events.assert_not_called()


def test_do_generate_clears_and_renders_user_message_first(monkeypatch):
    """The prompt clears and the user bubble appears before load probes."""
    call_order = []
    scheduled = []

    def clear_prompt():
        call_order.append("clear")

    def append_user_message_for_request(prompt, request_id=None):
        call_order.append(("append", prompt, bool(request_id)))

    def get_loaded_models():
        call_order.append("probe")
        return []

    widget = SimpleNamespace(
        prompt="Hello",
        generating=False,
        held_message=None,
        action=LLMActionType.APPLICATION_COMMAND,
        ui=SimpleNamespace(
            prompt=SimpleNamespace(setPlainText=Mock()),
            conversation=SimpleNamespace(
                append_user_message_for_request=
                append_user_message_for_request,
            ),
        ),
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=get_loaded_models,
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(send_request=Mock()),
        ),
        clear_prompt=clear_prompt,
        _ensure_conversation_context=lambda: 1,
        start_progress_bar=Mock(),
        _parse_slash_command=lambda prompt: (None, prompt, None),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        logger=Mock(),
        enable_send_button=Mock(),
        disable_send_button=Mock(),
        on_stop_button_clicked=Mock(),
        _submit_generation_request=lambda **kwargs: call_order.append(
            ("submit", kwargs["actual_prompt"], kwargs["request_id"])
        ),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    monkeypatch.setattr(module.QApplication, "processEvents", Mock())
    monkeypatch.setattr(
        module.QTimer,
        "singleShot",
        lambda delay, callback: scheduled.append((delay, callback)),
    )

    ChatPromptWidget.do_generate(widget)

    assert call_order == [
        "clear",
        ("append", "Hello", True),
    ]
    assert scheduled and scheduled[0][0] == 0

    scheduled[0][1]()

    assert call_order[-1][0] == "submit"


def test_submit_generation_request_runs_probe_after_ui_append():
    """Heavy submit setup still runs, but outside the initial UI turn."""
    call_order = []

    def get_loaded_models():
        call_order.append("probe")
        return []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=get_loaded_models,
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(send_request=Mock()),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: True),
        ),
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        start_progress_bar=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _is_thinking_enabled_for_request=(
            lambda: ChatPromptWidget._is_thinking_enabled_for_request(widget)
        ),
        logger=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Hello",
        action=LLMActionType.APPLICATION_COMMAND,
        conversation_id=1,
        request_id="req-1",
        slash_command=None,
    )

    assert call_order == ["probe"]
    widget.api.llm.send_request.assert_called_once()
    assert (
        widget.api.llm.send_request.call_args.kwargs["llm_request"].enable_thinking
        is True
    )


def test_configure_prompt_shortcuts_preserves_native_keypress_event(
    monkeypatch,
):
    """Prompt typing stays on Qt's native path while shortcuts are added."""

    class FakeShortcut:
        def __init__(self, sequence, parent):
            self.sequence = sequence
            self.parent = parent
            self.enabled = True
            self.context = None
            self._handler = None
            self.activated = SimpleNamespace(connect=self._connect)

        def _connect(self, handler):
            self._handler = handler

        def setContext(self, context):
            self.context = context

        def setEnabled(self, enabled):
            self.enabled = enabled

    native_keypress = object()

    class DummyWidget:
        _create_prompt_shortcut = ChatPromptWidget._create_prompt_shortcut
        _configure_prompt_shortcuts = ChatPromptWidget._configure_prompt_shortcuts
        _set_slash_navigation_shortcuts_enabled = (
            ChatPromptWidget._set_slash_navigation_shortcuts_enabled
        )

        def __init__(self):
            self._prompt_shortcuts_configured = False
            self._prompt_submit_shortcuts = []
            self._slash_popup_shortcuts = []
            self.ui = SimpleNamespace(
                prompt=SimpleNamespace(keyPressEvent=native_keypress)
            )

        def _on_submit_shortcut(self):
            return None

        def _handle_slash_popup_navigation(self, _key):
            return None

    monkeypatch.setattr(module, "QShortcut", FakeShortcut)
    monkeypatch.setattr(module, "QKeySequence", lambda key: key)

    widget = DummyWidget()

    widget._configure_prompt_shortcuts()

    assert widget.ui.prompt.keyPressEvent is native_keypress
    assert len(widget._prompt_submit_shortcuts) == 2
    assert len(widget._slash_popup_shortcuts) == 4
    assert all(
        shortcut.context == Qt.ShortcutContext.WidgetShortcut
        for shortcut in widget._prompt_submit_shortcuts
        + widget._slash_popup_shortcuts
    )
    assert all(not shortcut.enabled for shortcut in widget._slash_popup_shortcuts)


def test_chat_prompt_uses_chat_action_by_default():
    """Plain chat input should not default to legacy command-classifier mode."""
    widget = SimpleNamespace()

    assert ChatPromptWidget.action.fget(widget) is LLMActionType.CHAT