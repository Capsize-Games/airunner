from typing import List, Dict, Any, Optional

from PySide6.QtCore import QTimer, Slot, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel
from llama_cloud import MessageRole

from airunner.components.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.components.llm.data.conversation import Conversation
from airunner.components.llm.gui.widgets.loading_widget import LoadingWidget
from airunner.enums import SignalCode, TemplateName
from airunner.components.llm.gui.widgets.contentwidgets import ChatBridge
from airunner.components.chat.gui.widgets.templates.conversation_ui import (
    Ui_conversation,
)
import logging

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.utils import strip_names_from_message
from airunner.utils.text.formatter_extended import FormatterExtended

logger = logging.getLogger(__name__)


class ConversationWidget(BaseWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

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
        # Add a streaming buffer to ensure proper token ordering
        self._current_stream_tokens = []
        self._stream_started = False
        self._orphaned_tokens = (
            []
        )  # Collect tokens that arrive before is_first_message
        # Add sequence-based buffering to handle out-of-order signals
        self._sequence_buffer = {}  # Dict[int, LLMResponse]
        self._expected_sequence = 1  # Next expected sequence number
        # Track which message index is currently being streamed to avoid overwriting
        self._active_stream_message_index = None
        # prevent right click on self.ui.stage
        self.ui.stage.setContextMenuPolicy(
            Qt.ContextMenuPolicy.PreventContextMenu
        )
        self._web_channel = QWebChannel(self.ui.stage.page())
        self._chat_bridge = ChatBridge()
        self._chat_bridge.scrollRequested.connect(self._handle_scroll_request)
        self._chat_bridge.deleteMessageRequested.connect(self.deleteMessage)
        self._chat_bridge.copyMessageRequested.connect(self.copyMessage)
        self._chat_bridge.newChatRequested.connect(self.newChat)
        self._web_channel.registerObject("chatBridge", self._chat_bridge)
        self.ui.stage.page().setWebChannel(self._web_channel)

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

    @property
    def web_engine_view(self) -> Optional[object]:
        return self.ui.stage

    @property
    def template(self) -> Optional[str]:
        return "conversation.jinja2.html"

    @property
    def template_context(self) -> Dict:
        context = super().template_context
        context["messages"] = []
        return context

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
        self.set_conversation([])
        self._clear_conversation_widgets()

    def on_add_bot_message_to_conversation(self, data: Dict):
        self.hide_status_indicator()
        llm_response = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        # Skip empty end-of-stream signals, but reset state
        if llm_response.is_end_of_message:
            # Allow inclusion of any final token content then finalize after processing
            if not llm_response.message:
                self._finalize_stream_state()
                return
            # If final token carries content we'll process it then finalize in _process_sequential_tokens

        # Always use the sequence-based handler
        self._handle_sequenced_token(llm_response)

    def hide_status_indicator(self):
        """Hide the loading spinner."""
        self.loading_widget.hide()
        QApplication.processEvents()

    def wait_for_js_ready(self, callback, max_attempts=50):
        """Wait for the JS QWebChannel to be ready before calling setMessages.

        Args:
            callback: Function to call when JS is ready
            max_attempts: Maximum number of retry attempts (default 50 = ~2.5 seconds)
        """
        attempt_count = 0

        def check_ready():
            nonlocal attempt_count
            attempt_count += 1

            try:
                if not self.ui.stage or not self.ui.stage.page():
                    logger.debug(
                        "ConversationWidget: Widget or page no longer available for JS ready check"
                    )
                    return

                view_page = self.ui.stage.page()
                view_page.runJavaScript(
                    "window.isChatReady === true",
                    lambda ready: handle_result(ready),
                )
            except RuntimeError as e:
                logger.debug(
                    f"ConversationWidget: JavaScript ready check failed (widget deleted?): {e}"
                )
                callback()

        def handle_result(ready):
            if ready:
                callback()
            elif attempt_count < max_attempts:
                QTimer.singleShot(50, check_ready)
            else:
                callback()

        check_ready()

    def wait_for_dom_ready(self, callback, max_attempts=50):
        """Wait for the DOM to be ready before executing callback.

        Args:
            callback: Function to call when DOM is ready
            max_attempts: Maximum number of retry attempts (default 50 = ~2.5 seconds)
        """
        attempt_count = 0

        def check_dom_ready():
            nonlocal attempt_count
            attempt_count += 1

            try:
                if not self.ui.stage or not self.ui.stage.page():
                    logger.debug(
                        "ConversationWidget: Widget or page no longer available for DOM ready check"
                    )
                    return

                view_page = self.ui.stage.page()
                view_page.runJavaScript(
                    "document.readyState === 'complete' && !!document.getElementById('conversation-container')",
                    lambda ready: handle_dom_result(ready),
                )
            except RuntimeError as e:
                logger.debug(
                    f"ConversationWidget: DOM ready check failed (widget deleted?): {e}"
                )
                callback()

        def handle_dom_result(ready):
            if ready:
                callback()
            elif attempt_count < max_attempts:
                QTimer.singleShot(50, check_dom_ready)
            else:
                logger.warning(
                    f"ConversationWidget: DOM ready timeout after {max_attempts} attempts"
                )
                callback()

        check_dom_ready()

    def set_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """Update the conversation display using MathJax for all content types.

        Args:
            messages (List[Dict[str, Any]]): List of message dicts (sender, text, timestamp, etc).
        """
        simplified_messages = []
        for msg in messages:
            content = msg.get("text") or msg.get("content") or ""
            # Format content for MathJax compatibility
            fmt = FormatterExtended.format_content(content)

            # All content types are now handled by MathJax in the main template
            simplified_messages.append(
                {
                    **msg,
                    "content": fmt[
                        "content"
                    ],  # MathJax will handle all formatting
                    "content_type": fmt["type"],  # Keep for debugging/logging
                    "id": msg.get("id", len(simplified_messages)),
                    "timestamp": msg.get("timestamp", ""),
                    "name": msg.get("name")
                    or msg.get("sender")
                    or ("Assistant" if msg.get("is_bot") else "User"),
                    "is_bot": msg.get("is_bot", False),
                }
            )

        # Ensure _conversation_id is set if possible
        if self._conversation_id is None and self._conversation is not None:
            self._conversation_id = getattr(self._conversation, "id", None)

        def send():
            self._chat_bridge.set_messages(simplified_messages)

        self.wait_for_js_ready(send)

    def _handle_scroll_request(self) -> None:
        """Handle scroll request from JavaScript and delegate to parent scroll area."""

    def scroll_to_bottom(self) -> None:
        """Scroll the conversation to the bottom by triggering the parent QScrollArea."""

        def trigger_scroll():
            try:
                if not self.ui.stage or not self.ui.stage.page():
                    logger.debug(
                        "ConversationWidget: Widget or page no longer available for scroll"
                    )
                    return

                view_page = self.ui.stage.page()
                view_page.runJavaScript(
                    """
                    if (window.chatBridge && window.chatBridge.request_scroll) {
                        window.chatBridge.request_scroll();
                        console.log('[ConversationWidget] Scroll request sent to Qt');
                    } else {
                        console.warn('[ConversationWidget] chatBridge.request_scroll not available');
                    }
                    """,
                    lambda result: logger.debug(
                        f"ConversationWidget: Scroll request result: {result}"
                    ),
                )
            except RuntimeError as e:
                logger.debug(
                    f"ConversationWidget: JavaScript call failed (widget deleted?): {e}"
                )

        trigger_scroll()
        QTimer.singleShot(50, trigger_scroll)
        QTimer.singleShot(200, trigger_scroll)

    def _assign_message_ids(self, messages: list[dict]) -> list[dict]:
        """Assign unique, consecutive integer 'id' to every message."""
        for idx, msg in enumerate(messages):
            msg["id"] = idx
        return messages

    def set_conversation_widgets(self, messages, skip_scroll: bool = False):
        """Replace per-message widgets with a single HTML conversation view."""
        # Ensure every message has a unique integer 'id' and correct role/is_bot
        messages = self._assign_message_ids(messages)
        for msg in messages:
            if "role" not in msg:
                msg["role"] = "assistant" if msg.get("is_bot") else "user"
            if "is_bot" not in msg:
                msg["is_bot"] = msg.get("role") == "assistant"
        self._streamed_messages = list(messages)
        if self._conversation is not None:
            self._conversation.value = self._streamed_messages
        self.set_conversation(self._streamed_messages)

    def _clear_conversation(self, skip_update: bool = False):
        self.conversation = None
        self.conversation_history = []
        self._streamed_messages = []
        self.set_conversation([])
        self._clear_conversation_widgets(skip_update=skip_update)

    def _clear_conversation_widgets(self, skip_update: bool = False):
        """Clear the HTML conversation view."""
        self.set_conversation([])

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
        print("TODO: BOT MOOD UPDATED")

    def flush_token_buffer(self):
        """
        Flush the token buffer and update the UI.
        """
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
            self.set_conversation(self._streamed_messages)

    def on_llm_request_text_generate_signal(self, data):
        """
        Handle the LLM request text generation signal.
        """
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
        self.set_conversation(self._streamed_messages)

    def _get_view(self):
        """Return the QWebEngineView used for rendering the conversation."""
        return self.ui.stage if self.ui and hasattr(self.ui, "stage") else None

    @property
    def _view(self):
        """Compat property for tests expecting a _view attribute (QWebEngineView)."""
        return self._get_view()

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
        """Copy the message content to the clipboard.

        Attempts to find the message by id in the current conversation and
        places its visible text on the system clipboard.
        """
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
            # Use QApplication clipboard
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
            # Also clear local UI state
            self._clear_conversation()
        except Exception:
            return

    def _handle_sequenced_token(self, llm_response):
        """
        Handle tokens with sequence numbers to ensure proper ordering.

        Args:
            llm_response: LLMResponse object with sequence_number field
        """
        sequence_num = llm_response.sequence_number

        # Initialize / restart sequence tracking on first message boundary
        if llm_response.is_first_message:
            if not self._stream_started:
                existing_keys = list(self._sequence_buffer.keys())
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = (
                    None  # Force creation of a new message when processed
                )
            else:
                # New stream while another is active -> finalize previous WITHOUT deleting its content
                self._finalize_stream_state(
                    partial=True
                )  # Keep sequence buffer for possible early tokens
                self._expected_sequence = sequence_num
                self._current_stream_tokens = []
                self._stream_started = True
                self._active_stream_message_index = None

        # Store token in sequence buffer
        self._sequence_buffer[sequence_num] = llm_response

        # Process any tokens that are now in sequence immediately
        self._process_sequential_tokens()

    def _process_sequential_tokens(self):
        """Process buffered tokens that are in the correct sequence."""

        processed_any = False
        last_token_was_end = False
        while self._expected_sequence in self._sequence_buffer:
            token_response = self._sequence_buffer.pop(self._expected_sequence)

            # Add to stream buffer
            if token_response.message:
                self._current_stream_tokens.append(token_response.message)
            if getattr(token_response, "is_end_of_message", False):
                last_token_was_end = True

            self._expected_sequence += 1
            processed_any = True

        # Update the conversation display only once after processing all available tokens
        if processed_any:
            combined_content = "".join(self._current_stream_tokens)

            if not self._streamed_messages:
                self._streamed_messages = []

            # Update or create bot message
            if self._active_stream_message_index is None:
                # Always create a new message for a new stream to avoid overwriting prior answers
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

            # Assign IDs and update conversation
            self._streamed_messages = self._assign_message_ids(
                self._streamed_messages
            )
            self.set_conversation(self._streamed_messages)

        if last_token_was_end:
            self._finalize_stream_state()

    def _finalize_stream_state(self, partial: bool = False):
        """Reset streaming state after a message completes.

        Args:
            partial: If True, keeps existing sequence buffer (used when a new first token arrives mid-stream).
        """
        self._stream_started = False
        self._current_stream_tokens = []
        self._active_stream_message_index = None
        self._expected_sequence = 1 if not partial else self._expected_sequence
        if not partial:
            self._sequence_buffer = {}

    def on_theme_changed_signal(self, data: Dict):
        """
        Set the theme for the home widget by updating the CSS in the webEngineView.
        This will call the setTheme JS function in the loaded HTML.
        """
        if hasattr(self.ui, "stage"):
            theme_name = data.get(
                "template", TemplateName.SYSTEM_DEFAULT
            ).value.lower()
            # Set window.currentTheme before calling setTheme
            js = f"window.currentTheme = '{theme_name}'; window.setTheme && window.setTheme('{theme_name}');"
            self.ui.stage.page().runJavaScript(js)
        super().on_theme_changed_signal(data)
