"""Tests for chat prompt show-event startup helpers."""

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QEvent, Qt

from airunner.components.chat.gui.widgets import chat_prompt_widget as module
from airunner.components.chat.gui.widgets.chat_prompt_widget import (
    ChatPromptWidget,
)
from airunner.enums import LLMActionType, ModelStatus, ModelType


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

    def ensure_conversation_context():
        call_order.append("ensure")
        return 1

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
        _ensure_conversation_context=ensure_conversation_context,
        conversation_id=None,
        start_progress_bar=Mock(),
        _parse_slash_command=lambda prompt: (None, prompt, None, False),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _slash_command_request_prompt=lambda prompt, _slash: prompt,
        logger=Mock(),
        enable_send_button=Mock(),
        disable_send_button=Mock(),
        _set_generation_button_visibility=Mock(),
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

    widget._set_generation_button_visibility.assert_called_once_with(True)
    assert call_order == [
        "clear",
        ("append", "Hello", True),
    ]
    assert scheduled and scheduled[0][0] == 0

    scheduled[0][1]()

    assert call_order[-1][0] == "submit"


def test_submit_generation_request_bootstraps_conversation_after_ui_turn():
    """Conversation bootstrap should happen in the queued submit phase."""
    call_order = []
    sent_requests = []

    def ensure_conversation_context():
        call_order.append("ensure")
        return 7

    def get_loaded_models():
        call_order.append("probe")
        return []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=get_loaded_models,
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            prompt=SimpleNamespace(setPlainText=Mock()),
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        _ensure_conversation_context=ensure_conversation_context,
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=[],
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        logger=Mock(),
        enable_send_button=Mock(),
        _set_generation_button_visibility=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
        generating=True,
        prompt="",
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Hello",
        action=LLMActionType.CHAT,
        conversation_id=None,
        request_id="req-1",
        slash_command=None,
    )

    assert call_order == ["ensure", "probe"]
    assert sent_requests[0]["conversation_id"] == 7


def test_submit_generation_request_shows_loading_indicator_when_llm_is_cold():
    """Cold-started LLM requests should show inline loading status."""
    sent_requests = []
    conversation = SimpleNamespace(show_model_loading_status=Mock())
    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            conversation=conversation,
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        _pending_model_loading_request_ids=set(),
        _show_model_loading_indicator=(
            lambda request_id: ChatPromptWidget._show_model_loading_indicator(
                widget,
                request_id,
            )
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=[],
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        logger=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Hello",
        action=LLMActionType.CHAT,
        conversation_id=1,
        request_id="req-cold",
        slash_command=None,
    )

    conversation.show_model_loading_status.assert_called_once_with(
        "req-cold",
        "Loading model",
    )
    assert widget._pending_model_loading_request_ids == {"req-cold"}
    assert sent_requests


def test_model_loaded_clears_pending_inline_loading_indicator():
    """Loaded LLM status should remove any pending inline loading widgets."""
    conversation = SimpleNamespace(clear_model_loading_status=Mock())
    widget = SimpleNamespace(
        chat_loaded=False,
        ui=SimpleNamespace(conversation=conversation),
        _pending_model_loading_request_ids={"req-cold"},
        _clear_model_loading_indicators=(
            lambda request_id=None: (
                ChatPromptWidget._clear_model_loading_indicators(
                    widget,
                    request_id,
                )
            )
        ),
        disable_send_button=Mock(),
        enable_send_button=Mock(),
    )

    ChatPromptWidget.on_model_status_changed_signal(
        widget,
        {"model": ModelType.LLM, "status": ModelStatus.LOADED},
    )

    conversation.clear_model_loading_status.assert_called_once_with(
        "req-cold"
    )
    widget.enable_send_button.assert_called_once_with()
    assert widget._pending_model_loading_request_ids == set()


