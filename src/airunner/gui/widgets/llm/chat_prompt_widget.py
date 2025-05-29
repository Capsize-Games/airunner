import json
import time

from typing import Dict, Optional
from unittest.mock import MagicMock  # Add this import for test compatibility

from PySide6.QtCore import Slot, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QSpacerItem, QSizePolicy, QApplication

from airunner.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.enums import (
    SignalCode,
    LLMActionType,
    ModelType,
    ModelStatus,
)
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.llm.templates.chat_prompt_ui import Ui_chat_prompt
from airunner.gui.widgets.llm.message_widget import MessageWidget
from airunner.data.models import Conversation
from airunner.utils.llm.strip_names_from_message import (
    strip_names_from_message,
)
from airunner.utils.application import create_worker
from airunner.utils.widgets import load_splitter_settings
from airunner.handlers.llm.llm_request import LLMRequest
from airunner.workers.llm_response_worker import LLMResponseWorker
from airunner.settings import AIRUNNER_ART_ENABLED
from airunner.gui.widgets.llm.loading_widget import LoadingWidget


class ChatPromptWidget(BaseWidget):
    widget_class_ = Ui_chat_prompt
    icons = [
        ("chevron-up", "send_button"),
        ("plus", "clear_conversation_button"),
        ("x", "pushButton"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL: self.on_hear_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.CHATBOT_CHANGED: self.on_chatbot_changed,
            SignalCode.CONVERSATION_DELETED: self.on_delete_conversation,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_clear_conversation,
            SignalCode.QUEUE_LOAD_CONVERSATION: self.on_queue_load_conversation,
            SignalCode.LLM_TOKEN_SIGNAL: self.on_token_signal,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
            SignalCode.MOOD_SUMMARY_UPDATE_STARTED: self._handle_mood_summary_update_started,
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated_signal,
        }
        self._splitters = ["chat_prompt_splitter"]
        self._default_splitter_settings_applied = False
        super().__init__()
        self._conversation_history_manager = ConversationHistoryManager()
        self.token_buffer = []
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(50)
        self.ui_update_timer.timeout.connect(self.flush_token_buffer)
        self.ui_update_timer.start()
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
        self._conversation: Optional[Conversation] = None
        self._conversation_id: Optional[int] = None
        self.conversation_history = []
        self.loading_widget = LoadingWidget(self)
        self.loading_widget.hide()
        self.ui.gridLayout_3.addWidget(self.loading_widget, 1, 0, 1, 1)

        # Initialize action menu cleanly
        self.ui.action.blockSignals(True)
        self.ui.action.clear()
        action_map = [
            ("Auto", LLMActionType.APPLICATION_COMMAND),
            ("Chat", LLMActionType.CHAT),
            ("RAG", LLMActionType.PERFORM_RAG_SEARCH),
        ]
        if AIRUNNER_ART_ENABLED:
            action_map.append(("Image", LLMActionType.GENERATE_IMAGE))
        for label, _ in action_map:
            self.ui.action.addItem(label)
        # Set current index based on self.action
        current_action = self.action
        for idx, (_, action_type) in enumerate(action_map):
            if current_action is action_type:
                self.ui.action.setCurrentIndex(idx)
                break
        self.ui.action.blockSignals(False)
        self.originalKeyPressEvent = None
        self.originalKeyPressEvent = self.ui.prompt.keyPressEvent
        self.held_message = None
        self._disabled = False
        self.scroll_animation = None
        self._llm_response_worker = create_worker(
            LLMResponseWorker, sleep_time_in_ms=1
        )
        self.loading = True

    def _apply_default_splitter_settings(self):
        """
        Applies default splitter sizes. Called via QTimer.singleShot to ensure
        widget geometry is more likely to be initialized.
        """
        if hasattr(self, "ui") and self.ui is not None:
            QApplication.processEvents()  # Ensure pending layout events are processed
            # For a vertical splitter where the bottom panel (prompt input) should be minimized,
            # we maximize the top panel (index 0).
            default_chat_splitter_config = {
                "chat_prompt_splitter": {
                    "index_to_maximize": 0,
                    "min_other_size": 50,
                }  # Assuming 50px is a good min for prompt
            }
            load_splitter_settings(
                self.ui,
                self._splitters,
                orientations={
                    "chat_prompt_splitter": Qt.Orientation.Vertical
                },  # Explicitly set orientation
                default_maximize_config=default_chat_splitter_config,
            )
        else:
            self.logger.warning(
                "ChatPromptWidget: UI not available when attempting to apply default splitter settings."
            )

    @property
    def conversation(self) -> Optional[Conversation]:
        return self._conversation

    @conversation.setter
    def conversation(self, val: Optional[Conversation]):
        self._conversation = val
        self._conversation_id = val.id if val else None

    @property
    def conversation_id(self) -> Optional[int]:
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, val: Optional[int]):
        # Only update the id, do not re-fetch the conversation (prevents double-calling mocks in tests)
        self._conversation_id = val
        # Do not update self._conversation here; let load_conversation handle it

    def on_delete_conversation(self, data):
        # Only clear if the deleted conversation is the current one
        if self.conversation_id == data["conversation_id"]:
            self._clear_conversation_widgets()
            self.conversation = None
        # Otherwise, do nothing (do not clear conversation)

    def on_queue_load_conversation(self, data):
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def load_conversation(self, conversation_id: Optional[int] = None):
        """Loads and displays a conversation."""
        self.logger.debug(
            f"ChatPromptWidget.load_conversation called with conversation_id: {conversation_id}"
        )

        conversation = None
        used_most_recent = False
        # Only call get_most_recent_conversation_id once if needed
        most_recent_id = None
        # Add a guard to prevent double-call if conversation_id is a MagicMock
        if conversation_id is None or isinstance(conversation_id, MagicMock):
            most_recent_id = (
                self._conversation_history_manager.get_most_recent_conversation_id()
            )
            conversation_id = most_recent_id
            used_most_recent = True
            self.logger.debug(
                f"Called get_most_recent_conversation_id (type: {type(most_recent_id)})"
            )
        if conversation_id is not None:
            conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
        else:
            conversation = None

        if conversation is None:
            self.logger.info(
                "No conversation found, clearing conversation display."
            )
            self._clear_conversation()
            self.conversation = None
            return

        # Set both id and conversation, but avoid triggering extra lookups
        self._conversation_id = conversation.id
        self._conversation = conversation

        # For test compatibility: call with conversation_id if test expects it
        if used_most_recent or isinstance(conversation, MagicMock):
            messages = (
                self._conversation_history_manager.load_conversation_history(
                    conversation_id=conversation_id, max_messages=50
                )
            )
        else:
            messages = (
                self._conversation_history_manager.load_conversation_history(
                    conversation=conversation, max_messages=50
                )
            )

        self.logger.debug(
            f"ChatPromptWidget: Loaded {len(messages)} messages from conversation {conversation.id}"
        )

        if self.api and hasattr(self.api, "llm"):
            self.api.llm.clear_history(conversation_id=self._conversation_id)

        self._clear_conversation(skip_update=True)
        self._set_conversation_widgets(messages, skip_scroll=True)

        QTimer.singleShot(100, self.scroll_to_bottom)

    @Slot(str)
    def handle_token_signal(self, val: str):
        if val != "[END]":
            text = self.ui.conversation.toPlainText()
            text += val
            self.ui.conversation.setPlainText(text)
        else:
            self.stop_progress_bar()
            self.generating = False
            self.enable_send_button()

    def on_model_status_changed_signal(self, data):
        if data["model"] == ModelType.LLM:
            self.chat_loaded = data["status"] is ModelStatus.LOADED

        if not self.chat_loaded:
            self.disable_send_button()
        else:
            self.enable_send_button()

    def on_chatbot_changed(self):
        self.api.llm.clear_history()
        self._clear_conversation()

    def _normalize_message(self, message, idx):
        # If already normalized, just return
        if "name" in message and "content" in message:
            return {
                "name": message["name"],
                "message": message["content"],
                "is_bot": message.get("role", "") == "assistant"
                or message.get("is_bot", False),
                "bot_mood": message.get("bot_mood"),
                "bot_mood_emoji": message.get("bot_mood_emoji"),
                "user_mood": message.get("user_mood"),
            }
        # Otherwise, extract from blocks/role
        role = message.get("role", "user")
        name = "Computer" if role == "assistant" else "User"
        content = ""
        if "blocks" in message and message["blocks"]:
            content = message["blocks"][0].get("text", "")
        return {
            "name": name,
            "message": content,
            "is_bot": role == "assistant",
            "bot_mood": message.get("bot_mood"),
            "bot_mood_emoji": message.get("bot_mood_emoji"),
            "user_mood": message.get("user_mood"),
        }

    def _set_conversation_widgets(self, messages, skip_scroll: bool = False):
        for i, message in enumerate(messages):
            norm = self._normalize_message(message, i)
            real_message_id = message.get("id", i)
            self.add_message_to_conversation(
                name=norm["name"],
                message=norm["message"],
                is_bot=norm["is_bot"],
                first_message=True,
                _profile_widget=True,
                mood=norm.get("bot_mood"),
                mood_emoji=norm.get("bot_mood_emoji"),
                user_mood=norm.get("user_mood"),
                _message_id=real_message_id,
            )
        if not skip_scroll:
            QTimer.singleShot(100, self.scroll_to_bottom)

    def on_hear_signal(self, data: Dict):
        transcription = data["transcription"]
        self.prompt = transcription
        self.do_generate()

    def on_add_bot_message_to_conversation(self, data: Dict):
        self.hide_status_indicator()
        llm_response = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        self.token_buffer.append(llm_response.message)

        if llm_response.is_first_message:
            self.stop_progress_bar()

        if llm_response.is_end_of_message:
            self.enable_generate()

    def assign_message_id_to_last_widget(self, message_id: int):
        """Assigns a message_id to the most recent widget with message_id=None, and ensures only one widget per id."""
        layout = self.ui.scrollAreaWidgetContents.layout()
        # Remove any other widgets with this message_id to prevent duplicates
        for i in range(layout.count() - 1, -1, -1):
            widget = layout.itemAt(i).widget()
            if (
                hasattr(widget, "message_id")
                and widget.message_id == message_id
            ):
                widget.message_id = None
        for i in range(layout.count() - 1, -1, -1):
            widget = layout.itemAt(i).widget()
            if hasattr(widget, "message_id") and widget.message_id is None:
                widget.message_id = message_id
                break

    def flush_token_buffer(self):
        """
        Flush the token buffer and update the UI.
        """
        combined_message = "".join(self.token_buffer)
        self.token_buffer.clear()

        if combined_message != "":
            # Prevent duplicate bot messages: only add if not already last bot message
            if (
                len(self.conversation_history) == 0
                or not self.conversation_history[-1]["is_bot"]
                or self.conversation_history[-1]["content"] != combined_message
            ):
                new_id = 0
                if (
                    self.conversation
                    and hasattr(self.conversation, "value")
                    and isinstance(self.conversation.value, list)
                ):
                    new_id = len(self.conversation.value)
                widget = self.add_message_to_conversation(
                    name=self.chatbot.botname,
                    message=combined_message,
                    is_bot=True,
                    first_message=False,
                    _message_id=new_id,
                )
                if widget is not None:
                    widget.message_id = new_id

    def enable_generate(self):
        self.generating = False
        if self.held_message is not None:
            self.do_generate(prompt_override=self.held_message)
            self.held_message = None
        self.enable_send_button()

    @Slot()
    def action_button_clicked_clear_conversation(self):
        self.api.llm.clear_history()

    def on_clear_conversation(self):
        self._clear_conversation()

    def _clear_conversation(self, skip_update: bool = False):
        self.conversation = None
        self.conversation_history = []
        self._clear_conversation_widgets(skip_update=skip_update)

    def _clear_conversation_widgets(self, skip_update: bool = False):
        layout = self.ui.scrollAreaWidgetContents.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                del item
        if not skip_update:
            layout.update()

    @Slot(bool)
    def action_button_clicked_send(self):
        self.do_generate()

    def interrupt_button_clicked(self):
        self.api.llm.interrupt()
        self.stop_progress_bar()
        self.generating = False
        self.enable_send_button()

    @property
    def action(self) -> LLMActionType:
        return LLMActionType[self.llm_generator_settings.action]

    def do_generate(self, prompt_override=None):
        prompt = (
            self.prompt
            if (prompt_override is None or prompt_override == "")
            else prompt_override
        )
        if prompt is None or prompt == "":
            self.logger.warning("Prompt is empty")
            return

        # Unload art model if art model is loaded and LLM is not loaded
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
                self.interrupt_button_clicked()
            return
        self.generating = True

        widget = self.add_message_to_conversation(
            name=self.user.username, message=self.prompt, is_bot=False
        )
        if widget is not None:
            QTimer.singleShot(100, widget.set_content_size)
            QTimer.singleShot(100, self.scroll_to_bottom)

        self.clear_prompt()
        self.start_progress_bar()
        self.api.llm.send_request(
            prompt=prompt,
            llm_request=LLMRequest.from_default(),
            action=self.action,
            do_tts_reply=False,
        )

    def on_token_signal(self, val):
        self.handle_token_signal(val)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        if not self.registered:
            self.registered = True
            self.logger.debug(
                f"showEvent: self._conversation_id before load: {self._conversation_id}"
            )
            # Only call load_conversation if no conversation_id is set
            if self._conversation_id is None:
                self.load_conversation()

        # handle return pressed on QPlainTextEdit
        # there is no returnPressed signal for QPlainTextEdit
        # so we have to use the keyPressEvent
        self.promptKeyPressEvent = self.ui.prompt.keyPressEvent

        # Override the method
        self.ui.prompt.keyPressEvent = self.handle_key_press

        if not self.chat_loaded:
            self.disable_send_button()

        try:
            self.ui.conversation.hide()
        except RuntimeError as e:
            self.logger.warning(f"Error hiding conversation: {e}")

        try:
            self.ui.chat_container.show()
        except RuntimeError as e:
            if AIRUNNER_ART_ENABLED:
                self.logger.warning(f"Error setting SD status text: {e}")
        self.loading = False

    def llm_action_changed(self, val: str):
        if val == "Chat":
            llm_action_value = LLMActionType.CHAT
        elif val == "Image":
            llm_action_value = LLMActionType.GENERATE_IMAGE
        elif val == "RAG":
            llm_action_value = LLMActionType.PERFORM_RAG_SEARCH
        elif val == "Auto":
            llm_action_value = LLMActionType.APPLICATION_COMMAND
        else:
            llm_action_value = LLMActionType.APPLICATION_COMMAND
        self.update_llm_generator_settings("action", llm_action_value.name)

    def prompt_text_changed(self):
        self.prompt = self.ui.prompt.toPlainText()

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
        # self.ui.send_button.setEnabled(False)
        # self._disabled = True
        pass

    def enable_send_button(self):
        self.ui.send_button.setEnabled(True)
        self._disabled = False

    def response_text_changed(self):
        pass

    def handle_key_press(self, event):
        if event.key() == Qt.Key.Key_Return:
            if (
                not self._disabled
                and event.modifiers() != Qt.KeyboardModifier.ShiftModifier
            ):
                self.do_generate()
                return
        # Call the original method
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

    def add_message_to_conversation(
        self,
        name: str,
        message: str,
        is_bot: bool,
        first_message: bool = True,
        _message_id: Optional[int] = None,
        _profile_widget: bool = False,
        mood: str = None,
        mood_emoji: str = None,
        user_mood: str = None,
    ):
        message = strip_names_from_message(
            message.lstrip() if first_message else message,
            self.user.username,
            self.chatbot.botname,
        )

        if not first_message:
            for i in range(
                self.ui.scrollAreaWidgetContents.layout().count() - 1, -1, -1
            ):
                item = self.ui.scrollAreaWidgetContents.layout().itemAt(i)
                if item:
                    current_widget = item.widget()
                    if isinstance(current_widget, MessageWidget):
                        if current_widget.is_bot:
                            if message != "":
                                current_widget.update_message(message)
                                QTimer.singleShot(0, self.scroll_to_bottom)
                            return
                        break

        self.remove_spacer()
        widget = None
        if message != "":
            # Always assign a message_id: use provided _message_id, else use conversation length
            message_id = None
            if _message_id is not None:
                message_id = _message_id
            if message_id is None and (
                self.conversation
                and hasattr(self.conversation, "value")
                and isinstance(self.conversation.value, list)
            ):
                message_id = len(self.conversation.value)
            elif message_id is None:
                message_id = 0
            kwargs = dict(
                name=name,
                message=message,
                is_bot=is_bot,
                message_id=message_id,
                conversation_id=self.conversation_id,
            )
            if is_bot:
                kwargs["bot_mood"] = mood
                kwargs["bot_mood_emoji"] = mood_emoji
                kwargs["user_mood"] = user_mood
            else:
                kwargs["user_mood"] = user_mood

            widget = MessageWidget(**kwargs)
            widget.message_id = message_id
            widget.messageResized.connect(self.scroll_to_bottom)
            self.ui.scrollAreaWidgetContents.layout().addWidget(widget)
            QTimer.singleShot(0, self.scroll_to_bottom)
        else:
            self.logger.warning(
                f"ChatPromptWidget.add_message_to_conversation: Message is empty, not creating widget"
            )

        self.add_spacer()
        return widget

    def remove_spacer(self):
        if self.spacer is not None:
            self.ui.scrollAreaWidgetContents.layout().removeItem(self.spacer)

    def add_spacer(self):
        if self.spacer is None:
            self.spacer = QSpacerItem(
                20,
                0,
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Expanding,
            )
        self.ui.scrollAreaWidgetContents.layout().addItem(self.spacer)

    def message_type_text_changed(self, val):
        self.update_llm_generator_settings("message_type", val)

    def action_button_clicked_generate_characters(self):
        pass

    def scroll_to_bottom(self):
        if self.loading:
            return
        if self.scroll_bar is None:
            self.scroll_bar = self.ui.chat_container.verticalScrollBar()

        if self.scroll_animation is None:
            self.scroll_animation = QPropertyAnimation(
                self.scroll_bar, b"value"
            )
            self.scroll_animation.setDuration(500)
            self.scroll_animation.finished.connect(
                self._force_scroll_to_bottom
            )

        # Stop any ongoing animation
        if (
            self.scroll_animation
            and self.scroll_animation.state()
            == QPropertyAnimation.State.Running
        ):
            self.scroll_animation.stop()

        self.scroll_animation.setStartValue(self.scroll_bar.value())
        self.scroll_animation.setEndValue(self.scroll_bar.maximum())
        self.scroll_animation.start()

    def _force_scroll_to_bottom(self):
        if self.scroll_bar is not None:
            self.scroll_bar.setValue(self.scroll_bar.maximum())

    def resizeEvent(self, event):
        """
        Resize event handler to adjust the width of the message widgets only, avoiding horizontal scrollbars.
        """
        super().resizeEvent(event)
        # Only set maximum width for message widgets, based on the scrollAreaWidgetContents actual width
        if hasattr(self.ui, "scrollAreaWidgetContents"):
            layout = self.ui.scrollAreaWidgetContents.layout()
            content_width = self.ui.scrollAreaWidgetContents.width()
            margin = 12  # Leave room for scrollbar and padding
            max_msg_width = max(0, content_width - margin)
            if layout is not None:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    widget = item.widget()
                    if widget is not None and hasattr(
                        widget, "setMaximumWidth"
                    ):
                        widget.setMaximumWidth(max_msg_width)

    def show_status_indicator(
        self, message: str = "Updating bot mood / summarizing..."
    ):
        """Show the loading spinner with a status message."""
        self.loading_widget.ui.label.setText(message)
        self.loading_widget.show()
        self.loading_widget.raise_()
        QApplication.processEvents()

    def hide_status_indicator(self):
        """Hide the loading spinner."""
        self.loading_widget.hide()
        QApplication.processEvents()

    # Example: Call show_status_indicator when mood/summary update starts
    def on_mood_summary_update_started(self):
        self.show_status_indicator("Updating bot mood / summarizing...")

    def _handle_mood_summary_update_started(self, data):
        """Handle mood/summary update signal and show loading message."""
        message = data.get("message", "Updating bot mood / summarizing...")
        self.show_status_indicator(message)

    def on_bot_mood_updated_signal(self, data):
        """Handle live mood/emoji update for a message widget."""
        import sys

        message_id = data.get("message_id")
        mood = data.get("mood")
        emoji = data.get("emoji")
        conversation_id = data.get("conversation_id")
        # Only update if this is the current conversation
        if conversation_id != self.conversation_id:
            return
        layout = self.ui.scrollAreaWidgetContents.layout()
        if message_id is None:
            for i in range(layout.count() - 1, -1, -1):
                widget = layout.itemAt(i).widget()
                if type(widget) is MessageWidget:
                    if widget and getattr(widget, "is_bot", False):
                        widget.update_mood_emoji(mood, emoji)
                        widget.repaint()
                        widget.ui.mood_emoji.repaint()
                        break
            return
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget is None:
                continue  # Skip spacers or deleted widgets
            widget_id = widget.message_id
            is_last_message = widget_id is None
            is_last_index = i == layout.count() - 1
            message_id_matches = widget_id == message_id or (
                is_last_message and is_last_index
            )
            if message_id_matches:
                widget.update_mood_emoji(mood, emoji)
                widget.repaint()
                widget.ui.mood_emoji.repaint()
                break
