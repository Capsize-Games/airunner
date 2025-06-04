from typing import List, Dict, Any, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtWebChannel import QWebChannel

from airunner.conversations.conversation_history_manager import (
    ConversationHistoryManager,
)
from airunner.data.models import Conversation
from airunner.enums import SignalCode
from airunner.gui.widgets.llm.contentwidgets.chat_bridge import ChatBridge
from airunner.gui.widgets.llm.loading_widget import LoadingWidget
from airunner.components.chat.gui.widgets.templates.conversation_ui import (
    Ui_conversation,
)
import logging

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.utils.llm import strip_names_from_message
from airunner.utils.text.formatter_extended import FormatterExtended
from airunner.gui.widgets.llm.contentwidgets.conversation_webengine_page import (
    ConversationWebEnginePage,
)

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
        # Use custom QWebEnginePage to intercept link clicks and emit navigation signal
        custom_page = ConversationWebEnginePage(self.ui.stage, self)
        self.ui.stage.setPage(custom_page)
        self._web_channel = QWebChannel(self.ui.stage.page())
        self._chat_bridge = ChatBridge()
        self._chat_bridge.scrollRequested.connect(self._handle_scroll_request)
        # self._chat_bridge.contentHeightChanged.connect(
        #     self._handle_content_height_changed
        # )
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

    def on_delete_conversation(self, data):
        if self.conversation_id == data["conversation_id"]:
            self._clear_conversation_widgets()
            self.conversation = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self.registered:
            self.logger.debug("Rendering conversation template in showEvent")
            try:
                self.render_template(
                    self.ui.stage, "conversation.jinja2.html", messages=[]
                )
                self.logger.debug("Template rendered successfully.")
            except Exception as e:
                self.logger.error(f"Failed to render template: {e}")
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
        print("LOAD CONVERSATION")
        conversation_id = data.get("index")
        self.load_conversation(conversation_id=conversation_id)

    def load_conversation(self, conversation_id: Optional[int] = None):
        """Loads and displays a conversation."""
        self.logger.debug(
            f"ChatPromptWidget.load_conversation called with conversation_id: {conversation_id}"
        )
        conversation = (
            self._conversation_history_manager.get_current_conversation()
        )

        if conversation is None:
            self.logger.info(
                "No conversation found, clearing conversation display."
            )
            self._clear_conversation()
            self.conversation = None
            return

        self._conversation_id = conversation.id
        self._conversation = conversation

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

    def on_add_bot_message_to_conversation(self, data: Dict):
        self.hide_status_indicator()
        llm_response = data.get("response", None)
        if not llm_response:
            raise ValueError("No LLMResponse object found in data")

        if llm_response.node_id is not None:
            return

        if not self._streamed_messages:
            self._streamed_messages = []

        if llm_response.is_first_message:
            self._streamed_messages.append(
                {
                    "name": self.chatbot.botname,
                    "content": llm_response.message,
                    "role": "assistant",
                    "is_bot": True,
                }
            )
        else:
            if (
                self._streamed_messages
                and self._streamed_messages[-1]["is_bot"]
            ):
                self._streamed_messages[-1]["content"] += llm_response.message
            else:
                self._streamed_messages.append(
                    {
                        "name": self.chatbot.botname,
                        "content": llm_response.message,
                        "role": "assistant",
                        "is_bot": True,
                    }
                )
        self.set_conversation(self._streamed_messages)

        if llm_response.is_end_of_message:
            self.enable_generate()

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
                logger.warning(
                    f"ConversationWidget: JavaScript initialization timeout after {max_attempts} attempts"
                )
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
        self.logger.debug(
            f"set_conversation: sending messages: {simplified_messages}"
        )

        def send():
            self.logger.debug(
                f"Sending {len(simplified_messages)} messages to chat bridge"
            )
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

    # def _handle_content_height_changed(self, height: int) -> None:
    #     """Handle content height change from JavaScript and resize the QWebEngineView."""
    #     target_height = max(height + 40, 100)
    #
    #     logger.debug(
    #         f"ConversationWidget: Content height changed to {height}, setting view height to {target_height}"
    #     )
    #
    #     self.ui.stage.setMinimumHeight(target_height)
    #     self.setMinimumHeight(target_height)
    #
    #     self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    #     self.ui.stage.setSizePolicy(
    #         QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    #     )
    #
    #     self.updateGeometry()
    #
    #     QApplication.processEvents()

    def _set_conversation_widgets(self, messages, skip_scroll: bool = False):
        """Replace per-message widgets with a single HTML conversation view."""
        self._streamed_messages = list(messages)
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
                        "role": "assistant",
                        "is_bot": True,
                    }
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
        self.set_conversation(self._streamed_messages)

    def _get_view(self):
        """Return the QWebEngineView used for rendering the conversation."""
        return self.ui.stage if self.ui and hasattr(self.ui, "stage") else None

    @property
    def _view(self):
        """Compat property for tests expecting a _view attribute (QWebEngineView)."""
        return self._get_view()
