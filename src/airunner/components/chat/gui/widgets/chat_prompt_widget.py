from typing import Dict, Optional

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor

from langchain_core.messages.utils import count_tokens_approximately

from airunner.components.chat.gui.widgets.templates.chat_prompt_ui import (
    Ui_chat_prompt,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
    ModelService,
)
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
    SLASH_COMMANDS,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("chevron-up", "send_button"),
        ("plus", "clear_conversation_button"),
        ("clock", "history_button"),
        ("settings", "settings_button"),
        ("stop-circle", "stop_button"),
    ]
    logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL: self.on_hear_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_text_generate_request_signal,
            SignalCode.LLM_MODEL_CHANGED: self.on_llm_model_changed,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed,
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
        self.promptKeyPressEvent = None
        self.originalKeyPressEvent = None
        self.action_menu_displayed = None
        self.action_menu_displayed = None
        self.messages_spacer = None
        self.chat_loaded = False
        self.ui.action.blockSignals(True)
        self.ui.action.clear()
        self._model_context_tokens: Optional[int] = None
        # Put Chat first as the default for simple conversations (no tools)
        # Users can select Auto for tool access when needed
        action_map = [
            ("Chat", LLMActionType.CHAT),
            ("Auto", LLMActionType.APPLICATION_COMMAND),
            ("RAG", LLMActionType.PERFORM_RAG_SEARCH),
            ("Deep Research", LLMActionType.DEEP_RESEARCH),
            ("Use Computer", LLMActionType.USE_COMPUTER),
        ]
        if AIRUNNER_ART_ENABLED:
            action_map.append(("Image", LLMActionType.GENERATE_IMAGE))
        for label, _ in action_map:
            self.ui.action.addItem(label)
        current_action = self.action
        for idx, (_, action_type) in enumerate(action_map):
            if current_action is action_type:
                self.ui.action.setCurrentIndex(idx)
                break
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.ui.prompt.keyPressEvent = self.handle_key_press
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
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
        self.ui.chat_history_widget.setVisible(False)
        self.ui.tabWidget.tabBar().hide()
        self._model_context_tokens = self._resolve_model_context_length()
        if hasattr(self.ui, "token_count"):
            self._set_token_count_label(0, self._model_context_tokens)

    def _apply_default_splitter_settings(self):
        if hasattr(self, "ui") and self.ui is not None:
            QApplication.processEvents()
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
                "ChatPromptWidget: UI not available when attempting to apply default splitter settings."
            )

    @Slot()
    def on_clear_conversation_button_clicked(self):
        """Create a new conversation and clear the display."""
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

    @Slot(bool)
    def on_history_button_toggled(self, checked: bool):
        self.ui.settings_button.blockSignals(True)
        self.ui.settings_button.setChecked(False)
        self.ui.settings_button.blockSignals(False)
        self.ui.tabWidget.setCurrentIndex(2 if checked else 0)

    @Slot(bool)
    def on_settings_button_toggled(self, checked: bool):
        self.ui.history_button.blockSignals(True)
        self.ui.history_button.setChecked(False)
        self.ui.history_button.blockSignals(False)
        self.ui.tabWidget.setCurrentIndex(1 if checked else 0)

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
        return LLMActionType[self.llm_generator_settings.action]

    def on_model_status_changed_signal(self, data):
        if data["model"] == ModelType.LLM:
            self.chat_loaded = data["status"] is ModelStatus.LOADED

        if not self.chat_loaded:
            self.disable_send_button()
        else:
            self.enable_send_button()

    def on_hear_signal(self, data: Dict):
        transcription = data["transcription"]
        self.prompt = transcription
        self.do_generate()

    def enable_generate(self):
        self.generating = False
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    @Slot()
    def on_stop_button_clicked(self):
        self.api.llm.interrupt()
        self.stop_progress_bar()
        self.generating = False
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

        model_load_balancer = getattr(self.api, "model_load_balancer", None)
        art_model_loaded = (
            model_load_balancer
            and ModelType.SD in model_load_balancer.get_loaded_models()
        )
        llm_loaded = (
            model_load_balancer
            and ModelType.LLM in model_load_balancer.get_loaded_models()
        )
        if art_model_loaded and not llm_loaded:
            model_load_balancer.switch_to_non_art_mode()

        if self.generating:
            if self.held_message is None:
                self.held_message = prompt
                self.disable_send_button()
                self.on_stop_button_clicked()
            return
        self.generating = True

        conversation_id = self._ensure_conversation_context()
        if conversation_id is None:
            self.logger.error(
                "Aborting chat request - unable to determine conversation ID"
            )
            self.generating = False
            return

        self.clear_prompt()
        self.start_progress_bar()
        # Create LLMRequest optimized for the action type
        self.api.llm.send_request(
            prompt=prompt,
            llm_request=LLMRequest.for_action(self.action),
            action=self.action,
            do_tts_reply=False,
            conversation_id=conversation_id,
        )

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        self.ui.prompt.keyPressEvent = self.handle_key_press

        if not self.chat_loaded:
            self.disable_send_button()

        # Load conversation on first show
        if self.loading and hasattr(self.ui, "conversation"):
            self.logger.info(
                "First showEvent - loading most recent conversation"
            )
            self.load_conversation()
            self.loading = False

    def llm_action_changed(self, val: str):
        if val == "Chat":
            llm_action_value = LLMActionType.CHAT
        elif val == "Image":
            llm_action_value = LLMActionType.GENERATE_IMAGE
        elif val == "RAG":
            llm_action_value = LLMActionType.PERFORM_RAG_SEARCH
        elif val == "Deep Research":
            llm_action_value = LLMActionType.DEEP_RESEARCH
        elif val == "Auto":
            llm_action_value = LLMActionType.APPLICATION_COMMAND
        elif val == "Use Computer":
            llm_action_value = LLMActionType.USE_COMPUTER
        else:
            llm_action_value = LLMActionType.APPLICATION_COMMAND
        self.update_llm_generator_settings(action=llm_action_value.name)

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
            candidate = prompt[1:].split(" ")[0]
            if candidate in SLASH_COMMANDS:
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

    def _refresh_model_context_tokens(self) -> None:
        self._model_context_tokens = self._resolve_model_context_length()

    def on_llm_model_changed(self, data: Dict):
        self._refresh_model_context_tokens()
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
        if column not in {"model_version", "model_service", "model_path"}:
            return

        self._refresh_model_context_tokens()
        prompt_text = (
            self.ui.prompt.toPlainText().strip()
            if hasattr(self.ui, "prompt")
            else self.prompt
        )
        self._update_token_count_label(prompt_text)

    def clear_prompt(self):
        self.ui.prompt.setPlainText("")

    def start_progress_bar(self):
        self.ui.progressBar.setRange(0, 0)
        self.ui.progressBar.setValue(0)

    def stop_progress_bar(self):
        self.ui.progressBar.setRange(0, 1)
        self.ui.progressBar.setValue(1)
        self.ui.progressBar.reset()

    def disable_send_button(self):
        pass

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)
        self._disabled = False

    def handle_key_press(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if (
                not self._disabled
                and event.modifiers() != Qt.KeyboardModifier.ShiftModifier
            ):
                self.do_generate()
                event.accept()
                return
        if (
            self.originalKeyPressEvent is not None
            and self.originalKeyPressEvent != self.handle_key_press
        ):
            self.originalKeyPressEvent(event)

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
        if llm_response is not None and getattr(
            llm_response, "is_first_message", False
        ):
            self.stop_progress_bar()
            self.enable_generate()

    def on_llm_text_generate_request_signal(self, data: Dict):
        """Handle LLM text generate request signal - user message is being sent."""
        self.logger.debug(f"LLM_TEXT_GENERATE_REQUEST_SIGNAL received: {data}")
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
        self.logger.info(
            f"Loaded {len(messages)} messages from conversation {conversation_id}"
        )
        for idx, msg in enumerate(messages):
            self.logger.info(
                f"  Message {idx}: is_bot={msg.get('is_bot')}, content_preview={msg.get('content', '')[:50]}"
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
        pass

    def _set_conversation_widgets(self, messages, skip_scroll: bool = False):
        pass

    def _clear_conversation_widgets(self, skip_update: bool = False):
        pass

    def add_message_to_conversation(self, *args, **kwargs):
        pass

    def on_mood_summary_update_started(self, *args, **kwargs):
        pass

    def _handle_mood_summary_update_started(self, *args, **kwargs):
        pass

    def register_web_channel(self, channel):
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
