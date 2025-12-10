import os
from typing import Dict, List, Optional, Tuple

from PIL import Image
from PySide6.QtCore import Slot, Qt, QPoint
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QFileDialog,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtGui import QTextCursor, QFont, QDragEnterEvent, QDropEvent

from langchain_core.messages.utils import count_tokens_approximately

from airunner.components.chat.gui.widgets.templates.chat_prompt_ui import (
    Ui_chat_prompt,
)
from airunner.components.chat.gui.widgets.image_attachment_widget import (
    ImageAttachmentWidget,
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
from airunner.utils.image import convert_binary_to_image


# MIME type used by ImageWidget for drag operations
IMAGE_METADATA_MIME_TYPE = "application/x-qt-image-metadata"


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("chevron-up", "send_button"),
        ("plus", "clear_conversation_button"),
        ("clock", "history_button"),
        ("settings", "settings_button"),
        ("stop-circle", "stop_button"),
        ("paperclip", "attach_button"),
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
        self.promptKeyPressEvent = None
        self.originalKeyPressEvent = None
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
        self._attachment_widgets: List[ImageAttachmentWidget] = []
        self._attachments_spacer: Optional[QSpacerItem] = None
        
        # Initialize provider dropdown
        self._populate_provider_dropdown()
        
        # Initialize model dropdown
        self._populate_model_dropdown()
        
        # Connect model dropdown edit signal for custom model entry
        if hasattr(self.ui, "model_dropdown"):
            self.ui.model_dropdown.lineEdit().returnPressed.connect(self._on_custom_model_entered)
        
        # Hardcode action to AUTO - we don't use the dropdown anymore
        self.update_llm_generator_settings(action=LLMActionType.APPLICATION_COMMAND.name)
        
        # Initialize thinking checkbox from settings
        if hasattr(self.ui, "thinking_checkbox"):
            self.ui.thinking_checkbox.blockSignals(True)
            enable_thinking = getattr(self.llm_generator_settings, "enable_thinking", True)
            # Handle None value from database (default to True)
            if enable_thinking is None:
                enable_thinking = True
            self.ui.thinking_checkbox.setChecked(enable_thinking)
            self.ui.thinking_checkbox.blockSignals(False)
            # Update visibility based on whether model supports thinking
            self._update_thinking_checkbox_visibility()
        
        # Initialize precision dropdown
        self._populate_precision_dropdown()
        
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.ui.prompt.keyPressEvent = self.handle_key_press
        
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
        
        # Setup slash command autocomplete
        self._setup_slash_command_completer()
        
        # Setup image attachment handling
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
        self.ui.chat_history_widget.setVisible(False)
        self.ui.tabWidget.tabBar().hide()
        self._model_context_tokens = self._resolve_model_context_length()
        if hasattr(self.ui, "token_count"):
            self._set_token_count_label(0, self._model_context_tokens)
        
        # Initialize token tracking labels
        self._update_token_tracking_labels()

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
        # Action is always AUTO (APPLICATION_COMMAND) - handles everything automatically
        return LLMActionType.APPLICATION_COMMAND

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
        
        # Parse slash command if present
        self.logger.info(f"do_generate called with prompt: {prompt[:100] if prompt else 'None'}...")
        slash_command, actual_prompt, action_override = self._parse_slash_command(prompt)
        self.logger.info(f"Slash command parse result: command={slash_command}, action_override={action_override}")
        
        # Determine action type - use override from slash command if present
        action = action_override if action_override else self.action
        self.logger.info(f"Final action: {action}")
        
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
        
        # Create LLMRequest optimized for the action type
        llm_request = LLMRequest.for_action(action)
        
        # Set force_tool if slash command specifies one
        if force_tool:
            llm_request.force_tool = force_tool
            self.logger.info(f"Set force_tool={force_tool} on llm_request")
        
        # Add attached images (manual + auto canvas) if any
        images_for_request = self._collect_images_for_llm()
        if images_for_request:
            if self._is_model_vision_capable():
                llm_request.images = images_for_request
                self.logger.info(
                    f"Added {len(images_for_request)} images to llm_request"
                )
                if self._attached_images:
                    self._clear_image_attachments()
            else:
                self.logger.warning(
                    "Images attached but model does not support vision - ignoring"
                )
        
        self.logger.info(f"Sending request - action={action}, force_tool={llm_request.force_tool}, tool_categories={llm_request.tool_categories}")
        
        self.api.llm.send_request(
            prompt=actual_prompt,
            llm_request=llm_request,
            action=action,
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
        # Deprecated - action is now always AUTO
        pass

    def thinking_toggled(self, checked: bool) -> None:
        """Handle thinking checkbox toggle.
        
        When enabled, Qwen3 models will use <think>...</think> reasoning
        before responding. This produces more thoughtful responses but
        takes longer to generate.
        """
        self.update_llm_generator_settings(enable_thinking=checked)

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

    def _setup_slash_command_completer(self) -> None:
        """Setup slash command popup for autocomplete."""
        # Build command data with descriptions
        self._slash_commands_data = []
        for cmd, config in SLASH_COMMANDS.items():
            self._slash_commands_data.append({
                "command": f"/{cmd}",
                "description": config.get("description", ""),
            })
        
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
            self._slash_popup.hide()
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
                self._slash_popup.hide()
        else:
            self._slash_popup.hide()

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
        self._slash_popup.hide()
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
            self._slash_popup.hide()
            return True
        
        # Let all other keys pass through (including Enter - user might want to submit)
        # The popup will auto-hide if text no longer matches
        return False

    def _parse_slash_command(self, prompt: str) -> Tuple[Optional[str], str, Optional[LLMActionType]]:
        """Parse a slash command from the prompt.
        
        Args:
            prompt: The full prompt text
            
        Returns:
            Tuple of (command_name, remaining_prompt, action_type_override)
            - command_name: The slash command (e.g., "deepsearch") or None
            - remaining_prompt: The prompt with the command stripped
            - action_type_override: Optional LLMActionType to use instead of AUTO
        """
        if not prompt.startswith("/"):
            return None, prompt, None
        
        parts = prompt[1:].split(" ", 1)
        command = parts[0].lower()
        
        if command not in SLASH_COMMANDS:
            # Unknown command, treat as regular prompt
            return None, prompt, None
        
        # Get remaining prompt (everything after the command)
        remaining = parts[1].strip() if len(parts) > 1 else ""
        
        # Get action type override if specified
        cmd_config = SLASH_COMMANDS[command]
        action_override = None
        if "action" in cmd_config:
            action_name = cmd_config["action"]
            try:
                action_override = LLMActionType[action_name]
            except KeyError:
                self.logger.warning(f"Unknown action type in slash command: {action_name}")
        
        return command, remaining, action_override

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
            # Check model_version first (e.g., "qwen3-8b")
            if self._lookup_model_supports_thinking(model_version):
                return True
            # Fall back to model_path (e.g., "Qwen/Qwen3-8B" or local path)
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
        """Update the visibility of the thinking checkbox based on model capability."""
        if not hasattr(self.ui, "thinking_checkbox"):
            return
        
        supports_thinking = self._model_supports_thinking()
        self.ui.thinking_checkbox.setVisible(supports_thinking)

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
        if column not in {"model_version", "model_service", "model_path"}:
            return

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
        # Handle slash popup navigation first
        if self._handle_slash_popup_navigation(event.key()):
            event.accept()
            return
            
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

    def _populate_model_dropdown(self) -> None:
        """Populate the model dropdown with available models for current provider."""
        if not hasattr(self.ui, "model_dropdown"):
            return
        
        self.ui.model_dropdown.blockSignals(True)
        self.ui.model_dropdown.clear()
        
        # Get current provider from dropdown or settings
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
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
        
        self.ui.model_dropdown.blockSignals(False)
    
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
                                base_path = os.path.expanduser(
                                    getattr(self.path_settings, "base_path", "~/.local/share/airunner")
                                )
                                correct_path = os.path.join(base_path, f"text/models/llm/causallm/{model_name}")
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
                            base_path = os.path.expanduser(
                                getattr(self.path_settings, "base_path", "~/.local/share/airunner")
                            )
                            correct_path = os.path.join(base_path, f"text/models/llm/causallm/{model_name}")
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
                        if model_name and model_name in current_path:
                            self.ui.model_dropdown.setCurrentIndex(i)
                            self._update_model_tooltip(model_id)
                            return
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
                        base_path = os.path.expanduser(
                            getattr(self.path_settings, "base_path", "~/.local/share/airunner")
                        )
                        model_path = os.path.join(base_path, f"text/models/llm/causallm/{model_name}")
                        
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
        
        # Get current provider
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
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

    def _populate_provider_dropdown(self) -> None:
        """Populate the provider dropdown with available providers."""
        if not hasattr(self.ui, "provider_dropdown"):
            return
        
        self.ui.provider_dropdown.blockSignals(True)
        self.ui.provider_dropdown.clear()
        
        # Provider options with display name -> ModelService value mapping
        providers = [
            ("HuggingFace", ModelService.LOCAL.value),
            ("Ollama", ModelService.OLLAMA.value),
            ("OpenRouter", ModelService.OPENROUTER.value),
        ]
        
        for display_name, service_value in providers:
            self.ui.provider_dropdown.addItem(display_name, service_value)
        
        # Set current selection based on saved settings
        current_service = getattr(self.llm_generator_settings, "model_service", ModelService.LOCAL.value)
        for i in range(self.ui.provider_dropdown.count()):
            if self.ui.provider_dropdown.itemData(i) == current_service:
                self.ui.provider_dropdown.setCurrentIndex(i)
                break
        
        self.ui.provider_dropdown.blockSignals(False)

    @Slot(int)
    def on_provider_changed(self, index: int) -> None:
        """Handle provider selection change from dropdown."""
        if index < 0:
            return
        
        provider = self.ui.provider_dropdown.itemData(index)
        if not provider:
            return
        
        # Update settings with new provider
        self.update_llm_generator_settings(model_service=provider)
        
        # Repopulate model dropdown for new provider
        self._populate_model_dropdown()
        
        # Update precision dropdown for new provider
        self._populate_precision_dropdown()

    @Slot(int)
    def on_model_changed(self, index: int) -> None:
        """Handle model selection change from dropdown."""
        if index < 0:
            return
        
        model_id = self.ui.model_dropdown.itemData(index)
        model_text = self.ui.model_dropdown.currentText()
        
        # Get current provider
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
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
            base_path = os.path.expanduser(
                getattr(self.path_settings, "base_path", "~/.local/share/airunner")
            )
            model_path = os.path.join(base_path, f"text/models/llm/causallm/{model_name}")
            
            self.update_llm_generator_settings(
                model_path=model_path,
                model_version=model_name,
                model_id=model_id,  # Save the provider config model ID
            )
            
            # Emit signal that model changed (will trigger reload/download)
            self.emit_signal(
                SignalCode.LLM_MODEL_CHANGED,
                {"model_path": model_path, "model_name": model_name},
            )
        else:
            # Ollama or OpenRouter - just update model_version
            self.update_llm_generator_settings(
                model_version=model_id,
                model_path="",  # Not used for remote providers
                model_id=model_id,  # Save the model ID
            )
            
            # Emit signal
            self.emit_signal(
                SignalCode.LLM_MODEL_CHANGED,
                {"model_path": "", "model_name": model_id},
            )
        
        # Update thinking checkbox visibility based on new model
        self._update_thinking_checkbox_visibility()
        
        # Update context tokens
        self._refresh_model_context_tokens()
        
        # Update precision dropdown for new model
        self._populate_precision_dropdown()

    @Slot(int)
    def on_precision_changed(self, index: int) -> None:
        """Handle precision selection change from dropdown.
        
        Updates the LLM generator settings with the selected dtype/precision.
        This affects how the model is loaded (quantization level).
        """
        if index < 0:
            return
        
        if not hasattr(self.ui, "precision_dropdown"):
            return
        
        precision = self.ui.precision_dropdown.itemData(index)
        if not precision:
            return
        
        self.logger.info(f"Precision changed to: {precision}")
        self.update_llm_generator_settings(dtype=precision)
        
        # Emit signal to reload model with new precision
        self.emit_signal(
            SignalCode.LLM_MODEL_CHANGED,
            {
                "model_path": getattr(self.llm_generator_settings, "model_path", ""),
                "model_name": getattr(self.llm_generator_settings, "model_version", ""),
            },
        )

    def _populate_precision_dropdown(self) -> None:
        """Populate the precision dropdown with available options.
        
        Options are filtered based on the model's native precision.
        Lower precision options (more quantization) are always available,
        while higher precision options are limited by the model's native precision.
        
        Precision hierarchy (from highest to lowest):
        - bf16 (bfloat16) - 16-bit brain float
        - fp16 (float16) - 16-bit float
        - 8bit - 8-bit quantization
        - 4bit - 4-bit quantization (default)
        """
        if not hasattr(self.ui, "precision_dropdown"):
            return
        
        self.ui.precision_dropdown.blockSignals(True)
        self.ui.precision_dropdown.clear()
        
        # Get current provider
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
        # Remote providers don't support precision selection
        if provider != ModelService.LOCAL.value:
            self.ui.precision_dropdown.addItem("Auto", "auto")
            self.ui.precision_dropdown.setEnabled(False)
            self.ui.precision_dropdown.setToolTip("Precision selection not available for remote providers")
            self.ui.precision_dropdown.blockSignals(False)
            return
        
        self.ui.precision_dropdown.setEnabled(True)
        self.ui.precision_dropdown.setToolTip(
            "Model precision/quantization. Lower precision uses less memory but may reduce quality."
        )
        
        # Define precision options with display names and values
        # These are ordered from lowest precision (most memory efficient) to highest
        precision_options = [
            ("4-bit", "4bit"),
            ("8-bit", "8bit"),
            ("FP16", "float16"),
            ("BF16", "bfloat16"),
        ]
        
        # Get model's native precision from config if available
        native_precision = self._get_model_native_precision()
        
        # Build list of available options based on native precision
        precision_hierarchy = ["4bit", "8bit", "float16", "bfloat16"]
        native_index = precision_hierarchy.index(native_precision) if native_precision in precision_hierarchy else len(precision_hierarchy) - 1
        
        for display_name, value in precision_options:
            option_index = precision_hierarchy.index(value) if value in precision_hierarchy else 0
            if option_index <= native_index:
                self.ui.precision_dropdown.addItem(display_name, value)
        
        # Restore current selection from settings
        current_dtype = getattr(self.llm_generator_settings, "dtype", "4bit") or "4bit"
        
        # Find and select the saved dtype
        for i in range(self.ui.precision_dropdown.count()):
            if self.ui.precision_dropdown.itemData(i) == current_dtype:
                self.ui.precision_dropdown.setCurrentIndex(i)
                break
        else:
            # If saved dtype is not available (e.g., model changed), default to 4bit
            self.ui.precision_dropdown.setCurrentIndex(0)
        
        self.ui.precision_dropdown.blockSignals(False)

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
            if "/" in custom_model and not os.path.exists(custom_model):
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
            self.emit_signal(
                SignalCode.LLM_MODEL_CHANGED,
                {"model_path": model_path, "model_name": model_name},
            )
        else:
            # Ollama or OpenRouter - just set the model name
            self.update_llm_generator_settings(
                model_version=custom_model,
                model_path="",
            )
            self.emit_signal(
                SignalCode.LLM_MODEL_CHANGED,
                {"model_path": "", "model_name": custom_model},
            )

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
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
        # Handle as custom model
        self._handle_custom_model(provider, custom_text)

    def on_section_changed_signal(self, data: Dict) -> None:
        """Track the currently active main window section."""
        section = data.get("section")
        if section:
            self._active_section = section

    def _resolve_initial_section(self) -> Optional[str]:
        """Determine active section from persisted window settings."""
        try:
            index = self.window_settings.active_main_tab_index
        except Exception:
            return None

        index_to_section = {
            0: "home_button",
            1: "art_editor_button",
            2: "workflow_editor_button",
            3: "document_editor_button",
            4: "calendar_button",
        }
        return index_to_section.get(index)

    # =========================================================================
    # Image Attachment Methods
    # =========================================================================

    def _setup_image_attachments(self) -> None:
        """Set up image attachment handling (drag-drop, attach button)."""
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
        """Update attach button visibility based on model vision capability."""
        if not hasattr(self.ui, "attach_button"):
            return
        
        is_vision_capable = self._is_model_vision_capable()
        self.ui.attach_button.setEnabled(is_vision_capable)
        
        if is_vision_capable:
            self.ui.attach_button.setToolTip("Attach image for vision analysis")
        else:
            self.ui.attach_button.setToolTip(
                "Image attachment requires a vision-capable model "
                "(e.g., Ministral-3-8B)"
            )

    def _is_model_vision_capable(self) -> bool:
        """Check if the currently selected model supports vision/images.
        
        Returns:
            True if the model can process images, False otherwise.
        """
        # Get current provider
        provider = ModelService.LOCAL.value
        if hasattr(self.ui, "provider_dropdown") and self.ui.provider_dropdown.count() > 0:
            provider = self.ui.provider_dropdown.currentData() or ModelService.LOCAL.value
        
        # Get current model
        model_id = None
        if hasattr(self.ui, "model_dropdown") and self.ui.model_dropdown.count() > 0:
            model_id = self.ui.model_dropdown.currentData()
        
        if not model_id:
            return False
        
        # Check provider config for vision capability
        if provider == ModelService.LOCAL.value:
            model_config = LLMProviderConfig.LOCAL_MODELS.get(model_id, {})
            return model_config.get("vision_capable", False)
        elif provider == ModelService.OPENROUTER.value:
            # OpenRouter models with known vision capability
            # (simplified check - real implementation would query API)
            vision_models = [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-opus",
                "openai/gpt-4-turbo",
                "openai/gpt-4o",
                "google/gemini-pro-1.5",
            ]
            return model_id in vision_models
        elif provider == ModelService.OLLAMA.value:
            # Ollama vision-capable models (llava, bakllava, moondream)
            vision_models = ["llava", "bakllava", "moondream"]
            return any(vm in model_id.lower() for vm in vision_models)
        
        return False

    @Slot()
    def _on_attach_button_clicked(self) -> None:
        """Handle attach button click - open file dialog for images."""
        if not self._is_model_vision_capable():
            self.logger.warning("Cannot attach images: model does not support vision")
            return
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Images",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)",
        )
        
        for file_path in file_paths:
            self._add_image_attachment_from_path(file_path)

    def _add_image_attachment_from_path(self, file_path: str) -> None:
        """Add an image attachment from a file path.
        
        Args:
            file_path: Path to the image file.
        """
        try:
            image = Image.open(file_path)
            # Convert to RGB if needed (e.g., for RGBA or P mode images)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            self._add_image_attachment(image, file_path)
        except Exception as e:
            self.logger.error(f"Failed to load image from {file_path}: {e}")

    def _add_image_attachment(
        self,
        image: Image.Image,
        image_path: Optional[str] = None,
    ) -> None:
        """Add an image to the attachments list.
        
        Args:
            image: PIL Image to attach.
            image_path: Optional path to the source file.
        """
        if not self._is_model_vision_capable():
            self.logger.warning("Cannot attach images: model does not support vision")
            return
        
        # Store the image
        self._attached_images.append((image, image_path))
        
        # Create thumbnail widget
        widget = ImageAttachmentWidget(image, image_path, self)
        widget.removed.connect(lambda: self._remove_image_attachment(widget))
        self._attachment_widgets.append(widget)
        
        # Add to layout (before the spacer)
        if hasattr(self.ui, "attachments_layout"):
            # Remove spacer, add widget, re-add spacer
            if self._attachments_spacer:
                self.ui.attachments_layout.removeItem(self._attachments_spacer)
            self.ui.attachments_layout.addWidget(widget)
            if self._attachments_spacer:
                self.ui.attachments_layout.addItem(self._attachments_spacer)
        
        # Show attachments container
        self._update_attachments_visibility()
        
        self.logger.debug(
            f"Added image attachment: {image_path or 'in-memory'} "
            f"({image.width}x{image.height})"
        )

    def _remove_image_attachment(self, widget: ImageAttachmentWidget) -> None:
        """Remove an image attachment.
        
        Args:
            widget: The attachment widget to remove.
        """
        if widget in self._attachment_widgets:
            idx = self._attachment_widgets.index(widget)
            self._attachment_widgets.remove(widget)
            if idx < len(self._attached_images):
                self._attached_images.pop(idx)
            widget.deleteLater()
        
        self._update_attachments_visibility()

    def _clear_image_attachments(self) -> None:
        """Clear all image attachments."""
        for widget in self._attachment_widgets:
            widget.deleteLater()
        self._attachment_widgets.clear()
        self._attached_images.clear()
        self._update_attachments_visibility()

    def _update_attachments_visibility(self) -> None:
        """Update visibility of attachments container based on content."""
        if hasattr(self.ui, "attachments_scroll_area"):
            has_attachments = len(self._attachment_widgets) > 0
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
        """Return True when the main window art tab is currently active."""
        if self._active_section:
            return self._active_section == "art_editor_button"

        self._active_section = self._resolve_initial_section()
        return self._active_section == "art_editor_button"

    def eventFilter(self, obj, event) -> bool:
        """Handle events for installed event filters (prompt drag-drop).
        
        Args:
            obj: The object receiving the event.
            event: The event.
            
        Returns:
            True if event was handled, False otherwise.
        """
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
        """Handle drag enter for images.
        
        Args:
            event: The drag enter event.
            
        Returns:
            True if the drag was accepted, False otherwise.
        """
        if not self._is_model_vision_capable():
            return False
        
        mime = event.mimeData()
        
        # Accept internal image panel drags
        if mime.hasFormat(IMAGE_METADATA_MIME_TYPE):
            event.acceptProposedAction()
            return True
        
        # Accept image URLs
        if mime.hasUrls():
            for url in mime.urls():
                url_str = url.toString().lower()
                if url_str.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    event.acceptProposedAction()
                    return True
        
        # Accept raw image data
        for fmt in mime.formats():
            if fmt.startswith("image/"):
                event.acceptProposedAction()
                return True
        
        return False

    def _handle_drop(self, event: QDropEvent) -> bool:
        """Handle drop event for images.
        
        Args:
            event: The drop event.
            
        Returns:
            True if the drop was handled, False otherwise.
        """
        if not self._is_model_vision_capable():
            return False
        
        mime = event.mimeData()
        
        # Try internal image panel drag first
        if mime.hasFormat(IMAGE_METADATA_MIME_TYPE):
            try:
                import json
                data = mime.data(IMAGE_METADATA_MIME_TYPE)
                metadata_str = bytes(data.data()).decode("utf-8")
                metadata = json.loads(metadata_str)
                image_path = metadata.get("path")
                
                if image_path and os.path.exists(image_path):
                    self._add_image_attachment_from_path(image_path)
                    event.acceptProposedAction()
                    return True
            except Exception as e:
                self.logger.error(f"Failed to handle image metadata drop: {e}")
        
        # Try URLs
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path and os.path.exists(path):
                    url_str = path.lower()
                    if url_str.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                        self._add_image_attachment_from_path(path)
                        event.acceptProposedAction()
                        return True
        
        # Try raw image data
        import io
        for fmt in mime.formats():
            if not fmt.startswith("image/"):
                continue
            data = mime.data(fmt)
            if data.size() < 10:
                continue
            try:
                data_bytes = data.data()
                img = Image.open(io.BytesIO(data_bytes))
                self._add_image_attachment(img)
                event.acceptProposedAction()
                return True
            except Exception as e:
                self.logger.debug(f"Failed to load image from {fmt}: {e}")
        
        return False