def test_stop_button_restores_submit_immediately():
    """Stopping a chat request should swap controls back right away."""
    widget = SimpleNamespace(
        api=SimpleNamespace(llm=SimpleNamespace(interrupt=Mock())),
        stop_progress_bar=Mock(),
        enable_send_button=Mock(),
        _set_generation_button_visibility=Mock(),
        generating=True,
    )

    ChatPromptWidget.on_stop_button_clicked(widget)

    widget.api.llm.interrupt.assert_called_once_with()
    widget.stop_progress_bar.assert_called_once_with()
    widget._set_generation_button_visibility.assert_called_once_with(False)
    widget.enable_send_button.assert_called_once_with()
    assert widget.generating is False


def test_disable_send_button_keeps_ui_button_clickable():
    """Chat disable state should not hard-disable the visible send button."""
    send_button = Mock()
    widget = SimpleNamespace(
        ui=SimpleNamespace(send_button=send_button),
        _disabled=False,
    )

    ChatPromptWidget.disable_send_button(widget)

    send_button.setEnabled.assert_not_called()
    assert widget._disabled is True


def test_chat_completion_waits_for_end_of_message():
    """The stop control should remain until the streamed reply finishes."""
    widget = SimpleNamespace(
        stop_progress_bar=Mock(),
        enable_generate=Mock(),
        _estimate_token_count=lambda _message: 2,
        _current_response_tokens=0,
        _tokens_received_last=0,
        _tokens_received_total=0,
        _update_token_tracking_labels=Mock(),
    )

    ChatPromptWidget.on_add_bot_message_to_conversation(
        widget,
        {
            "response": SimpleNamespace(
                message="Hi",
                is_first_message=True,
                is_end_of_message=False,
            )
        },
    )

    widget.stop_progress_bar.assert_called_once_with()
    widget.enable_generate.assert_not_called()
    widget._update_token_tracking_labels.assert_not_called()

    ChatPromptWidget.on_add_bot_message_to_conversation(
        widget,
        {
            "response": SimpleNamespace(
                message=" there",
                is_first_message=False,
                is_end_of_message=True,
            )
        },
    )

    widget.enable_generate.assert_called_once_with()
    widget._update_token_tracking_labels.assert_called_once_with()
    assert widget._tokens_received_last == 4
    assert widget._tokens_received_total == 4


def test_attach_button_allows_documents_without_vision_support():
    """Document attachment should stay available on text-only models."""
    attach_button = Mock()
    widget = SimpleNamespace(
        ui=SimpleNamespace(attach_button=attach_button),
        _is_model_vision_capable=lambda: False,
    )

    ChatPromptWidget._update_attach_button_visibility(widget)

    attach_button.setEnabled.assert_called_once_with(True)
    attach_button.setToolTip.assert_called_once_with(
        "Attach documents for RAG"
    )


def test_submit_generation_request_attaches_rag_documents():
    """Attached documents should be forwarded via rag_files."""
    sent_requests = []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=["/tmp/notes.md"],
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        logger=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Search these notes",
        action=LLMActionType.CHAT,
        conversation_id=1,
        request_id="req-1",
        slash_command=None,
    )

    assert sent_requests
    llm_request = sent_requests[0]["llm_request"]
    assert llm_request.rag_files == ["/tmp/notes.md"]
    assert llm_request.force_tool is None
    assert llm_request.tool_categories == ["rag"]
    assert llm_request.attached_document_capabilities == []
    assert llm_request.attached_document_total_tokens == 0
    assert llm_request.attached_document_total_characters == 0


