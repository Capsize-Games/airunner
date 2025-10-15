from typing import List, Dict, Any, Optional

from PySide6.QtCore import QTimer, Slot, Qt
from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
)
from llama_cloud import MessageRole

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.gui.widgets.loading_widget import LoadingWidget
from airunner.components.llm.gui.widgets.message_widget import MessageWidget
from airunner.enums import SignalCode
from airunner.components.chat.gui.widgets.templates.conversation_ui import (
    Ui_conversation,
)
import logging

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.utils import strip_names_from_message

logger = logging.getLogger(__name__)


class ConversationWidget(BaseWidget):
    """Widget that displays a conversation using MessageWidget instances in a QScrollArea.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    widget_class_ = Ui_conversation

    def __init__(self, *args, **kwargs):
        self.registered: bool = False
        self.signal_handlers = {
            SignalCode.QUEUE_LOAD_CONVERSATION: self.on_queue_load_conversation,
            SignalCode.LLM_TEXT_STREAMED_SIGNAL: self.on_add_bot_message_to_conversation,
            SignalCode.CONVERSATION_DELETED: self.on_delete_conversation,
            SignalCode.LLM_CLEAR_HISTORY_SIGNAL: self.on_clear_conversation,
            SignalCode.MOOD_SUMMARY_UPDATE_STARTED: self._handle_mood_summary_update_started,
            SignalCode.BOT_MOOD_UPDATED: self.on_bot_mood_updated_signal,
            SignalCode.CHATBOT_CHANGED: self.on_chatbot_changed,
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL: self.on_llm_request_text_generate_signal,
        }
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(50)
        self.ui_update_timer.timeout.connect(self.flush_token_buffer)
        self.ui_update_timer.start()
        self._conversation_history_manager = ConversationHistoryManager()
        self._conversation: Optional[Conversation] = None
        self._conversation_id: Optional[int] = None
        self.conversation_history = []
        self._streamed_messages = []
        self.loading_widget = LoadingWidget(self)
        self.loading_widget.hide()
        super().__init__()
        self.token_buffer = []
        self._current_stream_tokens = []
        self._stream_started = False
        self._sequence_buffer = {}
        self._expected_sequence = 1
        self._active_stream_message_index = None
        self.ui.messages.setContextMenuPolicy(
            Qt.ContextMenuPolicy.PreventContextMenu
        )

        # Setup the scroll area content
        self._setup_scroll_area()

    def _setup_scroll_area(self):
        """Initialize the scroll area with a vertical layout and spacer."""
        # Get the existing VBoxLayout from the UI file
        self.messages_layout = self.ui.scrollAreaWidgetContents.layout()

        # Configure the layout
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(2)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Set size policy to prevent horizontal scrollbar
        # The content widget should match the scroll area's width
        self.ui.scrollAreaWidgetContents.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )

        # Add a vertical spacer at the bottom
        self.vertical_spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.messages_layout.addItem(self.vertical_spacer)

    def navigate(self, url: str):
        self.api.navigate(url)

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
        self._conversation_id = val

    def on_delete_conversation(self, data):
        if self.conversation_id == data["conversation_id"]:
            self._clear_conversation_widgets()
            self.conversation = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self.registered:
            self.registered = True
            self.logger.debug(
                f"showEvent: self._conversation_id before load: {self._conversation_id}"
            )
            if self._conversation_id is None:
                self.load_conversation()

    def on_chatbot_changed(self):
        self.api.llm.clear_history()
        self._clear_conversation()

    def on_queue_load_conversation(self, data):
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def load_conversation(self, conversation_id: Optional[int] = None) -> None:
        """Load a conversation by ID, update state and UI."""
        if conversation_id is None:
            conversation = (
                self._conversation_history_manager.get_current_conversation()
            )
        else:
            conversation = Conversation.objects.filter_by_first(
                id=conversation_id
            )
        if conversation is None:
            self.clear_conversation()
            return
        self._conversation = conversation
        self._conversation_id = conversation.id
        messages = (
            self._conversation_history_manager.load_conversation_history(
                conversation=conversation, max_messages=50
            )
        )
        self.set_conversation_widgets(messages, skip_scroll=True)

    def clear_conversation(self) -> None:
        """Clear all conversation state and UI."""
        self._conversation = None
        self._conversation_id = None
        self.conversation_history = []
        self._streamed_messages = []
        self._clear_conversation_widgets()

    def on_add_bot_message_to_conversation(self, data: Dict):
        self.hide_status_indicator()
        llm_response = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        if llm_response.is_end_of_message:
            if not llm_response.message:
                self._finalize_stream_state()
                return

        self._handle_sequenced_token(llm_response)

    def hide_status_indicator(self):
        """Hide the loading spinner."""
        self.loading_widget.hide()
        QApplication.processEvents()

    def scroll_to_bottom(self) -> None:
        """Scroll the conversation to the bottom."""
        QTimer.singleShot(0, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self):
        """Actually perform the scroll to bottom."""
        scrollbar = self.ui.messages.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _assign_message_ids(self, messages: list[dict]) -> list[dict]:
        """Assign unique, consecutive integer 'id' to every message."""
        for idx, msg in enumerate(messages):
            msg["id"] = idx
        return messages

    def set_conversation_widgets(self, messages, skip_scroll: bool = False):
        """Create MessageWidget instances for each message and add them to the scroll area."""
        logger.debug(
            f"set_conversation_widgets called with {len(messages)} messages"
        )
        for idx, msg in enumerate(messages):
            logger.debug(
                f"Message {idx}: is_bot={msg.get('is_bot')}, role={msg.get('role')}, content={msg.get('content', '')[:50]}..."
            )

        messages = self._assign_message_ids(messages)
        for msg in messages:
            if "role" not in msg:
                msg["role"] = "assistant" if msg.get("is_bot") else "user"
            if "is_bot" not in msg:
                msg["is_bot"] = msg.get("role") == "assistant"
        self._streamed_messages = list(messages)
        if self._conversation is not None:
            self._conversation.value = self._streamed_messages

        # Clear existing message widgets
        self._clear_message_widgets()

        # Create and add message widgets
        widgets_created = 0
        for msg in self._streamed_messages:
            widget = self._create_and_add_message_widget(msg)
            if widget is None:
                logger.warning(f"Failed to create widget for message: {msg}")
            else:
                widgets_created += 1
                logger.debug(
                    f"Created widget #{widgets_created} for message {msg.get('id')}"
                )

        logger.info(
            f"Created {widgets_created} widgets out of {len(self._streamed_messages)} messages"
        )
        logger.info(f"Layout now has {self.messages_layout.count()} items")

        # Force layout and widget updates
        self.messages_layout.activate()
        self.ui.scrollAreaWidgetContents.updateGeometry()
        self.ui.messages.updateGeometry()

        # Log scroll area content size
        logger.debug(
            f"ScrollAreaWidgetContents size: {self.ui.scrollAreaWidgetContents.size()}, "
            f"sizeHint: {self.ui.scrollAreaWidgetContents.sizeHint()}"
        )

        if not skip_scroll:
            self.scroll_to_bottom()

    def _clear_message_widgets(self):
        """Remove all message widgets from the layout."""
        # Remove the spacer first
        self.messages_layout.removeItem(self.vertical_spacer)

        # Remove all widgets from the layout
        while self.messages_layout.count() > 0:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()

        # Re-add the spacer at the end
        self.messages_layout.addItem(self.vertical_spacer)

    def _create_and_add_message_widget(
        self, msg: Dict
    ) -> Optional[MessageWidget]:
        """Create a MessageWidget for a message and add it to the layout."""
        content = (
            msg.get("content") or msg.get("text") or msg.get("message") or ""
        )
        name = msg.get("name") or (
            "Assistant" if msg.get("is_bot") else "User"
        )
        is_bot = msg.get("is_bot", False)
        message_id = msg.get("id", 0)

        logger.debug(
            f"_create_and_add_message_widget: is_bot={is_bot}, name={name}, content_len={len(content)}, content_preview={content[:50]}..."
        )

        if not content:
            logger.warning(
                f"Skipping message with no content: is_bot={is_bot}, name={name}, msg keys={list(msg.keys())}"
            )
            return None

        # Remove the spacer temporarily
        self.messages_layout.removeItem(self.vertical_spacer)

        # Create the message widget
        message_widget = MessageWidget(
            parent=self.ui.scrollAreaWidgetContents,
            name=name,
            message=content,
            message_id=message_id,
            conversation_id=self.conversation_id,
            is_bot=is_bot,
            bot_mood=msg.get("bot_mood"),
            bot_mood_emoji=msg.get("bot_mood_emoji"),
            user_mood=msg.get("user_mood"),
        )

        # Ensure widget respects parent width and wraps content
        # Expanding horizontally will fill available width but respect parent constraints
        # Minimum vertically will use only as much height as needed
        message_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )

        # Force widget to be visible
        message_widget.setVisible(True)
        message_widget.show()

        # Add to layout
        self.messages_layout.addWidget(message_widget)

        # Log widget size and visibility for debugging
        logger.debug(
            f"Widget visibility: {message_widget.isVisible()}, "
            f"height: {message_widget.height()}, "
            f"sizeHint: {message_widget.sizeHint()}, "
            f"minimumHeight: {message_widget.minimumHeight()}"
        )

        # Re-add the spacer at the end
        self.messages_layout.addItem(self.vertical_spacer)

        return message_widget

    def _clear_conversation(self, skip_update: bool = False):
        self.conversation = None
        self.conversation_history = []
        self._streamed_messages = []
        self._clear_conversation_widgets(skip_update=skip_update)

    def _clear_conversation_widgets(self, skip_update: bool = False):
        """Clear all message widgets from the scroll area."""
        self._clear_message_widgets()

    def on_clear_conversation(self):
        self._clear_conversation()

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
        widget = None
        if message != "":
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

        else:
            self.logger.warning(
                f"ChatPromptWidget.add_message_to_conversation: Message is empty, not creating widget"
            )

        return widget

    def show_status_indicator(
        self, message: str = "Updating bot mood / summarizing..."
    ):
        """Show the loading spinner with a status message."""
        self.loading_widget.ui.label.setText(message)
        self.loading_widget.show()
        self.loading_widget.raise_()
        QApplication.processEvents()

    def on_mood_summary_update_started(self):
        self.show_status_indicator("Updating bot mood / summarizing...")

    def _handle_mood_summary_update_started(self, data):
        """Handle mood/summary update signal and show loading message."""
        message = data.get("message", "Updating bot mood / summarizing...")
        self.show_status_indicator(message)

    def on_bot_mood_updated_signal(self, data):
        """Handle live mood/emoji update for a message widget."""
        message_id = data.get("message_id")
        mood = data.get("mood")
        mood_emoji = data.get("mood_emoji")

        if message_id is None:
            return

        # Find the message widget with this ID and update it
        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            if (
                item
                and item.widget()
                and isinstance(item.widget(), MessageWidget)
            ):
                widget = item.widget()
                if widget.message_id == message_id:
                    widget.update_mood_emoji(mood, mood_emoji)
                    break

    def flush_token_buffer(self):
        """Flush the token buffer and update the UI."""
        combined_message = "".join(self.token_buffer)
        self.token_buffer.clear()

        if combined_message != "":
            if (
                self._streamed_messages
                and self._streamed_messages[-1]["is_bot"]
            ):
                self._streamed_messages[-1]["content"] += combined_message
            else:
                self._streamed_messages.append(
                    {
                        "name": self.chatbot.botname,
                        "content": combined_message,
                        "role": MessageRole.ASSISTANT.value,
                        "is_bot": True,
                    }
                )
            self._streamed_messages = self._assign_message_ids(
                self._streamed_messages
            )
            self._update_message_widgets()

    def _update_message_widgets(self):
        """Update the message widgets to reflect the current streamed messages."""
        # Count current widgets (excluding spacer)
        current_widget_count = sum(
            1
            for i in range(self.messages_layout.count())
            if self.messages_layout.itemAt(i).widget()
        )

        # If we have more messages than widgets, add new widgets
        if len(self._streamed_messages) > current_widget_count:
            for msg in self._streamed_messages[current_widget_count:]:
                self._create_and_add_message_widget(msg)
            self.scroll_to_bottom()
        # If we have the same number, update the last widget
        elif current_widget_count > 0:
            last_msg = self._streamed_messages[-1]
            for i in range(self.messages_layout.count() - 1, -1, -1):
                item = self.messages_layout.itemAt(i)
                if (
                    item
                    and item.widget()
                    and isinstance(item.widget(), MessageWidget)
                ):
                    widget = item.widget()
                    if widget.is_bot == last_msg.get("is_bot"):
                        widget.update_message(last_msg.get("content", ""))
                        break

    def on_llm_request_text_generate_signal(self, data):
        """Handle the LLM request text generation signal."""
        request_data = data.get("request_data", {})
        prompt = request_data.get("prompt", "")
        self._streamed_messages.append(
            {
                "name": self.user.username,
                "content": prompt,
                "role": "user",
                "is_bot": False,
            }
        )
        self._streamed_messages = self._assign_message_ids(
            self._streamed_messages
        )
        self._update_message_widgets()
        self.scroll_to_bottom()

    @Slot(int)
    @Slot(str)
    def deleteMessage(self, message_id):
        """Delete a message and all subsequent messages from the conversation."""
        conversation = self._conversation
        if not conversation or not hasattr(conversation, "value"):
            return
        try:
            message_id = int(message_id)
        except Exception:
            return
        messages = conversation.value or []
        idx = next(
            (
                i
                for i, m in enumerate(messages)
                if int(m.get("id", -1)) == message_id
            ),
            None,
        )
        if idx is None:
            return
        new_messages = messages[:idx]
        new_messages = self._assign_message_ids(new_messages)
        Conversation.objects.update(pk=conversation.id, value=new_messages)
        self._conversation.value = new_messages
        self.set_conversation_widgets(new_messages)

    def copyMessage(self, message_id):
        """Copy the message content to the clipboard."""
        try:
            msgs = self._streamed_messages or (
                self.conversation.value
                if self.conversation and hasattr(self.conversation, "value")
                else []
            )
            idx = next(
                (
                    i
                    for i, m in enumerate(msgs)
                    if int(m.get("id", -1)) == int(message_id)
                ),
                None,
            )
            if idx is None:
                return
            content = msgs[idx].get("content", "")
            QApplication.clipboard().setText(content)
        except Exception:
            return

    def newChat(self):
        """Start a new chat by clearing history via API."""
        try:
            if hasattr(self.api, "llm") and hasattr(
                self.api.llm, "clear_history"
            ):
                self.api.llm.clear_history()
            self._clear_conversation()
        except Exception:
            return

    def _handle_sequenced_token(self, llm_response):
        """Handle tokens with sequence numbers to ensure proper ordering."""
        sequence_num = llm_response.sequence_number

        if llm_response.is_first_message:
            if not self._stream_started:
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = None
            else:
                self._finalize_stream_state(partial=True)
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = None

        self._sequence_buffer[sequence_num] = llm_response
        self._process_sequential_tokens()

    def _process_sequential_tokens(self):
        """Process buffered tokens that are in the correct sequence."""
        processed_any = False
        last_token_was_end = False
        while self._expected_sequence in self._sequence_buffer:
            token_response = self._sequence_buffer.pop(self._expected_sequence)

            if token_response.message:
                # Append incoming message chunk. Chunks from different
                # streaming implementations may be either deltas (only the
                # new text) or cumulative (the full message so far). To
                # avoid duplicating repeated prefixes when chunks are
                # cumulative, we keep the chunk list but detect the
                # cumulative case below when forming the combined content.
                self._current_stream_tokens.append(token_response.message)
            if getattr(token_response, "is_end_of_message", False):
                last_token_was_end = True

            self._expected_sequence += 1
            processed_any = True

        if processed_any:
            combined_content = "".join(self._current_stream_tokens)

            if not self._streamed_messages:
                self._streamed_messages = []

            if self._active_stream_message_index is None:
                self._streamed_messages.append(
                    {
                        "name": self.chatbot.botname,
                        "content": combined_content,
                        "role": MessageRole.ASSISTANT.value,
                        "is_bot": True,
                    }
                )
                self._active_stream_message_index = (
                    len(self._streamed_messages) - 1
                )
            else:
                self._streamed_messages[self._active_stream_message_index][
                    "content"
                ] = combined_content

            self._streamed_messages = self._assign_message_ids(
                self._streamed_messages
            )
            self._update_message_widgets()

        if last_token_was_end:
            self._finalize_stream_state()

    def _finalize_stream_state(self, partial: bool = False):
        """Reset streaming state after a message completes."""
        self._stream_started = False
        self._current_stream_tokens = []
        self._active_stream_message_index = None
        self._expected_sequence = 1 if not partial else self._expected_sequence
        if not partial:
            self._sequence_buffer = {}
