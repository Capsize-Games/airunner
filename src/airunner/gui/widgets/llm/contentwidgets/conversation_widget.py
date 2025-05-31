"""
ConversationWidget: Single QWebEngineView-based chat display widget.

Renders the entire conversation as HTML using Jinja2, replacing per-message widgets.

See REFACTOR.md for design rationale.
"""

from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtCore import QObject, Signal, Slot, Property
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
import os
import logging
from airunner.utils.text.formatter_extended import FormatterExtended
from airunner.settings import CONTENT_WIDGETS_BASE_PATH

logger = logging.getLogger(__name__)


class ChatBridge(QObject):
    appendMessage = Signal(dict)
    clearMessages = Signal()
    setMessages = Signal(list)

    @Slot(list)
    def set_messages(self, messages):
        self.setMessages.emit(messages)

    @Slot(dict)
    def append_message(self, msg):
        self.appendMessage.emit(msg)

    @Slot()
    def clear_messages(self):
        self.clearMessages.emit()


class ConversationWidget(QWidget):
    """Widget that displays a conversation using a single QWebEngineView and HTML template.

    Args:
        parent (QWidget, optional): Parent widget.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)
        self.setLayout(layout)

        # Set up Jinja2 environment with correct static content widgets path
        static_html_dir = os.path.join(CONTENT_WIDGETS_BASE_PATH, "html")
        self._env = Environment(
            loader=FileSystemLoader(static_html_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self._template = self._env.get_template("conversation.html")

        self._web_channel = QWebChannel(self._view.page())
        self._chat_bridge = ChatBridge()
        self._web_channel.registerObject("chatBridge", self._chat_bridge)
        self._view.page().setWebChannel(self._web_channel)
        html = self._template.render(messages=[])  # Initial empty
        base_url = f"file://{static_html_dir}/"
        self._view.setHtml(html, base_url)

    def _get_widget_template_for_type(self, content_type: str) -> str:
        """Return the relative path to the widget template for a given content type."""
        mapping = {
            FormatterExtended.FORMAT_PLAINTEXT: "plain_text_widget.jinja2.html",
            FormatterExtended.FORMAT_LATEX: "latex_widget.jinja2.html",
            FormatterExtended.FORMAT_MIXED: "mixed_content_widget.jinja2.html",
            FormatterExtended.FORMAT_MARKDOWN: "content_widget.jinja2.html",
        }
        return mapping.get(
            content_type,
            "plain_text_widget.jinja2.html",
        )

    def wait_for_js_ready(self, callback, max_attempts=50):
        """Wait for the JS QWebChannel to be ready before calling setMessages.

        Args:
            callback: Function to call when JS is ready
            max_attempts: Maximum number of retry attempts (default 50 = ~2.5 seconds)
        """
        from PySide6.QtCore import QTimer

        attempt_count = 0

        def check_ready():
            nonlocal attempt_count
            attempt_count += 1

            self._view.page().runJavaScript(
                "window.isChatReady === true",
                lambda ready: handle_result(ready),
            )

        def handle_result(ready):
            if ready:
                callback()
            elif attempt_count < max_attempts:
                # Use QTimer to properly wait before retrying
                QTimer.singleShot(50, check_ready)
            else:
                # Timeout reached, log warning and call callback anyway
                logger.warning(
                    f"ConversationWidget: JavaScript initialization timeout after {max_attempts} attempts"
                )
                callback()

        check_ready()

    def set_conversation(self, messages: List[Dict[str, Any]]) -> None:
        """Update the conversation display.

        Args:
            messages (List[Dict[str, Any]]): List of message dicts (sender, text, timestamp, etc).
        """
        enriched_messages = []
        for msg in messages:
            content = msg.get("text") or msg.get("content") or ""
            fmt = FormatterExtended.format_content(content)
            widget_template = self._get_widget_template_for_type(fmt["type"])
            enriched_messages.append(
                {
                    **msg,
                    "widget_template": widget_template,
                    "content": fmt["content"],
                    "content_type": fmt["type"],
                    "parts": fmt.get("parts"),
                    "font_size": 16,
                    "static_base_path": "/static/content_widgets",
                    "base_href": None,
                }
            )

        def send():
            self._chat_bridge.set_messages(enriched_messages)

        self.wait_for_js_ready(send)