def test_submit_generation_request_includes_document_capabilities(
    monkeypatch,
    tmp_path,
):
    """Attached documents should include planner capability metadata."""
    sent_requests = []
    document_path = tmp_path / "notes.md"
    document_path.write_text("Alpha beta gamma", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "extract_text_from_file",
        lambda _path: "Alpha beta gamma",
    )

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=[str(document_path)],
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        logger=Mock(),
        _estimate_token_count=lambda prompt: 3 if prompt else 0,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
        _model_context_tokens=8,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Search these notes",
        action=LLMActionType.CHAT,
        conversation_id=1,
        request_id="req-capabilities",
        slash_command=None,
    )

    llm_request = sent_requests[0]["llm_request"]
    assert llm_request.attached_document_total_tokens == 3
    assert llm_request.attached_document_total_characters == 16
    assert llm_request.attached_document_capabilities == [
        {
            "path": str(document_path),
            "file_name": "notes.md",
            "file_size": document_path.stat().st_size,
            "estimated_tokens": 3,
            "estimated_characters": 16,
            "text_available": True,
            "fits_current_context": True,
        }
    ]


def test_submit_generation_request_keeps_document_attachments_visible():
    """Attached document pills should persist until the user removes them."""
    sent_requests = []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=["/tmp/notes.md"],
        llm_generator_settings=SimpleNamespace(enable_thinking=False),
        logger=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Review this document for me",
        action=LLMActionType.CHAT,
        conversation_id=1,
        request_id="req-1",
        slash_command=None,
    )

    assert sent_requests
    assert widget._attached_documents == ["/tmp/notes.md"]


def test_submit_generation_request_uses_action_presets_when_override_disabled():
    """Unchecked manual overrides should keep the action preset profile."""
    sent_requests = []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=[],
        llm_generator_settings=SimpleNamespace(
            override_parameters=False,
            enable_thinking=False,
            temperature=100,
            top_p=100,
            max_new_tokens=42,
            top_k=99,
            repetition_penalty=500,
            ngram_size=7,
            min_length=3,
            num_beams=4,
            sequences=2,
            do_sample=False,
            early_stopping=False,
            eta_cutoff=7,
            length_penalty=2000,
            use_cache=False,
        ),
        logger=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Hello",
        action=LLMActionType.CHAT,
        conversation_id=1,
        request_id="req-override-off",
        slash_command=None,
    )

    llm_request = sent_requests[0]["llm_request"]
    assert llm_request.temperature == 0.7
    assert llm_request.top_p == 0.8
    assert llm_request.max_new_tokens == 8192
    assert llm_request.tool_categories is None


def test_submit_generation_request_applies_manual_overrides_when_enabled():
    """Checked manual overrides should replace visible generation params."""
    sent_requests = []

    widget = SimpleNamespace(
        api=SimpleNamespace(
            model_load_balancer=SimpleNamespace(
                get_loaded_models=lambda: [],
                switch_to_non_art_mode=Mock(),
            ),
            llm=SimpleNamespace(
                send_request=lambda **kwargs: sent_requests.append(kwargs)
            ),
        ),
        ui=SimpleNamespace(
            thinking_checkbox=SimpleNamespace(isChecked=lambda: False),
        ),
        start_progress_bar=Mock(),
        _is_thinking_enabled_for_request=lambda: False,
        _get_reasoning_effort_for_request=lambda: None,
        _collect_images_for_llm=lambda: [],
        _is_model_vision_capable=lambda: False,
        _attached_documents=[],
        llm_generator_settings=SimpleNamespace(
            override_parameters=True,
            enable_thinking=False,
            temperature=100,
            top_p=100,
            max_new_tokens=42,
            top_k=99,
            repetition_penalty=250,
            ngram_size=7,
            min_length=3,
            num_beams=4,
            sequences=2,
            do_sample=False,
            early_stopping=False,
            eta_cutoff=7,
            length_penalty=2000,
            use_cache=False,
        ),
        logger=Mock(),
        _estimate_token_count=lambda _prompt: 1,
        _update_token_tracking_labels=Mock(),
        _tokens_sent_last=0,
        _tokens_sent_total=0,
        _tokens_received_last=0,
        _current_response_tokens=0,
    )

    ChatPromptWidget._submit_generation_request(
        widget,
        actual_prompt="Search the document",
        action=LLMActionType.PERFORM_RAG_SEARCH,
        conversation_id=1,
        request_id="req-override-on",
        slash_command=None,
    )

    llm_request = sent_requests[0]["llm_request"]
    assert llm_request.do_sample is False
    assert llm_request.temperature == 0.1
    assert llm_request.top_p == 0.1
    assert llm_request.max_new_tokens == 42
    assert llm_request.num_beams == 4
    assert llm_request.num_return_sequences == 2
    assert llm_request.tool_categories == ["RAG", "SEARCH"]


