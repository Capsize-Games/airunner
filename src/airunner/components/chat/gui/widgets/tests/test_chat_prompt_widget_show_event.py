"""Tests for chat prompt show-event startup helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QEvent, Qt

from airunner.components.chat.gui.widgets import chat_prompt_widget as module
from airunner.components.chat.gui.widgets.chat_request_mode import (
    get_chat_request_mode,
)
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


def test_resolve_initial_section_defaults_to_canvas(monkeypatch):
    """The chat widget should treat the single center pane as art/canvas."""
    monkeypatch.setattr(module, "AIRUNNER_ART_ENABLED", True)

    assert ChatPromptWidget._resolve_initial_section(SimpleNamespace()) == (
        "art_editor_button"
    )


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
        _parse_slash_command=lambda prompt: (None, prompt, None, False),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _selected_request_mode=lambda: get_chat_request_mode("ask"),
        _slash_command_request_prompt=lambda prompt, _slash: prompt,
        _request_mode_prompt=lambda prompt, _mode: prompt,
        _request_system_prompt=lambda _mode: None,
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
        _model_supports_reasoning_effort=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _is_thinking_enabled_for_request=(
            lambda: ChatPromptWidget._is_thinking_enabled_for_request(widget)
        ),
        _request_system_prompt=lambda _mode: None,
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
        request_mode=None,
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
                prompt=SimpleNamespace(
                    keyPressEvent=native_keypress,
                    installEventFilter=Mock(),
                )
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
    widget.ui.prompt.installEventFilter.assert_called_once_with(widget)
    assert len(widget._prompt_submit_shortcuts) == 0
    assert len(widget._slash_popup_shortcuts) == 4
    assert all(
        shortcut.context == Qt.ShortcutContext.WidgetShortcut
        for shortcut in widget._prompt_submit_shortcuts
        + widget._slash_popup_shortcuts
    )
    assert all(not shortcut.enabled for shortcut in widget._slash_popup_shortcuts)


def test_plain_enter_is_treated_as_prompt_submit():
    """Plain Enter should submit the prompt."""
    widget = SimpleNamespace()
    event = SimpleNamespace(
        type=lambda: QEvent.Type.KeyPress,
        key=lambda: Qt.Key.Key_Return,
        modifiers=lambda: Qt.KeyboardModifier.NoModifier,
    )

    assert ChatPromptWidget._is_prompt_submit_keypress(widget, event) is True


def test_shift_enter_is_not_treated_as_prompt_submit():
    """Shift+Enter should remain available for newline insertion."""
    widget = SimpleNamespace()
    event = SimpleNamespace(
        type=lambda: QEvent.Type.KeyPress,
        key=lambda: Qt.Key.Key_Return,
        modifiers=lambda: Qt.KeyboardModifier.ShiftModifier,
    )

    assert ChatPromptWidget._is_prompt_submit_keypress(widget, event) is False


def test_chat_prompt_uses_chat_action_by_default():
    """Plain chat input should not default to legacy command-classifier mode."""
    widget = SimpleNamespace()

    assert ChatPromptWidget.action.fget(widget) is LLMActionType.CHAT


def test_request_mode_helpers_use_qsettings(monkeypatch):
    """Request mode persistence should read and write through QSettings."""

    class FakeSettings:
        def __init__(self):
            self.values = {"request_mode": "plan"}
            self.group = None

        def beginGroup(self, group):
            self.group = group

        def value(self, key, default=None, type=None):
            return self.values.get(key, default)

        def setValue(self, key, value):
            self.values[key] = value

        def endGroup(self):
            self.group = None

    settings = FakeSettings()
    widget = SimpleNamespace()

    monkeypatch.setattr(module, "get_qsettings", lambda: settings)

    mode_key = ChatPromptWidget._load_request_mode_key(widget)
    ChatPromptWidget._save_request_mode_key(widget, "agent")

    assert mode_key == "plan"
    assert settings.values["request_mode"] == "agent"


def test_request_system_prompt_appends_project_instructions(monkeypatch):
    """Agent mode should append project instructions to the base prompt."""

    class PromptService:
        @staticmethod
        def instructions_text():
            return "Use pytest for validation."

    widget = SimpleNamespace()

    monkeypatch.setattr(module, "load_coding_prompt", lambda _key: "Base prompt")
    monkeypatch.setattr(
        module,
        "active_project_prompt_service",
        lambda: PromptService(),
    )

    prompt = ChatPromptWidget._request_system_prompt(
        widget,
        get_chat_request_mode("agent"),
    )

    assert "Base prompt" in prompt
    assert "Project Instructions" in prompt
    assert "Use pytest for validation." in prompt


def test_parse_slash_command_recognizes_project_template(monkeypatch):
    """Project prompt templates should parse like slash commands."""
    widget = SimpleNamespace(
        _project_slash_templates={
            "maze": SimpleNamespace(prompt="Template prompt")
        },
        _refresh_slash_commands_data=lambda: None,
        logger=Mock(),
    )

    result = ChatPromptWidget._parse_slash_command(
        widget,
        "/maze add DFS support",
    )

    assert result == ("maze", "add DFS support", None, True)


def test_parse_slash_command_prefers_builtin_config():
    """Built-in slash commands should win over same-name templates."""
    widget = SimpleNamespace(
        _project_slash_templates={
            "deepsearch": SimpleNamespace(prompt="Template prompt")
        },
        _refresh_slash_commands_data=lambda: None,
        logger=Mock(),
    )

    result = ChatPromptWidget._parse_slash_command(
        widget,
        "/deepsearch weekly sync",
    )

    assert result == (
        "deepsearch",
        "weekly sync",
        LLMActionType.DEEP_RESEARCH,
        False,
    )


def test_parse_slash_command_rejects_retired_command_names():
    """Retired slash commands should not parse from project templates."""
    widget = SimpleNamespace(
        _project_slash_templates={
            "meeting-pack": SimpleNamespace(prompt="Template prompt")
        },
        _refresh_slash_commands_data=lambda: None,
        logger=Mock(),
    )

    result = ChatPromptWidget._parse_slash_command(
        widget,
        "/meeting-pack weekly sync",
    )

    assert result == (None, "/meeting-pack weekly sync", None, False)


def test_refresh_slash_commands_keeps_builtin_template_binding(monkeypatch):
    """Same-name project templates should stay bound to built-in commands."""
    widget = SimpleNamespace()
    prompt_service = SimpleNamespace(
        prompt_templates=lambda: [
            SimpleNamespace(
                command_name="deepsearch",
                description="Deep search template",
                prompt="Template prompt",
            )
        ]
    )

    monkeypatch.setattr(
        module,
        "active_project_prompt_service",
        lambda: prompt_service,
    )

    ChatPromptWidget._refresh_slash_commands_data(widget)

    assert widget._project_slash_templates["deepsearch"].prompt == (
        "Template prompt"
    )
    assert [
        item["command"] for item in widget._slash_commands_data
    ].count("/deepsearch") == 1


def test_refresh_slash_commands_omits_retired_commands(monkeypatch):
    """Retired commands should stay out of autocomplete data."""
    widget = SimpleNamespace()
    prompt_service = SimpleNamespace(
        prompt_templates=lambda: [
            SimpleNamespace(
                command_name="meeting-pack",
                description="Meeting pack",
                prompt="Template prompt",
            ),
            SimpleNamespace(
                command_name="maze",
                description="Maze prompt",
                prompt="Maze prompt",
            ),
        ]
    )

    monkeypatch.setattr(
        module,
        "active_project_prompt_service",
        lambda: prompt_service,
    )

    ChatPromptWidget._refresh_slash_commands_data(widget)

    assert "meeting-pack" not in widget._project_slash_templates
    assert "maze" in widget._project_slash_templates
    commands = [item["command"] for item in widget._slash_commands_data]
    assert "/meeting-pack" not in commands
    assert "/maze" in commands


def test_refresh_slash_commands_keeps_required_search_commands(monkeypatch):
    """Search, deepsearch, and news should remain available."""
    widget = SimpleNamespace()

    monkeypatch.setattr(
        module,
        "active_project_prompt_service",
        lambda: None,
    )

    ChatPromptWidget._refresh_slash_commands_data(widget)

    commands = {item["command"] for item in widget._slash_commands_data}
    assert "/search" in commands
    assert "/deepsearch" in commands
    assert "/news" in commands
    assert "/deepresearch" not in commands
    assert "/image" not in commands
    assert "/code" not in commands
    assert "/clear" not in commands


def test_submit_generation_request_sets_request_mode_system_prompt():
    """Request-mode prompts should flow into the generated llm_request."""
    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
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
        _model_supports_reasoning_effort=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _is_thinking_enabled_for_request=(
            lambda: ChatPromptWidget._is_thinking_enabled_for_request(widget)
        ),
        _request_system_prompt=lambda _mode: "Plan prompt",
        logger=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Plan this task",
        action=LLMActionType.CODE,
        conversation_id=1,
        request_id="req-plan",
        request_mode=get_chat_request_mode("plan"),
        slash_command=None,
    )

    llm_request = widget.api.llm.send_request.call_args.kwargs["llm_request"]
    assert llm_request.system_prompt == "Plan prompt"
    assert llm_request.mode_override == "code"