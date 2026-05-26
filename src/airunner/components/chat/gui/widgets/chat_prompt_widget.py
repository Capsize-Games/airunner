import os
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from PIL import Image
from PySide6.QtCore import QEvent, QTimer, Slot, Qt, QPoint
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtGui import (
    QTextCursor,
    QFont,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QShortcut,
)

from langchain_core.messages.utils import count_tokens_approximately

from airunner.components.chat.gui.widgets.templates.chat_prompt_ui import (
    Ui_chat_prompt,
)
from airunner.components.chat.gui.widgets.chat_attachment_pill_widget import (
    ChatAttachmentPillWidget,
)
from airunner_model.models.document import Document
from airunner.components.documents.document_import import (
    chat_image_suffixes,
    import_document_to_library,
    is_rag_document_path,
    rag_document_suffixes,
)
from airunner_model.models.conversation import Conversation
from airunner.components.llm.managers.agent.document_loader import (
    extract_text_from_file,
)
from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
    ModelService,
)
from airunner.utils.application.log_hygiene import summarize_mapping_keys
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.utils.application import create_worker, get_logger
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.workers.llm_response_worker import (
    LLMResponseWorker,
)
from airunner.settings import (
    AIRUNNER_ART_ENABLED,
    AIRUNNER_LOG_LEVEL,
    RETIRED_SLASH_COMMANDS,
    SLASH_COMMANDS,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig
from airunner_model.runtimes.file_policy import (
    PathPolicyError,
    resolve_existing_file,
)
from airunner.utils.image import convert_binary_to_image


# MIME type used by ImageWidget for drag operations
IMAGE_METADATA_MIME_TYPE = "application/x-qt-image-metadata"
KNOWLEDGE_BASE_DOCUMENT_SUFFIXES = rag_document_suffixes() + (
    ".doc",
    ".docx",
    ".odt",
    ".zim",
)


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("chevron-up", "send_button"),
        ("plus", "clear_conversation_button"),
        ("stop-circle", "stop_button"),
        ("paperclip", "attach_button"),
    ]
    logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def _attach_lazy_tab_widget(
        self,
        parent_attr: str,
        layout_attr: str,
        widget_attr: str,
        placeholder_attr: str,
        object_name: str,
        factory,
    ):
        widget = getattr(self.ui, widget_attr, None)
        if widget is not None:
            return widget

        layout = getattr(self.ui, layout_attr)
        widget = factory(getattr(self.ui, parent_attr))
        widget.setObjectName(object_name)
        layout.addWidget(widget, 0, 0, 1, 1)

        placeholder = getattr(self.ui, placeholder_attr, None)
        if placeholder is not None:
            layout.removeWidget(placeholder)
            placeholder.deleteLater()
            setattr(self.ui, placeholder_attr, None)

        setattr(self.ui, widget_attr, widget)
        return widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL: self.on_hear_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_text_generate_request_signal,
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.DOCUMENT_COLLECTION_CHANGED: self.on_document_collection_changed,
            SignalCode.SECTION_CHANGED: self.on_section_changed_signal,
        }
        self._splitters = ["chat_prompt_splitter"]
        self._default_splitter_settings_applied = False
        super().__init__()
        self._highlighted = False
        self.registered: bool = False
        self.scroll_bar = None
        self.is_modal = True
        self.generating = False
        self.prefix = ""
        self.prompt = ""
        self.suffix = ""
        self.spacer = None
        self.action_menu_displayed = None
        self.action_menu_displayed = None
        self.messages_spacer = None
        self.chat_loaded = False
        self._model_context_tokens: Optional[int] = None
        
        # Token tracking for sent/received messages
        self._tokens_sent_last: int = 0
        self._tokens_received_last: int = 0
        self._tokens_sent_total: int = 0
        self._tokens_received_total: int = 0
        self._current_response_tokens: int = 0  # Accumulator for streaming response
        self._active_section: Optional[str] = self._resolve_initial_section()
        
        # Image attachments for vision-capable models
        self._attached_images: List[Tuple[Image.Image, Optional[str]]] = []
        self._image_attachment_widgets: List[ChatAttachmentPillWidget] = []
        self._attached_documents: List[str] = []
        self._document_attachment_widgets: List[
            ChatAttachmentPillWidget
        ] = []
        self._pending_model_loading_request_ids: set[str] = set()
        self._attachments_spacer: Optional[QSpacerItem] = None
        self._startup_controls_loaded = False
        self._model_dropdown_line_edit = None
        
        # Default plain chat input to CHAT mode. Tool routing still happens
        # per-request via auto selection when the prompt needs it.
        self.update_llm_generator_settings(action=LLMActionType.CHAT.name)

        self._create_reasoning_effort_dropdown()
        
        self._prompt_shortcuts_configured = False
        self._prompt_submit_shortcuts: List[QShortcut] = []
        self._slash_popup_shortcuts: List[QShortcut] = []
        
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
        
        # Setup slash command autocomplete
        self._setup_slash_command_completer()
        self._configure_prompt_shortcuts()
        
        # Setup file attachment handling
        self._setup_image_attachments()
        
        self._llm_response_worker = create_worker(
            LLMResponseWorker, sleep_time_in_ms=1
        )
        # Conversation history manager used to fetch conversation IDs and history
        self._conversation_history_manager = ConversationHistoryManager()
        self.loading = True
        self.conversation_id: int = None
        self.conversation = None
        self._llm_history_tab_index = None
        self._llm_history_widget = None
        if hasattr(self.ui, "chat_history_placeholder"):
            self.ui.chat_history_placeholder.setVisible(False)
        self.ui.tabWidget.tabBar().hide()
        self._model_context_tokens = self._resolve_model_context_length()
        if hasattr(self.ui, "token_count"):
            self._set_token_count_label(0, self._model_context_tokens)
        
        # Initialize token tracking labels
        self._update_token_tracking_labels()
        self._set_generation_button_visibility(False)

    def _set_generation_button_visibility(
        self, is_generating: bool
    ) -> None:
        """Show only the action button that matches request state."""
        ui = getattr(self, "ui", None)
        if ui is None:
            return

        send_button = getattr(ui, "send_button", None)
        stop_button = getattr(ui, "stop_button", None)

        if send_button is not None:
            send_button.setVisible(not is_generating)
        if stop_button is not None:
            stop_button.setVisible(is_generating)

    def _apply_default_splitter_settings(self):
        if hasattr(self, "ui") and self.ui is not None:
            default_chat_splitter_config = {
                "chat_prompt_splitter": {
                    "index_to_maximize": 0,
                    "min_other_size": 50,
                }
            }
            self.load_splitter_settings(
                orientations={"chat_prompt_splitter": Qt.Orientation.Vertical},
                default_maximize_config=default_chat_splitter_config,
            )
        else:
            self.logger.warning(
                "ChatPromptWidget: UI not available when applying "
                "default splitter settings."
            )

    def _schedule_default_splitter_settings(self) -> None:
        """Apply splitter settings after the show event unwinds."""
        if self._default_splitter_settings_applied:
            return
        if not self.isVisible():
            return
        self._default_splitter_settings_applied = True
        QTimer.singleShot(0, self._apply_default_splitter_settings)

    @Slot()
    def on_clear_conversation_button_clicked(self):
        """Create a new conversation and clear the display."""
        # Reset token counters for new conversation
        self._tokens_sent_last = 0
        self._tokens_received_last = 0
        self._tokens_sent_total = 0
        self._tokens_received_total = 0
        self._current_response_tokens = 0
        self._update_token_tracking_labels()
        
        # Create a new conversation in the database
        new_conversation = Conversation.create()
        if new_conversation:
            self.logger.info(
                f"Created new conversation with ID: {new_conversation.id}"
            )
            # Make it the current conversation
            Conversation.make_current(new_conversation.id)
            # Update GUI state
            self.conversation_id = new_conversation.id
            self.conversation = new_conversation
            self._set_api_conversation_id(new_conversation.id)
            # Clear the display
            if hasattr(self.ui, "conversation"):
                self.ui.conversation.clear_conversation()
            # Tell the backend to use this new conversation
            self.api.llm.clear_history(conversation_id=new_conversation.id)
        else:
            self.logger.error("Failed to create new conversation")
            # Fallback to old behavior
            self.api.llm.clear_history()

    def _ensure_settings_view_loaded(self):
        """Create the settings page only when the user opens it."""
        from airunner.components.llm.gui.widgets.llm_settings_widget import (
            LLMSettingsWidget,
        )

        return self._attach_lazy_tab_widget(
            "tab_2",
            "gridLayout_3",
            "llm_settings",
            "llm_settings_placeholder",
            "llm_settings",
            LLMSettingsWidget,
        )

    def _ensure_history_view_loaded(self):
        """Create the history page only when the user opens it."""
        from airunner.components.llm.gui.widgets.llm_history_widget import (
            LLMHistoryWidget,
        )

        return self._attach_lazy_tab_widget(
            "tab_3",
            "gridLayout_5",
            "widget",
            "history_placeholder",
            "widget",
            LLMHistoryWidget,
        )

    @Slot()
    def on_send_button_clicked(self):
        self.do_generate()

    def _find_parent_tab_widget(self):
        """Find the parent QTabWidget containing this widget."""
        parent = self.parent()
        while parent is not None:
            from PySide6.QtWidgets import QTabWidget

            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None

    @property
    def action(self) -> LLMActionType:
        # The chat prompt should use conversational mode by default.
        # Explicit slash commands can still override this per request.
        return LLMActionType.CHAT

    def on_model_status_changed_signal(self, data):
        if data["model"] == ModelType.LLM:
            self.chat_loaded = data["status"] is ModelStatus.LOADED
            if self.chat_loaded:
                clear_loading = getattr(
                    self,
                    "_clear_model_loading_indicators",
                    None,
                )
                if callable(clear_loading):
                    clear_loading()

        if not self.chat_loaded:
            self.disable_send_button()
        else:
            self.enable_send_button()

    def _show_model_loading_indicator(self, request_id: str) -> None:
        """Show an inline request-scoped model loading indicator."""
        if not request_id:
            return
        conversation = getattr(self.ui, "conversation", None)
        if conversation is None:
            return
        self._pending_model_loading_request_ids.add(request_id)
        show_loading = getattr(conversation, "show_model_loading_status", None)
        if callable(show_loading):
            show_loading(request_id, "Loading model")

    def _clear_model_loading_indicators(
        self,
        request_id: Optional[str] = None,
    ) -> None:
        """Clear one or all inline model loading indicators."""
        if request_id is None:
            request_ids = tuple(self._pending_model_loading_request_ids)
        elif request_id in self._pending_model_loading_request_ids:
            request_ids = (request_id,)
        else:
            request_ids = ()

        if not request_ids:
            return

        conversation = getattr(self.ui, "conversation", None)
        clear_loading = getattr(conversation, "clear_model_loading_status", None)
        for current_request_id in request_ids:
            if callable(clear_loading):
                clear_loading(current_request_id)
            self._pending_model_loading_request_ids.discard(
                current_request_id
            )

    def on_hear_signal(self, data: Dict):
        transcription = data["transcription"]
        self.prompt = transcription
        self.do_generate()

    def enable_generate(self):
        self.generating = False
        self._set_generation_button_visibility(False)
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    @Slot()
    def on_stop_button_clicked(self):
        self.api.llm.interrupt()
        self.stop_progress_bar()
        self.generating = False
        self._set_generation_button_visibility(False)
        clear_loading = getattr(
            self,
            "_clear_model_loading_indicators",
            None,
        )
        if callable(clear_loading):
            clear_loading()
        self.enable_send_button()

    def do_generate(self, prompt_override=None):
        prompt = (
            self.prompt
            if (prompt_override is None or prompt_override == "")
            else prompt_override
        )

        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        if self.generating:
            if self.held_message is None:
                self.held_message = prompt
                self.disable_send_button()
                self.on_stop_button_clicked()
            return
        self.generating = True
        self._set_generation_button_visibility(True)

        request_id = str(uuid4())

        self.clear_prompt()
        self.logger.info(
            f"do_generate called with prompt: "
            f"{prompt[:100] if prompt else 'None'}..."
        )
        slash_command, cleaned_prompt, action_override, slash_is_template = (
            self._parse_slash_command(prompt)
        )
        self.logger.info(
            "Slash command parse result: command=%s, "
            "action_override=%s",
            slash_command,
            action_override,
        )
        action = self.action
        request_prompt = cleaned_prompt
        if slash_command is not None:
            request_prompt = self._slash_command_request_prompt(
                cleaned_prompt,
                slash_command,
            )
            if not slash_is_template and action_override is not None:
                action = action_override
        self.logger.info(f"Final action: {action}")

        if hasattr(self.ui, "conversation"):
            self.ui.conversation.append_user_message_for_request(
                cleaned_prompt,
                request_id=request_id,
            )

        QTimer.singleShot(
            0,
            lambda: self._submit_generation_request(
                actual_prompt=request_prompt,
                action=action,
                conversation_id=self.conversation_id,
                request_id=request_id,
                slash_command=slash_command,
            ),
        )

        prompt_focus = getattr(getattr(self.ui, "prompt", None), "setFocus", None)
        if callable(prompt_focus):
            for delay in (0, 50, 150):
                QTimer.singleShot(delay, prompt_focus)

    def _submit_generation_request(
        self,
        *,
        actual_prompt: str,
        action: LLMActionType,
        conversation_id: Optional[int],
        request_id: str,
        slash_command: Optional[str],
    ) -> None:
        """Run the heavier generation setup after the UI has a paint turn."""

        if conversation_id is None:
            conversation_id = self._ensure_conversation_context()
        if conversation_id is None:
            self.logger.error(
                "Aborting chat request - unable to determine conversation ID"
            )
            self.ui.prompt.setPlainText(actual_prompt)
            self.prompt = actual_prompt
            self.generating = False
            self._set_generation_button_visibility(False)
            self.enable_send_button()
            return

        model_load_balancer = getattr(self.api, "model_load_balancer", None)
        loaded_models = set(
            model_load_balancer.get_loaded_models()
            if model_load_balancer is not None
            else []
        )
        art_model_loaded = ModelType.SD in loaded_models
        llm_loaded = ModelType.LLM in loaded_models
        daemon_client = getattr(self.api, "daemon_client", None)
        if art_model_loaded and not llm_loaded and daemon_client is None:
            model_load_balancer.switch_to_non_art_mode()
        if not llm_loaded:
            show_loading = getattr(
                self,
                "_show_model_loading_indicator",
                None,
            )
            if callable(show_loading):
                show_loading(request_id)

        self.start_progress_bar()
        
        # Get configuration from slash command
        force_tool = None
        if slash_command and slash_command in SLASH_COMMANDS:
            cmd_config = SLASH_COMMANDS[slash_command]
            force_tool = cmd_config.get("tool")
            self.logger.info(f"Slash command /{slash_command} -> action={action}, force_tool={force_tool}")
        
        # Use actual_prompt (with slash command stripped) for token counting
        sent_tokens = self._estimate_token_count(actual_prompt)
        self._tokens_sent_last = sent_tokens
        self._tokens_sent_total += sent_tokens
        self._tokens_received_last = 0
        self._current_response_tokens = 0
        self._update_token_tracking_labels()
        
        # Create the top-level visible-response request, using manual
        # overrides only when the user explicitly enabled them.
        llm_request = LLMRequest.for_visible_action(
            action,
            getattr(self, "llm_generator_settings", None),
        )
        llm_request.enable_thinking = (
            self._is_thinking_enabled_for_request()
        )
        llm_request.reasoning_effort = self._get_reasoning_effort_for_request()
        
        # Set force_tool if slash command specifies one
        if force_tool:
            llm_request.force_tool = force_tool
            self.logger.info(f"Set force_tool={force_tool} on llm_request")

        rag_files = list(getattr(self, "_attached_documents", []))
        if rag_files:
            llm_request.rag_files = rag_files
            ChatPromptWidget._populate_request_document_capabilities(
                self,
                llm_request,
                rag_files,
            )
            self.logger.info(
                "Added %s document(s) to llm_request for document routing",
                len(rag_files),
            )
        
        self.logger.info(f"Sending request - action={action}, force_tool={llm_request.force_tool}, tool_categories={llm_request.tool_categories}")
        try:
            self.api.llm.send_request(
                actual_prompt,
                llm_request=llm_request,
                action=action,
                do_tts_reply=False,
                conversation_id=conversation_id,
                request_id=request_id,
            )
        except Exception as e:
            self.logger.error(f"Error submitting generation request: {e}")

    def _is_thinking_enabled_for_request(self) -> bool:
        """Return the effective request thinking preference."""
        if not self._model_supports_thinking():
            return False

        return bool(
            getattr(self.llm_generator_settings, "enable_thinking", True)
        )

    def _get_reasoning_effort_for_request(self) -> Optional[str]:
        """Return the request-scoped GPT-OSS reasoning effort."""
        if not self._model_supports_reasoning_effort():
            return None

        if hasattr(self.ui, "reasoning_effort_dropdown"):
            effort = self.ui.reasoning_effort_dropdown.currentData()
            if effort in {"low", "medium", "high"}:
                return effort

        effort = getattr(
            self.llm_generator_settings,
            "reasoning_effort",
            "medium",
        )
        effort = str(effort or "medium").strip().lower()
        if effort in {"low", "medium", "high"}:
            return effort
        return "medium"

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_default_splitter_settings()
        self._configure_prompt_shortcuts()
        self._sync_document_attachments_from_active_documents()

        if not self.chat_loaded:
            self.disable_send_button()

    def _create_prompt_shortcut(
        self,
        key: int,
        handler,
    ) -> QShortcut:
        """Create one prompt-scoped shortcut without overriding key events."""
        shortcut = QShortcut(QKeySequence(key), self.ui.prompt)
        shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut.activated.connect(handler)
        return shortcut

    def _configure_prompt_shortcuts(self) -> None:
        """Install prompt shortcuts while keeping native text input in Qt."""
        if self._prompt_shortcuts_configured:
            return
        if not hasattr(self.ui, "prompt") or self.ui.prompt is None:
            return

        self.ui.prompt.installEventFilter(self)
        self._prompt_submit_shortcuts = []
        self._slash_popup_shortcuts = [
            self._create_prompt_shortcut(
                Qt.Key.Key_Up,
                lambda: self._handle_slash_popup_navigation(Qt.Key.Key_Up),
            ),
            self._create_prompt_shortcut(
                Qt.Key.Key_Down,
                lambda: self._handle_slash_popup_navigation(
                    Qt.Key.Key_Down
                ),
            ),
            self._create_prompt_shortcut(
                Qt.Key.Key_Tab,
                lambda: self._handle_slash_popup_navigation(Qt.Key.Key_Tab),
            ),
            self._create_prompt_shortcut(
                Qt.Key.Key_Escape,
                lambda: self._handle_slash_popup_navigation(
                    Qt.Key.Key_Escape
                ),
            ),
        ]
        self._set_slash_navigation_shortcuts_enabled(False)
        self._prompt_shortcuts_configured = True

    def _set_slash_navigation_shortcuts_enabled(
        self,
        enabled: bool,
    ) -> None:
        """Enable popup navigation shortcuts only while the popup is shown."""
        for shortcut in self._slash_popup_shortcuts:
            shortcut.setEnabled(enabled)

    def _hide_slash_popup(self) -> None:
        """Hide the slash popup and restore normal prompt navigation."""
        if hasattr(self, "_slash_popup") and self._slash_popup is not None:
            self._slash_popup.hide()
        self._set_slash_navigation_shortcuts_enabled(False)

    def _on_submit_shortcut(self) -> None:
        """Submit the current prompt from a keyboard shortcut."""
        self.do_generate()

    def _is_prompt_submit_keypress(self, event: QEvent) -> bool:
        """Return True when a keypress should submit the current prompt."""
        if event.type() != QEvent.Type.KeyPress:
            return False
        if event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return False

        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            return False

        effective_modifiers = (
            modifiers & ~Qt.KeyboardModifier.KeypadModifier
        )
        return effective_modifiers == Qt.KeyboardModifier.NoModifier

    def _finish_startup_controls_if_ready(self) -> None:
        """Populate startup controls after the main window is ready."""
        if self._startup_controls_loaded:
            return
        self._startup_controls_loaded = True
        self._populate_model_dropdown()
        self._populate_reasoning_effort_dropdown()
        self._update_thinking_checkbox_visibility()

    def _apply_prompt_prefix(self, prompt: str, prefix: str) -> str:
        """Return the request prompt with one optional hidden prefix."""

        if not prefix:
            return prompt
        return f"{prefix}{prompt}"

    def _slash_command_request_prompt(
        self,
        prompt: str,
        slash_command: Optional[str],
    ) -> str:
        """Return the request prompt for a slash-command request."""

        if not slash_command:
            return prompt
        if slash_command in RETIRED_SLASH_COMMANDS:
            return prompt
        template = getattr(self, "_project_slash_templates", {}).get(
            slash_command
        )
        if template is not None:
            parts = [template.prompt.strip(), prompt.strip()]
            return "\n\n".join(part for part in parts if part)
        prefix = SLASH_COMMANDS.get(slash_command, {}).get(
            "prompt_prefix",
            "",
        )
        return self._apply_prompt_prefix(prompt, str(prefix or ""))

    def _create_reasoning_effort_dropdown(self) -> None:
        """Add a compact GPT-OSS reasoning selector to the footer."""
        if hasattr(self.ui, "reasoning_effort_dropdown"):
            return

        dropdown = QComboBox(self.ui.footer_container)
        dropdown.setObjectName("reasoning_effort_dropdown")
        dropdown.setMinimumHeight(30)
        dropdown.setMinimumWidth(96)
        dropdown.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        dropdown.setToolTip("GPT-OSS reasoning effort")

        dropdown.currentIndexChanged.connect(self.on_reasoning_effort_changed)
        dropdown.hide()
        self.ui.reasoning_effort_dropdown = dropdown

    def on_main_window_loaded_signal(self, _data=None) -> None:
        """Finish non-critical startup work after the main window loads."""
        self._finish_startup_controls_if_ready()
        if self.loading and hasattr(self.ui, "conversation"):
            QTimer.singleShot(0, self._load_initial_conversation)
            self.loading = False

    def on_document_collection_changed(self, _data=None) -> None:
        """Mirror the active document collection in the prompt pills."""
        self._sync_document_attachments_from_active_documents()

    def _load_initial_conversation(self) -> None:
        """Load the initial conversation after the UI has settled."""
        self.logger.debug("Loading most recent conversation")
        self.load_conversation()

    def llm_action_changed(self, val: str):
        # Deprecated - action is now always AUTO
        pass

    def thinking_toggled(self, checked: bool) -> None:
        """Retained for compatibility after removing the thinking toggle."""
        _ = checked

    def prompt_text_changed(self) -> None:
        """Handle changes to the prompt text and highlight slash commands if present."""
        prompt = self.ui.prompt.toPlainText()
        self.prompt = prompt.strip()
        self._update_token_count_label(self.prompt)
        self.highlight_slash_command(prompt)

    def highlight_slash_command(self, prompt: str) -> None:
        """Highlight the slash command prefix (if any) in the prompt."""
        command = None
        if prompt.startswith("/"):
            self._refresh_slash_commands_data()
            candidate = prompt[1:].split(" ")[0]
            if candidate in SLASH_COMMANDS or candidate in getattr(
                self,
                "_project_slash_templates",
                {},
            ):
                command = candidate
        highlight = command is not None
        prompt_widget = self.ui.prompt
        text = prompt_widget.toPlainText()
        prompt_widget.blockSignals(True)
        cursor = QTextCursor(prompt_widget.document())
        cursor.setPosition(0)

        if command is not None:
            length = len(command) + 1  # +1 for the leading slash
        else:
            length = len(text)

        cursor.setPosition(length, QTextCursor.MoveMode.KeepAnchor)
        fmt = cursor.charFormat()
        fmt.setFontWeight(500 if highlight else 400)
        fmt.setForeground(
            Qt.GlobalColor.black if highlight else Qt.GlobalColor.white
        )
        fmt.setBackground(
            Qt.GlobalColor.yellow if highlight else Qt.GlobalColor.transparent
        )
        cursor.setCharFormat(fmt)

        if command is not None:
            # Move the cursor to the end of the command for further typing
            cursor.setPosition(length)
            cursor.setPosition(len(text), QTextCursor.MoveMode.KeepAnchor)
            fmt = cursor.charFormat()
            fmt.setFontWeight(400)
            fmt.setForeground(Qt.GlobalColor.white)
            fmt.setBackground(Qt.GlobalColor.transparent)
            cursor.setCharFormat(fmt)

        prompt_widget.blockSignals(False)

    def _setup_slash_command_completer(self) -> None:
        """Setup slash command popup for autocomplete."""
        self._refresh_slash_commands_data()
        
        # Create popup list widget - use ToolTip type so it doesn't steal focus
        self._slash_popup = QListWidget()
        self._slash_popup.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self._slash_popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._slash_popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._slash_popup.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._slash_popup.setMouseTracking(True)
        self._slash_popup.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #454545;
                outline: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 12px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #094771;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """)
        
        # Connect click signal only (not activated - we handle Enter ourselves)
        self._slash_popup.itemClicked.connect(self._on_slash_item_clicked)
        
        # Connect text change to check for slash
        self.ui.prompt.textChanged.connect(self._check_slash_command_trigger)

    def _populate_slash_popup(self, filter_text: str = "") -> None:
        """Populate the popup with matching commands."""
        self._refresh_slash_commands_data()
        self._slash_popup.clear()
        
        filter_lower = filter_text.lower()
        for cmd_data in self._slash_commands_data:
            cmd = cmd_data["command"]
            desc = cmd_data["description"]
            
            # Filter by partial match
            if filter_lower and not cmd.lower().startswith(filter_lower):
                continue
            
            # Create item with command and description
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            
            # Format: /command                    description
            display_text = f"{cmd:<20} {desc}"
            item.setText(display_text)
            
            # Use monospace for command part
            font = QFont("Consolas", 11)
            item.setFont(font)
            
            self._slash_popup.addItem(item)
        
        # Select first item
        if self._slash_popup.count() > 0:
            self._slash_popup.setCurrentRow(0)

    def _show_slash_popup(self) -> None:
        """Show the slash command popup below the cursor."""
        if self._slash_popup.count() == 0:
            self._hide_slash_popup()
            return
        
        # Calculate position - above the prompt widget
        prompt_rect = self.ui.prompt.geometry()
        global_pos = self.ui.prompt.mapToGlobal(QPoint(0, 0))
        
        # Size the popup
        item_height = 28
        visible_items = min(self._slash_popup.count(), 12)
        popup_height = visible_items * item_height + 4
        popup_width = 450
        
        # Position above the prompt
        popup_x = global_pos.x()
        popup_y = global_pos.y() - popup_height - 5
        
        self._slash_popup.setGeometry(popup_x, popup_y, popup_width, popup_height)
        self._slash_popup.show()
        self._slash_popup.raise_()
        self._set_slash_navigation_shortcuts_enabled(True)

    def _check_slash_command_trigger(self) -> None:
        """Check if we should show the slash command popup."""
        if not hasattr(self, '_slash_popup'):
            return
            
        text = self.ui.prompt.toPlainText()
        
        if text.startswith("/"):
            # Get the partial command (everything after / until space or end)
            parts = text.split(" ", 1)
            partial_cmd = parts[0] if parts else "/"
            
            # Only show popup if still typing the command (no space yet)
            if len(parts) == 1:
                self._populate_slash_popup(partial_cmd)
                self._show_slash_popup()
            else:
                self._hide_slash_popup()
        else:
            self._hide_slash_popup()

    def _on_slash_item_clicked(self, item: QListWidgetItem) -> None:
        """Handle when a slash command is selected from the popup."""
        cmd = item.data(Qt.ItemDataRole.UserRole)
        
        # Get current text after the partial command
        current_text = self.ui.prompt.toPlainText()
        space_idx = current_text.find(" ")
        if space_idx > 0:
            rest = current_text[space_idx:]
        else:
            rest = " "
        
        # Set the new text
        self.ui.prompt.blockSignals(True)
        self.ui.prompt.setPlainText(cmd + rest)
        
        # Move cursor to end
        cursor = self.ui.prompt.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.ui.prompt.setTextCursor(cursor)
        self.ui.prompt.blockSignals(False)
        
        # Hide popup and update highlighting
        self._hide_slash_popup()
        self.highlight_slash_command(cmd + rest)
        
        # Focus back to prompt
        self.ui.prompt.setFocus()

    def _handle_slash_popup_navigation(self, key: int) -> bool:
        """Handle keyboard navigation in slash popup. Returns True if handled.
        
        Only intercepts navigation keys (Up/Down/Tab/Escape).
        All other keys pass through to allow normal typing.
        """
        if not hasattr(self, '_slash_popup') or not self._slash_popup.isVisible():
            return False
        
        if key == Qt.Key.Key_Up:
            current = self._slash_popup.currentRow()
            if current > 0:
                self._slash_popup.setCurrentRow(current - 1)
            return True
        elif key == Qt.Key.Key_Down:
            current = self._slash_popup.currentRow()
            if current < self._slash_popup.count() - 1:
                self._slash_popup.setCurrentRow(current + 1)
            return True
        elif key == Qt.Key.Key_Tab:
            # Tab selects the current item
            item = self._slash_popup.currentItem()
            if item:
                self._on_slash_item_clicked(item)
            return True
        elif key == Qt.Key.Key_Escape:
            self._hide_slash_popup()
            return True
        
        # Let all other keys pass through (including Enter - user might want to submit)
        # The popup will auto-hide if text no longer matches
        return False

    def _parse_slash_command(
        self,
        prompt: str,
    ) -> Tuple[Optional[str], str, Optional[LLMActionType], bool]:
        """Parse a slash command from the prompt.
        
        Args:
            prompt: The full prompt text
            
        Returns:
            Tuple of (command_name, remaining_prompt,
            action_type_override, is_project_template)
            - command_name: The slash command (e.g., "deepsearch") or None
            - remaining_prompt: The prompt with the command stripped
            - action_type_override: Optional LLMActionType to use instead of AUTO
        """
        if not prompt.startswith("/"):
            return None, prompt, None, False
        
        parts = prompt[1:].split(" ", 1)
        command = parts[0].lower()
        self._refresh_slash_commands_data()
        remaining = parts[1].strip() if len(parts) > 1 else ""
        if command in RETIRED_SLASH_COMMANDS:
            return None, prompt, None, False
        if command in SLASH_COMMANDS:
            cmd_config = SLASH_COMMANDS[command]
            action_override = None
            if "action" in cmd_config:
                action_name = cmd_config["action"]
                try:
                    action_override = LLMActionType[action_name]
                except KeyError:
                    self.logger.warning(
                        "Unknown action type in slash command: %s",
                        action_name,
                    )
            return command, remaining, action_override, False

        if command in getattr(self, "_project_slash_templates", {}):
            return command, remaining, None, True

        return None, prompt, None, False

    def _refresh_slash_commands_data(self) -> None:
        """Load slash-command metadata for built-in commands only."""
        self._project_slash_templates = {}
        self._slash_commands_data = []
        for cmd, config in SLASH_COMMANDS.items():
            self._slash_commands_data.append(
                {
                    "command": f"/{cmd}",
                    "description": config.get("description", ""),
                }
            )

    def _update_token_count_label(self, prompt: str) -> None:
        """Refresh the token count label with the latest approximation."""
        if not hasattr(self.ui, "token_count"):
            return
        token_count = self._estimate_token_count(prompt)
        self._set_token_count_label(token_count, self._model_context_tokens)

    def _estimate_token_count(self, prompt: str) -> int:
        """Estimate the number of tokens the current prompt will consume."""
        if not prompt:
            return 0
        try:
            return count_tokens_approximately(prompt)
        except Exception as exc:  # pragma: no cover - defensive fallback
            self.logger.debug("Token estimation failed: %s", exc)
            return (len(prompt) + 3) // 4

    @staticmethod
    def _safe_attachment_file_size(file_path: str) -> int:
        """Return one best-effort file size for attachment metadata."""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def _capability_total(
        capabilities: List[Dict[str, object]],
        key: str,
    ) -> int:
        """Return one integer total across attachment capabilities."""
        total = 0
        for capability in capabilities:
            total += int(capability.get(key, 0) or 0)
        return total

    def _document_attachment_roots(self) -> Optional[Tuple[str, ...]]:
        """Return approved roots for attachment capability scans."""
        roots = [
            root
            for root in (
                getattr(self, "documents_path", None),
                getattr(self, "ebook_path", None),
                getattr(self, "webpages_path", None),
                getattr(self, "zim_path", None),
            )
            if root
        ]
        return tuple(roots) or None

    def _resolve_document_attachment_capability_path(
        self,
        file_path: str,
    ) -> Optional[str]:
        """Return one validated attachment path for capability scans."""
        try:
            return resolve_existing_file(
                file_path,
                label="Attached document path",
                allowed_suffixes=KNOWLEDGE_BASE_DOCUMENT_SUFFIXES,
                allowed_roots=ChatPromptWidget._document_attachment_roots(
                    self
                ),
            )
        except PathPolicyError as exc:
            self.logger.debug(
                "Skipped attachment capability scan for %s: %s",
                file_path,
                exc,
            )
            return None

    def _extract_document_attachment_text(self, file_path: str) -> str:
        """Return extracted text for one attached document, if available."""
        try:
            return extract_text_from_file(file_path) or ""
        except Exception as exc:
            self.logger.debug(
                "Attachment capability scan failed for %s: %s",
                file_path,
                exc,
            )
            return ""

    def _document_attachment_capability_payload(
        self,
        file_path: str,
        text: str,
    ) -> Dict[str, object]:
        """Build one planner capability payload for an attached file."""
        tokens = self._estimate_token_count(text)
        characters = len(text)
        context_limit = getattr(self, "_model_context_tokens", None) or 0
        return {
            "path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": ChatPromptWidget._safe_attachment_file_size(
                file_path
            ),
            "estimated_tokens": tokens,
            "estimated_characters": characters,
            "text_available": bool(text),
            "fits_current_context": bool(
                context_limit and tokens <= context_limit
            ),
        }

    def _build_document_attachment_capability(
        self,
        file_path: str,
    ) -> Optional[Dict[str, object]]:
        """Build planner metadata for one attached document."""
        resolved = (
            ChatPromptWidget._resolve_document_attachment_capability_path(
                self,
                file_path,
            )
        )
        if not resolved:
            return None
        text = ChatPromptWidget._extract_document_attachment_text(
            self,
            resolved,
        )
        return ChatPromptWidget._document_attachment_capability_payload(
            self,
            resolved,
            text,
        )

    def _build_document_attachment_capabilities(
        self,
        file_paths: List[str],
    ) -> List[Dict[str, object]]:
        """Build planner metadata for the current attached documents."""
        capabilities: List[Dict[str, object]] = []
        for file_path in file_paths:
            capability = ChatPromptWidget._build_document_attachment_capability(
                self,
                file_path,
            )
            if capability is not None:
                capabilities.append(capability)
        return capabilities

    def _populate_request_document_capabilities(
        self,
        llm_request: LLMRequest,
        file_paths: List[str],
    ) -> None:
        """Attach planner-facing document capability metadata to a request."""
        capabilities = ChatPromptWidget._build_document_attachment_capabilities(
            self,
            file_paths,
        )
        llm_request.attached_document_capabilities = capabilities
        llm_request.attached_document_total_tokens = (
            ChatPromptWidget._capability_total(
                capabilities,
                "estimated_tokens",
            )
        )
        llm_request.attached_document_total_characters = (
            ChatPromptWidget._capability_total(
                capabilities,
                "estimated_characters",
            )
        )

    def _set_token_count_label(
        self, token_count: int, context_limit: Optional[int]
    ) -> None:
        """Apply a consistent, human-friendly label value."""
        if not hasattr(self.ui, "token_count"):
            return
        if context_limit and context_limit > 0:
            remaining = max(context_limit - token_count, 0)
            self.ui.token_count.setText(
                f"~{token_count:,} tokens ({remaining:,} remain)"
            )
        else:
            self.ui.token_count.setText(f"~{token_count:,} tokens")

    def _update_token_tracking_labels(self) -> None:
        """Update the sent/received token tracking labels."""
        if hasattr(self.ui, "last_message_tokens"):
            self.ui.last_message_tokens.setText(
                f"Last: ↑{self._tokens_sent_last:,} ↓{self._tokens_received_last:,}"
            )
        if hasattr(self.ui, "total_tokens"):
            self.ui.total_tokens.setText(
                f"Total: ↑{self._tokens_sent_total:,} ↓{self._tokens_received_total:,}"
            )

    def _resolve_model_context_length(self) -> Optional[int]:
        settings = getattr(self, "llm_generator_settings", None)
        if not settings:
            return None

        model_service = getattr(settings, "model_service", None)
        model_version = getattr(settings, "model_version", "") or ""
        model_path = getattr(settings, "model_path", "") or ""

        if model_service == ModelService.LOCAL.value:
            context = self._lookup_local_model_context(model_version)
            if context is not None:
                return context
            return self._lookup_local_model_context(model_path)

        return None

    def _lookup_local_model_context(self, source: str) -> Optional[int]:
        if not source:
            return None
        normalized_source = str(source).strip().lower()
        if not normalized_source:
            return None

        for model_info in LLMProviderConfig.LOCAL_MODELS.values():
            name = (model_info.get("name") or "").strip().lower()
            repo_id = (model_info.get("repo_id") or "").strip().lower()

            if name and (
                normalized_source == name
                or name in normalized_source
                or normalized_source in name
            ):
                return model_info.get("context_length")
            if repo_id and (
                normalized_source == repo_id
                or repo_id in normalized_source
                or normalized_source in repo_id
            ):
                return model_info.get("context_length")

        return None

    def _model_supports_thinking(self) -> bool:
        """Check if the current model supports thinking mode.
        
        Only Qwen3 models support the enable_thinking parameter with
        <think>...</think> reasoning blocks.
        
        Returns:
            True if the model supports thinking mode, False otherwise.
        """
        settings = getattr(self, "llm_generator_settings", None)
        if not settings:
            return False

        model_service = getattr(settings, "model_service", None)
        model_version = getattr(settings, "model_version", "") or ""
        model_path = getattr(settings, "model_path", "") or ""

        if model_service == ModelService.LOCAL.value:
            # Check model_version first (e.g., "qwen3.5-9b")
            if self._lookup_model_supports_thinking(model_version):
                return True
            # Fall back to model_path (e.g., "Qwen/Qwen3.5-9B" or local path)
            return self._lookup_model_supports_thinking(model_path)

        return False

    def _lookup_model_supports_thinking(self, source: str) -> bool:
        """Look up whether a model source supports thinking mode.
        
        Args:
            source: Model identifier (name, repo_id, or path)
            
        Returns:
            True if the model supports thinking, False otherwise.
        """
        if not source:
            return False
        normalized_source = str(source).strip().lower()
        if not normalized_source:
            return False

        # Check LLMProviderConfig.LOCAL_MODELS
        for model_info in LLMProviderConfig.LOCAL_MODELS.values():
            name = (model_info.get("name") or "").strip().lower()
            repo_id = (model_info.get("repo_id") or "").strip().lower()

            if name and (
                normalized_source == name
                or name in normalized_source
                or normalized_source in name
            ):
                return model_info.get("supports_thinking", False)
            if repo_id and (
                normalized_source == repo_id
                or repo_id in normalized_source
                or normalized_source in repo_id
            ):
                return model_info.get("supports_thinking", False)

        # Fallback: Check for "qwen3" in the source name (covers custom paths)
        if "qwen3" in normalized_source:
            return True

        return False

    def _model_supports_reasoning_effort(self) -> bool:
        """Return True when the current model exposes GPT-OSS effort modes."""
        settings = getattr(self, "llm_generator_settings", None)
        if not settings:
            return False

        model_version = getattr(settings, "model_version", "") or ""
        model_path = getattr(settings, "model_path", "") or ""
        model_id = getattr(settings, "model_id", "") or ""

        return any(
            self._lookup_model_supports_reasoning_effort(source)
            for source in (model_id, model_version, model_path)
            if source
        )

    def _lookup_model_supports_reasoning_effort(self, source: str) -> bool:
        """Look up whether one model source supports GPT-OSS effort modes."""
        normalized_source = str(source or "").strip().lower()
        if not normalized_source:
            return False

        for model_info in LLMProviderConfig.LOCAL_MODELS.values():
            aliases = [
                model_info.get("name", ""),
                model_info.get("repo_id", ""),
                model_info.get("gguf_filename", ""),
            ]
            if any(
                alias
                and (
                    normalized_source == str(alias).strip().lower()
                    or str(alias).strip().lower() in normalized_source
                    or normalized_source in str(alias).strip().lower()
                )
                for alias in aliases
            ):
                return bool(
                    model_info.get("supports_reasoning_effort", False)
                )

        return "gpt-oss" in normalized_source

    def _get_model_capabilities(self) -> Dict[str, bool]:
        """Get the capabilities of the current model.
        
        Returns a dict with capability flags:
        - function_calling: Can use tools/functions
        - supports_thinking: Has thinking mode (<think>...</think>)
        - rag_capable: Optimized for RAG workflows
        - vision_capable: Can process images
        - code_capable: Good at code generation
        
        Returns:
            Dict with capability flags, defaults to conservative values.
        """
        default_caps = {
            "function_calling": False,
            "supports_thinking": False,
            "rag_capable": True,  # Most models can do basic RAG
            "vision_capable": False,
            "code_capable": False,
        }
        
        settings = getattr(self, "llm_generator_settings", None)
        if not settings:
            return default_caps

        model_service = getattr(settings, "model_service", None)
        model_version = getattr(settings, "model_version", "") or ""
        model_path = getattr(settings, "model_path", "") or ""

        if model_service == ModelService.LOCAL.value:
            # Check model_version first, then model_path
            caps = self._lookup_model_capabilities(model_version)
            if caps is not None:
                return caps
            caps = self._lookup_model_capabilities(model_path)
            if caps is not None:
                return caps

        return default_caps

    def _lookup_model_capabilities(self, source: str) -> Optional[Dict[str, bool]]:
        """Look up model capabilities from LLMProviderConfig.
        
        Args:
            source: Model identifier (name, repo_id, or path)
            
        Returns:
            Dict with capability flags or None if not found.
        """
        if not source:
            return None
        normalized_source = str(source).strip().lower()
        if not normalized_source:
            return None

        for model_info in LLMProviderConfig.LOCAL_MODELS.values():
            name = (model_info.get("name") or "").strip().lower()
            repo_id = (model_info.get("repo_id") or "").strip().lower()

            matched = False
            if name and (
                normalized_source == name
                or name in normalized_source
                or normalized_source in name
            ):
                matched = True
            elif repo_id and (
                normalized_source == repo_id
                or repo_id in normalized_source
                or normalized_source in repo_id
            ):
                matched = True

            if matched:
                return {
                    "function_calling": model_info.get("function_calling", False),
                    "supports_thinking": model_info.get("supports_thinking", False),
                    "rag_capable": model_info.get("rag_capable", True),
                    "vision_capable": model_info.get("vision_capable", False),
                    "code_capable": model_info.get("code_capable", False),
                }

        return None

    def _update_action_dropdown(self) -> None:
        """Deprecated - action is always AUTO now."""
        pass

    def _update_thinking_checkbox_visibility(self) -> None:
        """Update footer reasoning controls for the current model."""
        supports_reasoning_effort = self._model_supports_reasoning_effort()

        if hasattr(self.ui, "thinking_checkbox"):
            self.ui.thinking_checkbox.setVisible(False)

        if hasattr(self.ui, "reasoning_effort_dropdown"):
            if supports_reasoning_effort:
                self._populate_reasoning_effort_dropdown()
            self.ui.reasoning_effort_dropdown.setVisible(
                supports_reasoning_effort
            )

    def _refresh_model_context_tokens(self) -> None:
        self._model_context_tokens = self._resolve_model_context_length()

    def on_llm_model_changed(self, data: Dict):
        self._refresh_model_context_tokens()
        self._update_thinking_checkbox_visibility()
        self._update_action_dropdown()
        self._update_attach_button_visibility()
        prompt_text = (
            self.ui.prompt.toPlainText().strip()
            if hasattr(self.ui, "prompt")
            else self.prompt
        )
        self._update_token_count_label(prompt_text)

    def on_application_settings_changed(self, data: Dict):
        if (
            not isinstance(data, dict)
            or data.get("setting_name") != "llm_generator_settings"
        ):
            return

        column = data.get("column_name")
        if column in {"model_version", "model_service", "model_path"}:
            self._populate_model_dropdown()
            self._refresh_model_context_tokens()
            self._update_thinking_checkbox_visibility()
            self._update_action_dropdown()
            self._update_attach_button_visibility()
            prompt_text = (
                self.ui.prompt.toPlainText().strip()
                if hasattr(self.ui, "prompt")
                else self.prompt
            )
            self._update_token_count_label(prompt_text)
            return

        if column == "reasoning_effort":
            self._populate_reasoning_effort_dropdown()
            return

    def clear_prompt(self):
        self.prompt = ""
        self.ui.prompt.setPlainText("")
        if hasattr(self, "_slash_popup") and self._slash_popup.isVisible():
            self._hide_slash_popup()

    def start_progress_bar(self):
        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)

    def stop_progress_bar(self):
        self.ui.progressBar.setRange(0, 1)
        self.ui.progressBar.setValue(1)
        self.ui.progressBar.reset()

    def disable_send_button(self):
        self._disabled = True

    def enable_send_button(self):
        send_button = getattr(getattr(self, "ui", None), "send_button", None)
        if send_button is not None:
            send_button.setEnabled(True)
        self._disabled = False

    def hide_action_menu(self):
        self.action_menu_displayed = False
        self.ui.action_menu.hide()

    def display_action_menu(self):
        self.action_menu_displayed = True
        self.ui.action_menu.show()

    def insert_newline(self):
        self.ui.prompt.insertPlainText("\n")

    def message_type_text_changed(self, val):
        self.update_llm_generator_settings(message_type=val)

    def on_add_bot_message_to_conversation(self, data: Dict):
        llm_response = data.get("response", None)
        if llm_response is None:
            return
            
        # Track received tokens from streaming response
        message = getattr(llm_response, "message", "") or ""
        if message:
            chunk_tokens = self._estimate_token_count(message)
            self._current_response_tokens += chunk_tokens
        
        # Update labels when response is complete
        if getattr(llm_response, "is_end_of_message", False):
            self._tokens_received_last = self._current_response_tokens
            self._tokens_received_total += self._current_response_tokens
            self._update_token_tracking_labels()
        
        if getattr(llm_response, "is_first_message", False):
            pending_request_ids = getattr(
                self,
                "_pending_model_loading_request_ids",
                set(),
            )
            clear_loading = getattr(
                self,
                "_clear_model_loading_indicators",
                None,
            )
            response_request_id = getattr(llm_response, "request_id", None)
            if response_request_id and callable(clear_loading):
                clear_loading(response_request_id)
            elif len(pending_request_ids) == 1 and callable(clear_loading):
                clear_loading(next(iter(pending_request_ids)))
            self.stop_progress_bar()

        if getattr(llm_response, "is_end_of_message", False):
            self.enable_generate()

    def on_llm_text_generate_request_signal(self, data: Dict):
        """Handle LLM text generate request signal - user message is being sent."""
        self.logger.debug(
            "LLM_TEXT_GENERATE_REQUEST_SIGNAL received (%s)",
            summarize_mapping_keys(data, label="request"),
        )
        # The ConversationWidget should handle displaying the message
        # This handler is just for logging/debugging

    def load_conversation(self, conversation_id: int = None):
        """Load a conversation and synchronize with ConversationWidget."""
        if conversation_id is None:
            # Try to load the current conversation first, fall back to most recent
            current_conversation = (
                self._conversation_history_manager.get_current_conversation()
            )
            if current_conversation:
                conversation_id = current_conversation.id
            else:
                conversation_id = (
                    self._conversation_history_manager.get_most_recent_conversation_id()
                )
        if conversation_id is None:
            if hasattr(self.ui, "conversation"):
                self.ui.conversation.clear_conversation()
            self.conversation = None
            self.conversation_id = None
            self._set_api_conversation_id(None)
            return
        self.conversation_id = conversation_id
        self._set_api_conversation_id(conversation_id)

        conversation = Conversation.objects.filter_by_first(id=conversation_id)
        self.conversation = conversation
        if hasattr(self.api, "llm") and hasattr(self.api.llm, "clear_history"):
            self.api.llm.clear_history(conversation_id=conversation_id)
        messages = (
            self._conversation_history_manager.load_conversation_history(
                conversation_id=conversation_id, max_messages=50
            )
        )
        self.logger.debug(
            f"Loaded {len(messages)} messages from conversation {conversation_id}"
        )
        for idx, msg in enumerate(messages):
            self.logger.debug(
                f"Message {idx}: is_bot={msg.get('is_bot')}, content_preview={msg.get('content', '')[:50]}"
            )

        if hasattr(self.ui, "conversation"):
            self.ui.conversation.conversation = conversation
            self.ui.conversation.set_conversation_widgets(messages)

    def on_queue_load_conversation(self, data):
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def on_delete_conversation(self, data):
        deleted_id = data.get("conversation_id")
        if self.conversation_id == deleted_id:
            if hasattr(self.ui, "conversation"):
                self.ui.conversation.clear_conversation()
            self.conversation = None
            self.conversation_id = None
            self._set_api_conversation_id(None)

    def _clear_conversation(self, skip_update: bool = False):
        del skip_update
        pass

    def _set_conversation_widgets(self, messages, skip_scroll: bool = False):
        del messages, skip_scroll
        pass

    def _clear_conversation_widgets(self, skip_update: bool = False):
        del skip_update
        pass

    def add_message_to_conversation(self, *args, **kwargs):
        pass

    def on_mood_summary_update_started(self, *args, **kwargs):
        pass

    def _handle_mood_summary_update_started(self, *args, **kwargs):
        pass

    def register_web_channel(self, channel):
        del channel
        pass

    def _ensure_conversation_context(self) -> Optional[int]:
        """Ensure we have a valid conversation ID before sending a request."""
        if self.conversation_id is not None:
            return self.conversation_id

        conversation = (
            self._conversation_history_manager.get_current_conversation()
        )
        if conversation is not None:
            self.conversation = conversation
            self.conversation_id = conversation.id
            self._set_api_conversation_id(conversation.id)
            return self.conversation_id

        conversation = Conversation.create()
        if conversation is None:
            self.logger.error("Failed to create a new conversation")
            return None

        Conversation.make_current(conversation.id)
        self.conversation = conversation
        self.conversation_id = conversation.id
        self._set_api_conversation_id(conversation.id)
        if hasattr(self.ui, "conversation"):
            self.ui.conversation.clear_conversation()
        return conversation.id

    def _set_api_conversation_id(self, conversation_id: Optional[int]) -> None:
        api = getattr(self, "api", None)
        if api is not None:
            setattr(api, "current_conversation_id", conversation_id)

    def _populate_model_dropdown(self) -> None:
        """Populate the model dropdown with available models for current provider."""
        if not hasattr(self.ui, "model_dropdown"):
            return
        
        self.ui.model_dropdown.blockSignals(True)
        self.ui.model_dropdown.clear()
        
        # Get current provider from dropdown or settings
        provider = self._current_model_service()
        
        # Make dropdown editable for custom model entry
        self.ui.model_dropdown.setEditable(True)
        self.ui.model_dropdown.setInsertPolicy(self.ui.model_dropdown.InsertPolicy.NoInsert)
        
        # Get models based on provider
        if provider == ModelService.LOCAL.value:
            # HuggingFace/Local models - show from LOCAL_MODELS config
            models = LLMProviderConfig.get_models_for_provider("local")
            for model_id in models:
                if model_id == "custom":
                    continue
                model_info = LLMProviderConfig.get_model_info("local", model_id)
                if model_info:
                    display_name = model_info.get("name", model_id)
                    self.ui.model_dropdown.addItem(display_name, model_id)
            
            # Add custom option at end
            self.ui.model_dropdown.addItem("-- Custom Path --", "custom")
            
        elif provider == ModelService.OLLAMA.value:
            # Ollama models
            models = LLMProviderConfig.get_models_for_provider("ollama")
            for model_id in models:
                if model_id == "custom":
                    continue
                self.ui.model_dropdown.addItem(model_id, model_id)
            
            # Add custom option
            self.ui.model_dropdown.addItem("-- Custom Model --", "custom")
            
        elif provider == ModelService.OPENROUTER.value:
            # OpenRouter models
            models = LLMProviderConfig.get_models_for_provider("openrouter")
            for model_id in models:
                if model_id == "custom":
                    continue
                self.ui.model_dropdown.addItem(model_id, model_id)
            
            # Add custom option
            self.ui.model_dropdown.addItem("-- Custom Model --", "custom")
        
        # Try to restore current selection
        self._restore_model_selection(provider)

        self._connect_model_dropdown_line_edit()
        
        self.ui.model_dropdown.blockSignals(False)

    def _connect_model_dropdown_line_edit(self) -> None:
        """Connect custom model entry once the combo box has a line edit."""
        line_edit = self.ui.model_dropdown.lineEdit()
        if line_edit is None or line_edit is self._model_dropdown_line_edit:
            return
        self._model_dropdown_line_edit = line_edit
        line_edit.returnPressed.connect(self._on_custom_model_entered)
    
    def _restore_model_selection(self, provider: str) -> None:
        """Restore model selection based on saved settings."""
        # First try to match by saved model_id (most reliable)
        saved_model_id = getattr(self.llm_generator_settings, "model_id", None) or ""
        if saved_model_id:
            for i in range(self.ui.model_dropdown.count()):
                item_model_id = self.ui.model_dropdown.itemData(i)
                if item_model_id == saved_model_id:
                    self.ui.model_dropdown.setCurrentIndex(i)
                    if provider == ModelService.LOCAL.value:
                        self._update_model_tooltip(saved_model_id)
                        
                        # Verify model_path is correct - rebuild if corrupted
                        current_path = getattr(self.llm_generator_settings, "model_path", "") or ""
                        # Check for corrupted paths (TTS/SD/art model paths)
                        invalid_patterns = ["/tts/", "/openvoice", "/art/models/", "/txt2img", "/inpaint"]
                        is_corrupted = not current_path or any(pattern in current_path for pattern in invalid_patterns)
                        if is_corrupted:
                            # Path is missing or corrupted - rebuild from model_id
                            model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
                            if model_info:
                                model_name = model_info.get("name", saved_model_id)
                                correct_path = self._get_local_model_storage_path(
                                    saved_model_id,
                                    str(model_info.get("repo_id", "")),
                                )
                                self.logger.info(
                                    f"Rebuilding corrupted model_path from model_id '{saved_model_id}': {correct_path}"
                                )
                                self.update_llm_generator_settings(
                                    model_path=correct_path,
                                    model_version=model_name,
                                )
                    return
        
        # Fallback: try to match by model path or version
        if provider == ModelService.LOCAL.value:
            # For HuggingFace, match by model path
            current_path = getattr(self.llm_generator_settings, "model_path", "") or ""
            if current_path:
                # Check for corrupted path (TTS/SD/art model paths should not be in LLM settings)
                invalid_patterns = ["/tts/", "/openvoice", "/art/models/", "/txt2img", "/inpaint"]
                is_corrupted = any(pattern in current_path for pattern in invalid_patterns)
                if is_corrupted:
                    self.logger.warning(
                        f"Detected corrupted LLM model_path: {current_path}. "
                        "Attempting to recover from model_id..."
                    )
                    # Try to recover from model_id first
                    if saved_model_id and saved_model_id != "custom":
                        model_info = LLMProviderConfig.get_model_info("local", saved_model_id)
                        if model_info:
                            model_name = model_info.get("name", saved_model_id)
                            correct_path = self._get_local_model_storage_path(
                                saved_model_id,
                                str(model_info.get("repo_id", "")),
                            )
                            self.logger.info(f"Recovered corrupted model_path to: {correct_path}")
                            self.update_llm_generator_settings(
                                model_path=correct_path,
                                model_version=model_name,
                            )
                            return
                    # No recovery possible - clear the corrupted path
                    self.update_llm_generator_settings(model_path="")
                    return
                    
                for i in range(self.ui.model_dropdown.count()):
                    model_id = self.ui.model_dropdown.itemData(i)
                    if model_id == "custom":
                        continue
                    model_info = LLMProviderConfig.get_model_info("local", model_id)
                    if model_info:
                        model_name = model_info.get("name", "")
                        expected_path = self._get_local_model_storage_path(
                            model_id,
                            str(model_info.get("repo_id", "")),
                        )
                        normalized_current = os.path.normpath(current_path)
                        normalized_expected = os.path.normpath(expected_path)
                        if model_name and (
                            model_name in current_path
                            or normalized_current == normalized_expected
                            or normalized_current.startswith(
                                normalized_expected + os.sep
                            )
                        ):
                            self.ui.model_dropdown.setCurrentIndex(i)
                            self._update_model_tooltip(model_id)
                            return
            self._select_and_save_default_model(provider)
        else:
            # For Ollama/OpenRouter, match by model_version
            current_model = getattr(self.llm_generator_settings, "model_version", "") or ""
            if current_model:
                for i in range(self.ui.model_dropdown.count()):
                    model_id = self.ui.model_dropdown.itemData(i)
                    if model_id == current_model or self.ui.model_dropdown.itemText(i) == current_model:
                        self.ui.model_dropdown.setCurrentIndex(i)
                        return
                # If not found in list, it might be custom - set as text
                self.ui.model_dropdown.setEditText(current_model)
                return

            self._select_and_save_default_model(provider)

    def _select_and_save_default_model(self, provider: str) -> None:
        """Select and save the first available model as default.
        
        Called when corrupted settings are detected to auto-recover.
        
        Args:
            provider: Current provider (local, ollama, openrouter)
        """
        if provider == ModelService.LOCAL.value:
            # Find the first non-custom model
            for i in range(self.ui.model_dropdown.count()):
                model_id = self.ui.model_dropdown.itemData(i)
                if model_id and model_id != "custom":
                    # Select in dropdown
                    self.ui.model_dropdown.setCurrentIndex(i)
                    self._update_model_tooltip(model_id)
                    
                    # Build the correct path and save to settings
                    model_info = LLMProviderConfig.get_model_info("local", model_id)
                    if model_info:
                        model_name = model_info.get("name", model_id)
                        model_path = self._get_local_model_storage_path(
                            model_id,
                            str(model_info.get("repo_id", "")),
                        )
                        
                        # Save to database
                        self.update_llm_generator_settings(
                            model_path=model_path,
                            model_version=model_name,
                            model_id=model_id,
                        )
                        self.logger.info(f"Auto-selected default model: {model_id} ({model_path})")
                    return
        else:
            # For remote providers, select first non-custom model
            for i in range(self.ui.model_dropdown.count()):
                model_id = self.ui.model_dropdown.itemData(i)
                if model_id and model_id != "custom":
                    self.ui.model_dropdown.setCurrentIndex(i)
                    self.update_llm_generator_settings(
                        model_version=model_id,
                        model_path="",
                        model_id=model_id,
                    )
                    self.logger.info(f"Auto-selected default model: {model_id}")
                    return

    def _update_model_tooltip(self, model_id: str) -> None:
        """Update the model dropdown tooltip with model metadata."""
        if not hasattr(self.ui, "model_dropdown"):
            return

        provider = self._current_model_service()
        
        if model_id == "custom":
            if provider == ModelService.LOCAL.value:
                self.ui.model_dropdown.setToolTip("Enter a custom model path or HuggingFace repo ID")
            elif provider == ModelService.OLLAMA.value:
                self.ui.model_dropdown.setToolTip("Enter any Ollama model name (e.g., llama3.2:latest)")
            else:
                self.ui.model_dropdown.setToolTip("Enter any OpenRouter model ID (e.g., anthropic/claude-3-sonnet)")
            return
        
        if provider == ModelService.LOCAL.value:
            # HuggingFace models - show full metadata
            model_info = LLMProviderConfig.get_model_info("local", model_id)
            if not model_info:
                self.ui.model_dropdown.setToolTip("Select LLM model")
                return
            
            vram_gb = model_info.get("vram_4bit_gb", "?")
            context_length = model_info.get("context_length", 0)
            context_k = f"{context_length // 1000}K" if context_length >= 1000 else str(context_length)
            
            tool_mode = model_info.get("tool_calling_mode", "none")
            tool_str = tool_mode.upper() if tool_mode != "none" else "None"
            
            gguf_file = model_info.get("gguf_filename", "")
            gguf_str = gguf_file if gguf_file else "Not available"
            
            description = model_info.get("description", "")
            
            tooltip = f"~{vram_gb}GB VRAM | {context_k} context | Tools: {tool_str}\n"
            tooltip += f"GGUF: {gguf_str}"
            if description:
                tooltip += f"\n{description}"
            
            self.ui.model_dropdown.setToolTip(tooltip)
            
        elif provider == ModelService.OLLAMA.value:
            # Ollama - simpler tooltip
            self.ui.model_dropdown.setToolTip(f"Ollama model: {model_id}\nRequires Ollama running locally")
            
        elif provider == ModelService.OPENROUTER.value:
            # OpenRouter - show model ID
            self.ui.model_dropdown.setToolTip(f"OpenRouter model: {model_id}\nRequires OpenRouter API key")

    def _get_local_model_storage_path(
        self,
        model_id: str,
        repo_id: str = "",
    ) -> str:
        """Return the expected local artifact path for one local model."""
        base_path = os.path.expanduser(
            getattr(self.path_settings, "base_path", "~/.local/share/airunner")
        )
        return LLMProviderConfig.get_expected_local_artifact_path(
            base_path,
            "local",
            model_id=model_id,
            repo_id=repo_id,
        )

    def _emit_llm_model_changed_signal(
        self,
        model_path: str,
        model_name: str,
    ) -> None:
        """Emit a UI-only LLM model change notification."""
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED,
            {
                "model_path": model_path,
                "model_name": model_name,
                "reload_runtime": False,
            },
        )

    @Slot(int)
    def on_model_changed(self, index: int) -> None:
        """Handle model selection change from dropdown."""
        if index < 0:
            return
        
        model_id = self.ui.model_dropdown.itemData(index)
        model_text = self.ui.model_dropdown.currentText()
        
        # Get current provider
        provider = self._current_model_service()
        
        # Handle custom model entry
        if model_id == "custom" or not model_id:
            # User is entering custom model - use the text they typed
            custom_model = model_text if model_text and not model_text.startswith("--") else ""
            if custom_model:
                self._handle_custom_model(provider, custom_model)
            return
        
        # Update tooltip with model metadata
        self._update_model_tooltip(model_id)
        
        if provider == ModelService.LOCAL.value:
            # HuggingFace/Local model
            model_info = LLMProviderConfig.get_model_info("local", model_id)
            if not model_info:
                return
            
            model_name = model_info.get("name", model_id)
            model_path = self._get_local_model_storage_path(
                model_id,
                str(model_info.get("repo_id", "")),
            )
            
            self.update_llm_generator_settings(
                model_path=model_path,
                model_version=model_name,
                model_id=model_id,  # Save the provider config model ID
            )

            self._emit_llm_model_changed_signal(model_path, model_name)
        else:
            # Ollama or OpenRouter - just update model_version
            self.update_llm_generator_settings(
                model_version=model_id,
                model_path="",  # Not used for remote providers
                model_id=model_id,  # Save the model ID
            )

            self._emit_llm_model_changed_signal("", model_id)
        
        # Update thinking checkbox visibility based on new model
        self._update_thinking_checkbox_visibility()
        
        # Update context tokens
        self._refresh_model_context_tokens()
        
    def _get_model_native_precision(self) -> str:
        """Determine the native precision of the currently selected model.
        
        Checks the model's config.json for torch_dtype or other indicators.
        Falls back to bfloat16 if unknown (most permissive).
        
        Returns:
            Native precision string (e.g., "bfloat16", "float16", "4bit")
        """
        model_path = getattr(self.llm_generator_settings, "model_path", "") or ""
        
        if not model_path or not os.path.exists(model_path):
            # No local model path - assume bfloat16 (most permissive)
            return "bfloat16"
        
        config_path = os.path.join(model_path, "config.json")
        if not os.path.exists(config_path):
            return "bfloat16"
        
        try:
            import json
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # Check torch_dtype in config
            torch_dtype = config.get("torch_dtype", "")
            if torch_dtype == "bfloat16":
                return "bfloat16"
            elif torch_dtype == "float16":
                return "float16"
            elif torch_dtype == "float32":
                # FP32 models can run at any precision
                return "bfloat16"
            
            # Check for pre-quantized models
            quantization_config = config.get("quantization_config", {})
            if quantization_config:
                quant_method = quantization_config.get("quant_method", "")
                if quant_method in ["bitsandbytes", "gptq", "awq"]:
                    bits = quantization_config.get("bits", 4)
                    if bits == 4:
                        return "4bit"
                    elif bits == 8:
                        return "8bit"
            
            # Default to bfloat16 if we can't determine
            return "bfloat16"
            
        except (json.JSONDecodeError, IOError, KeyError) as e:
            self.logger.warning(f"Failed to read model config: {e}")
            return "bfloat16"

    def _handle_custom_model(self, provider: str, custom_model: str) -> None:
        """Handle custom model entry for any provider."""
        if provider == ModelService.LOCAL.value:
            # Could be a path or HuggingFace repo ID
            resolved_model_id = LLMProviderConfig.resolve_model_id(
                "local",
                custom_model,
            )
            if resolved_model_id:
                model_info = LLMProviderConfig.get_model_info(
                    "local",
                    resolved_model_id,
                )
                model_name = model_info.get("name", resolved_model_id)
                model_path = self._get_local_model_storage_path(
                    resolved_model_id,
                    str(model_info.get("repo_id", custom_model)),
                )
            elif "/" in custom_model and not os.path.exists(custom_model):
                # Likely a HuggingFace repo ID
                base_path = os.path.expanduser(
                    getattr(self.path_settings, "base_path", "~/.local/share/airunner")
                )
                # Extract model name from repo ID (e.g., "mistralai/Mistral-7B" -> "Mistral-7B")
                model_name = custom_model.split("/")[-1]
                model_path = os.path.join(base_path, f"text/models/llm/causallm/{model_name}")
            else:
                # Assume it's a local path
                model_path = custom_model
                model_name = os.path.basename(custom_model)
            
            self.update_llm_generator_settings(
                model_path=model_path,
                model_version=model_name,
            )
            self._emit_llm_model_changed_signal(model_path, model_name)
        else:
            # Ollama or OpenRouter - just set the model name
            self.update_llm_generator_settings(
                model_version=custom_model,
                model_path="",
            )
            self._emit_llm_model_changed_signal("", custom_model)

    def _on_custom_model_entered(self) -> None:
        """Handle when user presses Enter after typing a custom model."""
        if not hasattr(self.ui, "model_dropdown"):
            return
        
        custom_text = self.ui.model_dropdown.currentText()
        if not custom_text or custom_text.startswith("--"):
            return
        
        # Check if this is already a known model
        for i in range(self.ui.model_dropdown.count()):
            if self.ui.model_dropdown.itemText(i) == custom_text:
                # It's a known model, don't treat as custom
                return
        
        # Get current provider
        provider = self._current_model_service()
        
        # Handle as custom model
        self._handle_custom_model(provider, custom_text)

    def _populate_reasoning_effort_dropdown(self) -> None:
        """Populate the GPT-OSS reasoning-effort selector."""
        if not hasattr(self.ui, "reasoning_effort_dropdown"):
            return

        dropdown = self.ui.reasoning_effort_dropdown
        dropdown.blockSignals(True)
        dropdown.clear()
        dropdown.addItem("Low", "low")
        dropdown.addItem("Med", "medium")
        dropdown.addItem("High", "high")

        current_effort = str(
            getattr(self.llm_generator_settings, "reasoning_effort", "medium")
            or "medium"
        ).strip().lower()
        if current_effort not in {"low", "medium", "high"}:
            current_effort = "medium"

        for index in range(dropdown.count()):
            if dropdown.itemData(index) == current_effort:
                dropdown.setCurrentIndex(index)
                break

        dropdown.blockSignals(False)

    @Slot(int)
    def on_reasoning_effort_changed(self, index: int) -> None:
        """Persist one GPT-OSS reasoning-effort selection."""
        if index < 0 or not hasattr(self.ui, "reasoning_effort_dropdown"):
            return

        effort = self.ui.reasoning_effort_dropdown.itemData(index)
        if effort not in {"low", "medium", "high"}:
            return

        self.update_llm_generator_settings(reasoning_effort=effort)

    def _current_model_service(self) -> str:
        """Return the current model-service setting used by the footer."""
        provider = getattr(
            self.llm_generator_settings,
            "model_service",
            ModelService.LOCAL.value,
        )
        provider = str(provider or ModelService.LOCAL.value).strip().lower()
        if provider in {
            ModelService.LOCAL.value,
            ModelService.OLLAMA.value,
            ModelService.OPENROUTER.value,
        }:
            return provider
        return ModelService.LOCAL.value

    def on_section_changed_signal(self, data: Dict) -> None:
        """Track the currently active main window section."""
        section = data.get("section")
        if section:
            self._active_section = section

    def _resolve_initial_section(self) -> Optional[str]:
        """Return the single remaining center-section identifier."""
        if AIRUNNER_ART_ENABLED:
            return "art_editor_button"
        return None

    # =========================================================================
    # Image Attachment Methods
    # =========================================================================

    def _setup_image_attachments(self) -> None:
        """Set up document and image attachment handling."""
        # Enable drag-drop on the prompt widget
        self.setAcceptDrops(True)
        if hasattr(self.ui, "prompt"):
            self.ui.prompt.setAcceptDrops(True)
            # Install event filter to handle drops on prompt
            self.ui.prompt.viewport().installEventFilter(self)
        
        # Connect attach button
        if hasattr(self.ui, "attach_button"):
            self.ui.attach_button.clicked.connect(self._on_attach_button_clicked)
            # Update visibility based on model capability
            self._update_attach_button_visibility()
        
        # Hide attachments container initially
        if hasattr(self.ui, "attachments_scroll_area"):
            self.ui.attachments_scroll_area.setVisible(False)
        
        # Add spacer to attachments layout
        if hasattr(self.ui, "attachments_layout"):
            self._attachments_spacer = QSpacerItem(
                40, 20,
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Minimum
            )
            self.ui.attachments_layout.addItem(self._attachments_spacer)

    def _update_attach_button_visibility(self) -> None:
        """Update attach button state and tooltip for available file types."""
        if not hasattr(self.ui, "attach_button"):
            return
        
        self.ui.attach_button.setEnabled(True)

        self.ui.attach_button.setToolTip("Attach documents for RAG")

    @property
    def documents_path(self) -> str:
        """Return the local document library used by the knowledge base."""
        configured = getattr(self.path_settings, "documents_path", None)
        if configured:
            return os.path.expanduser(configured)
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/documents",
        )

    @property
    def zim_path(self) -> str:
        """Return the local ZIM library used by the knowledge base."""
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "zim",
        )

    @property
    def ebook_path(self) -> str:
        """Return the local ebook library used by the knowledge base."""
        configured = getattr(self.path_settings, "ebook_path", None)
        if configured:
            return os.path.expanduser(configured)
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/ebooks",
        )

    @property
    def webpages_path(self) -> str:
        """Return the local webpage library used by the knowledge base."""
        configured = getattr(self.path_settings, "webpages_path", None)
        if configured:
            return os.path.expanduser(configured)
        return os.path.join(
            os.path.expanduser(self.path_settings.base_path),
            "text/other/webpages",
        )

    def _validate_knowledge_base_document_path(
        self,
        file_path: str,
        *,
        log_rejection: bool = True,
    ) -> Optional[str]:
        """Validate one existing knowledge-base document path."""
        try:
            return resolve_existing_file(
                file_path,
                label="Attached document path",
                allowed_suffixes=KNOWLEDGE_BASE_DOCUMENT_SUFFIXES,
                allowed_roots=(
                    self.documents_path,
                    self.ebook_path,
                    self.webpages_path,
                    self.zim_path,
                ),
            )
        except PathPolicyError as exc:
            if log_rejection:
                self.logger.warning(
                    "Rejected dropped document path: %s",
                    exc,
                )
            return None

    def _active_document_paths(self) -> List[str]:
        """Return active knowledge-base documents for prompt pills."""
        active_paths: List[str] = []
        seen: set[str] = set()
        for document in Document.objects.all():
            file_path = getattr(document, "path", None)
            if not getattr(document, "active", False) or not file_path:
                continue
            validated_path = self._validate_knowledge_base_document_path(
                file_path,
                log_rejection=False,
            )
            if not validated_path or validated_path in seen:
                continue
            seen.add(validated_path)
            active_paths.append(validated_path)
        return active_paths

    def _set_document_attachments(self, file_paths: List[str]) -> None:
        """Replace prompt document pills with one ordered path set."""
        unique_paths: List[str] = []
        seen: set[str] = set()
        for file_path in file_paths:
            if not file_path or file_path in seen:
                continue
            seen.add(file_path)
            unique_paths.append(file_path)

        if unique_paths == self._attached_documents:
            return

        for widget in self._document_attachment_widgets:
            widget.deleteLater()
        self._document_attachment_widgets.clear()
        self._attached_documents.clear()

        for file_path in unique_paths:
            self._add_document_attachment(file_path)

        self._update_attachments_visibility()

    def _sync_document_attachments_from_active_documents(self) -> None:
        """Sync prompt document pills from the active document set."""
        self._set_document_attachments(self._active_document_paths())

    def _attachment_file_dialog_filter(self) -> str:
        """Return the file dialog filter for the current attachment mode."""
        document_patterns = " ".join(
            f"*{suffix}" for suffix in rag_document_suffixes()
        )
        image_patterns = " ".join(
            f"*{suffix}" for suffix in chat_image_suffixes()
        )
        return (
            "Supported Attachments "
            f"({document_patterns} {image_patterns});;"
            f"Documents ({document_patterns});;"
            f"Images ({image_patterns});;"
            "All Files (*)"
        )

    @Slot()
    def _on_attach_button_clicked(self) -> None:
        """Open the attachment picker for RAG documents and images."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Files",
            "",
            self._attachment_file_dialog_filter(),
        )

        self._handle_selected_attachment_paths(file_paths)

    def _handle_selected_attachment_paths(
        self,
        file_paths: List[str],
    ) -> None:
        """Attach supported document and image paths for one chat request."""
        for file_path in file_paths:
            if is_rag_document_path(file_path):
                self._add_document_attachment_from_path(file_path)
                continue

            self.logger.warning(
                "Skipped unsupported attachment path: %s",
                file_path,
            )

    def _add_document_attachment_from_path(self, file_path: str) -> None:
        """Import one document into the local library and attach it."""
        try:
            imported_path = import_document_to_library(
                file_path,
                self.documents_path,
            )
        except Exception as exc:
            self.logger.error(
                "Failed to attach document from %s: %s",
                file_path,
                exc,
            )
            return

        self._attach_knowledge_base_document(imported_path)

    def _add_document_attachment(self, file_path: str) -> None:
        """Attach one imported document path to the current chat request."""
        if file_path in self._attached_documents:
            return

        self._attached_documents.append(file_path)
        widget = ChatAttachmentPillWidget(
            os.path.basename(file_path),
            tooltip=file_path,
            parent=self,
        )
        widget.removed.connect(
            lambda: self._remove_document_attachment(widget, file_path)
        )
        self._document_attachment_widgets.append(widget)
        self._add_attachment_widget(widget)

    def _attach_knowledge_base_document(self, file_path: str) -> None:
        """Attach one existing knowledge-base document and mark it active."""
        validated_path = self._validate_knowledge_base_document_path(
            file_path
        )
        if not validated_path:
            return

        docs = Document.objects.filter_by(path=validated_path)
        if docs:
            Document.objects.update(pk=docs[0].id, active=True)
        else:
            Document.objects.create(
                path=validated_path,
                active=True,
                indexed=False,
            )

        self._add_document_attachment(validated_path)
        self.emit_signal(
            SignalCode.DOCUMENT_COLLECTION_CHANGED,
            {"paths": [validated_path]},
        )

    def _remove_document_attachment(
        self,
        widget: ChatAttachmentPillWidget,
        file_path: str,
    ) -> None:
        """Detach one document and deactivate it in the knowledge base."""
        if file_path in self._attached_documents:
            self._attached_documents.remove(file_path)
        if widget in self._document_attachment_widgets:
            self._document_attachment_widgets.remove(widget)
        self._remove_attachment_widget(widget)

        docs = Document.objects.filter_by(path=file_path)
        if docs:
            Document.objects.update(pk=docs[0].id, active=False)

        self.emit_signal(
            SignalCode.DOCUMENT_COLLECTION_CHANGED,
            {"paths": [file_path]},
        )

    def _clear_document_attachments(self) -> None:
        """Clear the document attachments for the current chat request."""
        for widget in self._document_attachment_widgets:
            widget.deleteLater()
        self._document_attachment_widgets.clear()
        self._attached_documents.clear()
        self._update_attachments_visibility()

    def _add_attachment_widget(
        self,
        widget: ChatAttachmentPillWidget,
    ) -> None:
        """Insert one attachment pill before the trailing spacer."""
        if hasattr(self.ui, "attachments_layout"):
            if self._attachments_spacer:
                self.ui.attachments_layout.removeItem(self._attachments_spacer)
            self.ui.attachments_layout.addWidget(widget)
            if self._attachments_spacer:
                self.ui.attachments_layout.addItem(self._attachments_spacer)

        self._update_attachments_visibility()

    def _remove_attachment_widget(
        self,
        widget: ChatAttachmentPillWidget,
    ) -> None:
        """Remove one attachment pill from the UI."""
        widget.deleteLater()
        self._update_attachments_visibility()

    def _remove_image_attachment(
        self,
        widget: ChatAttachmentPillWidget,
    ) -> None:
        """Remove an image attachment.
        
        Args:
            widget: The attachment widget to remove.
        """
        if widget in self._image_attachment_widgets:
            idx = self._image_attachment_widgets.index(widget)
            self._image_attachment_widgets.remove(widget)
            if idx < len(self._attached_images):
                self._attached_images.pop(idx)

        self._remove_attachment_widget(widget)

    def _clear_image_attachments(self) -> None:
        """Clear all image attachments."""
        for widget in self._image_attachment_widgets:
            widget.deleteLater()
        self._image_attachment_widgets.clear()
        self._attached_images.clear()
        self._update_attachments_visibility()

    def _update_attachments_visibility(self) -> None:
        """Update visibility of attachments container based on content."""
        if hasattr(self.ui, "attachments_scroll_area"):
            has_attachments = bool(
                self._document_attachment_widgets
                or self._image_attachment_widgets
            )
            self.ui.attachments_scroll_area.setVisible(has_attachments)

    def _get_attached_images(self) -> List[Image.Image]:
        """Get list of attached PIL Images for LLM request.
        
        Returns:
            List of PIL Image objects.
        """
        return [img for img, _ in self._attached_images]

    def _collect_images_for_llm(self) -> List[Image.Image]:
        """Combine manual attachments with current canvas image when available."""
        images = list(self._get_attached_images())
        canvas_image = self._get_canvas_image_attachment()
        if canvas_image is not None:
            images.insert(0, canvas_image)
        return images

    def _get_canvas_image_attachment(self) -> Optional[Image.Image]:
        """Fetch the active canvas image when the art tab is active."""
        if not AIRUNNER_ART_ENABLED or not self._is_art_tab_active():
            return None

        try:
            binary_image = self.drawing_pad_settings.image
        except Exception:
            return None

        if not binary_image:
            return None

        image = convert_binary_to_image(binary_image)
        if image is None:
            return None
        if image.mode not in ("RGB", "RGBA"):
            try:
                image = image.convert("RGB")
            except Exception:
                return None
        return image

    def _is_art_tab_active(self) -> bool:
        """Return True when the always-visible center canvas is available."""
        return bool(AIRUNNER_ART_ENABLED)

    def eventFilter(self, obj, event) -> bool:
        """Handle prompt submission and prompt drag-drop events.
        
        Args:
            obj: The object receiving the event.
            event: The event.
            
        Returns:
            True if event was handled, False otherwise.
        """
        if hasattr(self.ui, "prompt") and obj is self.ui.prompt:
            if self._is_prompt_submit_keypress(event):
                self.do_generate()
                return True

        # Handle drag events on prompt viewport
        if hasattr(self.ui, "prompt") and obj is self.ui.prompt.viewport():
            if event.type() == event.Type.DragEnter:
                return self._handle_drag_enter(event)
            elif event.type() == event.Type.DragMove:
                event.acceptProposedAction()
                return True
            elif event.type() == event.Type.Drop:
                return self._handle_drop(event)
        
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event for image attachments."""
        if self._handle_drag_enter(event):
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event for image attachments."""
        if self._handle_drop(event):
            return
        super().dropEvent(event)

    def _handle_drag_enter(self, event: QDragEnterEvent) -> bool:
        """Handle drag enter for supported documents and images.
        
        Args:
            event: The drag enter event.
            
        Returns:
            True if the drag was accepted, False otherwise.
        """
        mime = event.mimeData()

        if self._extract_dragged_knowledge_base_paths(event):
            event.acceptProposedAction()
            return True

        # Accept supported local document or image URLs
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if not path:
                    continue
                if is_rag_document_path(path):
                    event.acceptProposedAction()
                    return True

        return False

    def _handle_drop(self, event: QDropEvent) -> bool:
        """Handle dropped documents and images for the current chat."""
        mime = event.mimeData()

        internal_paths = self._extract_dragged_knowledge_base_paths(event)
        if internal_paths:
            for path in internal_paths:
                self._attach_knowledge_base_document(path)
            event.acceptProposedAction()
            return True

        if mime.hasUrls():
            handled = False
            for url in mime.urls():
                path = url.toLocalFile()
                if not path or not os.path.exists(path):
                    continue
                if is_rag_document_path(path):
                    self._add_document_attachment_from_path(path)
                    handled = True
                    continue
            if handled:
                event.acceptProposedAction()
                return True

        return False

    def _extract_dragged_knowledge_base_paths(
        self,
        event: QDragEnterEvent | QDropEvent,
    ) -> List[str]:
        """Return existing document paths from one internal tree drag."""
        source = event.source()
        if source is None or not hasattr(source, "selectedIndexes"):
            return []

        paths: List[str] = []
        seen: set[str] = set()
        for index in source.selectedIndexes():
            try:
                path = index.data(Qt.ItemDataRole.UserRole)
            except Exception:
                path = None
            if not isinstance(path, str) or not path or path in seen:
                continue
            if not os.path.exists(path):
                continue
            seen.add(path)
            paths.append(path)
        return paths