def test_attach_knowledge_base_document_marks_document_active(
    monkeypatch,
):
    """Knowledge-base drops should mark the document active and attach it."""
    update = Mock()
    create = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(id=9, indexed=True)],
                update=update,
                create=create,
            )
        ),
    )

    widget = SimpleNamespace(
        _validate_knowledge_base_document_path=lambda path: path,
        _add_document_attachment=Mock(),
        emit_signal=Mock(),
    )

    ChatPromptWidget._attach_knowledge_base_document(
        widget,
        "/tmp/doc.pdf",
    )

    update.assert_called_once_with(pk=9, active=True)
    create.assert_not_called()
    widget._add_document_attachment.assert_called_once_with(
        "/tmp/doc.pdf"
    )
    widget.emit_signal.assert_called_once_with(
        module.SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.pdf"]},
    )


def test_add_document_attachment_from_path_activates_imported_document(
    monkeypatch,
):
    """Imported attachments should flow through active-document sync."""
    monkeypatch.setattr(
        module,
        "import_document_to_library",
        Mock(return_value="/tmp/imported.md"),
    )
    widget = SimpleNamespace(
        documents_path="/tmp/library",
        logger=Mock(),
        _attach_knowledge_base_document=Mock(),
    )

    ChatPromptWidget._add_document_attachment_from_path(
        widget,
        "/tmp/source.md",
    )

    widget._attach_knowledge_base_document.assert_called_once_with(
        "/tmp/imported.md"
    )


def test_set_document_attachments_rebuilds_from_active_documents():
    """Prompt pills should be rebuilt from the active document set."""
    old_widget = SimpleNamespace(deleteLater=Mock())
    added = []
    widget = SimpleNamespace(
        _document_attachment_widgets=[old_widget],
        _attached_documents=["/tmp/old.md"],
        _update_attachments_visibility=Mock(),
    )

    def add_document_attachment(file_path):
        added.append(file_path)
        widget._attached_documents.append(file_path)

    widget._add_document_attachment = add_document_attachment

    ChatPromptWidget._set_document_attachments(
        widget,
        ["/tmp/a.md", "/tmp/a.md", "/tmp/b.md"],
    )

    old_widget.deleteLater.assert_called_once_with()
    assert widget._attached_documents == ["/tmp/a.md", "/tmp/b.md"]
    assert added == ["/tmp/a.md", "/tmp/b.md"]


def test_on_document_collection_changed_syncs_prompt_attachments():
    """Prompt pills should refresh when the active collection changes."""
    widget = SimpleNamespace(
        _sync_document_attachments_from_active_documents=Mock(),
    )

    ChatPromptWidget.on_document_collection_changed(widget, {})

    widget._sync_document_attachments_from_active_documents.assert_called_once_with()


def test_remove_document_attachment_deactivates_document(monkeypatch):
    """Removing a prompt pill should deactivate the document globally."""
    update = Mock()
    monkeypatch.setattr(
        module,
        "Document",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter_by=lambda path: [SimpleNamespace(id=13)],
                update=update,
            )
        ),
    )
    pill = SimpleNamespace()
    widget = SimpleNamespace(
        _attached_documents=["/tmp/doc.md"],
        _document_attachment_widgets=[pill],
        _remove_attachment_widget=Mock(),
        emit_signal=Mock(),
    )

    ChatPromptWidget._remove_document_attachment(
        widget,
        pill,
        "/tmp/doc.md",
    )

    assert widget._attached_documents == []
    assert widget._document_attachment_widgets == []
    widget._remove_attachment_widget.assert_called_once_with(pill)
    update.assert_called_once_with(pk=13, active=False)
    widget.emit_signal.assert_called_once_with(
        module.SignalCode.DOCUMENT_COLLECTION_CHANGED,
        {"paths": ["/tmp/doc.md"]},
    )


def test_handle_drag_enter_accepts_knowledge_base_tree_document_drag():
    """Prompt drags should accept document items from the knowledge tree."""
    path = "/home/joe/Projects/airunner/README.md"
    source = SimpleNamespace(
        selectedIndexes=lambda: [
            SimpleNamespace(
                data=lambda role=None: (
                    path
                    if role == Qt.ItemDataRole.UserRole
                    else None
                )
            )
        ]
    )
    event = SimpleNamespace(
        mimeData=lambda: SimpleNamespace(
            hasFormat=lambda _fmt: False,
            hasUrls=lambda: False,
            formats=lambda: [],
        ),
        source=lambda: source,
        acceptProposedAction=Mock(),
    )
    widget = SimpleNamespace(_is_model_vision_capable=lambda: False)
    widget._extract_dragged_knowledge_base_paths = (
        lambda drag_event: ChatPromptWidget._extract_dragged_knowledge_base_paths(
            widget,
            drag_event,
        )
    )

    handled = ChatPromptWidget._handle_drag_enter(widget, event)

    assert handled is True
    event.acceptProposedAction.assert_called_once_with()


def test_handle_drop_attaches_knowledge_base_tree_document():
    """Prompt drops should attach document items from the knowledge tree."""
    path = "/home/joe/Projects/airunner/README.md"
    source = SimpleNamespace(
        selectedIndexes=lambda: [
            SimpleNamespace(
                data=lambda role=None: (
                    path
                    if role == Qt.ItemDataRole.UserRole
                    else None
                )
            )
        ]
    )
    event = SimpleNamespace(
        mimeData=lambda: SimpleNamespace(
            hasFormat=lambda _fmt: False,
            hasUrls=lambda: False,
            formats=lambda: [],
        ),
        source=lambda: source,
        acceptProposedAction=Mock(),
    )
    widget = SimpleNamespace(
        _is_model_vision_capable=lambda: False,
        _attach_knowledge_base_document=Mock(),
    )
    widget._extract_dragged_knowledge_base_paths = (
        lambda drop_event: ChatPromptWidget._extract_dragged_knowledge_base_paths(
            widget,
            drop_event,
        )
    )

    handled = ChatPromptWidget._handle_drop(widget, event)

    assert handled is True
    widget._attach_knowledge_base_document.assert_called_once_with(path)
    event.acceptProposedAction.assert_called_once_with()


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


def test_event_filter_submits_prompt_even_when_internal_flag_is_disabled():
    """Enter should follow the same send path as the clickable button."""
    prompt = object()
    widget = SimpleNamespace(
        ui=SimpleNamespace(prompt=prompt),
        _disabled=True,
        _is_prompt_submit_keypress=lambda event: True,
        do_generate=Mock(),
    )

    handled = ChatPromptWidget.eventFilter(widget, prompt, object())

    assert handled is True
    widget.do_generate.assert_called_once_with()


def test_chat_prompt_uses_chat_action_by_default():
    """Plain chat input should not default to legacy command-classifier mode."""
    widget = SimpleNamespace()

    assert ChatPromptWidget.action.fget(widget) is LLMActionType.CHAT


def test_refresh_slash_commands_keeps_required_search_commands():
    """Search, deepsearch, and news should remain available."""
    widget = SimpleNamespace()

    ChatPromptWidget._refresh_slash_commands_data(widget)

    commands = {item["command"] for item in widget._slash_commands_data}
    assert "/search" in commands
    assert "/deepsearch" in commands
    assert "/news" in commands
    assert "/deepresearch" not in commands
    assert "/image" not in commands
    assert "/code" not in commands
    assert "/clear" not in commands